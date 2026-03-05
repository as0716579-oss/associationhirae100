import os
import io
import qrcode
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_mail import Mail, Message
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
from models import db, BenefitRequest, ContactMessage, User

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'), override=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Initialize the serializer for secure tokens
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Database configuration
env_uri = os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_DATABASE_URI')

if env_uri:
    # SQLAlchemy 1.4+ requires 'postgresql://' instead of 'postgres://'
    if env_uri.startswith("postgres://"):
        env_uri = env_uri.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = env_uri
else:
    # Fallback for local development
    db_path = os.path.join(basedir, "instance", "hiraa.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail configuration (Gmail SMTP)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_ASCII_ATTACHMENTS'] = False

# Flask-Mail strictly requires the sender to be exactly matching the tuple format if a name is used
# Or just the plain email string. We will use the plain string to be 100% safe.
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

# Debug print (will show in console)
print(f"DEBUG: Mail configured for: {app.config['MAIL_USERNAME']}")
print(f"DEBUG: Default sender: {app.config['MAIL_DEFAULT_SENDER']}")

db.init_app(app)
mail = Mail(app)

# Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# The email that receives requests
ASSOCIATION_EMAIL = os.getenv('ASSOCIATION_EMAIL', app.config['MAIL_USERNAME'])


def send_status_email(req, pdf_content=None):
    """Send acceptance or rejection email to the user with in-memory PDF attachment."""
    try:
        status_text = "مقبول" if req.status == 'accepted' else "مرفوض"
        subject = f"إشعار بقرار بخصوص طلبكم رقم {req.tracking_id} - {status_text}"
        
        html_body = render_template('notification_email.html',
                                    status=req.status,
                                    name=req.first_name,
                                    last_name=req.last_name,
                                    tracking_id=req.tracking_id,
                                    national_id=req.national_id,
                                    city=req.city,
                                    website_url=url_for('index', _external=True),
                                    year=datetime.utcnow().year)
        
        msg = Message(subject, recipients=[req.email], sender=app.config['MAIL_DEFAULT_SENDER'])
        msg.html = html_body
        
        if pdf_content:
            msg.attach(f"Decision_{req.tracking_id}.pdf", "application/pdf", pdf_content)
        
        mail.send(msg)
        return True
    except Exception as e:
        import traceback
        print(f"CRITICAL: SMTP Error: {str(e)}")
        traceback.print_exc()
        return False


def generate_qr_code(data):
    """Generate QR code as base64 string."""
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a5e3a", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def generate_pdf(request_data):
    """Generate Arabic PDF for benefit request in-memory using FPDF2 (Serverless friendly)."""
    try:
        # Prepare Arabic text - Reshape and BiDi for RTL
        def fix_text(text):
            if not text: return ""
            reshaped_text = arabic_reshaper.reshape(str(text))
            return get_display(reshaped_text)

        pdf = FPDF()
        pdf.add_page()
        
        # Load fonts - Ensure Cairo.ttf exists in static/fonts
        font_path = os.path.join(app.root_path, 'static', 'fonts', 'Cairo.ttf')
        pdf.add_font('Cairo', '', font_path)
        pdf.set_font('Cairo', '', 14)

        # Header Section
        pdf.set_text_color(26, 94, 58) # #1a5e3a
        pdf.set_font('Cairo', '', 18)
        pdf.cell(0, 10, fix_text("جمعية حراء للأعمال الاجتماعية"), ln=True, align='C')
        pdf.set_font('Cairo', '', 10)
        pdf.cell(0, 10, fix_text("المقر المركزي - المملكة المغربية"), ln=True, align='C')
        pdf.ln(5)
        pdf.set_draw_color(26, 94, 58)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(10)

        # Official Title
        pdf.set_font('Cairo', '', 20)
        pdf.cell(0, 15, fix_text("إشعار بخصوص طلب الاستفادة"), ln=True, align='C')
        pdf.ln(5)

        # Reference and Date
        pdf.set_text_color(68, 68, 68)
        pdf.set_font('Cairo', '', 10)
        decision_date = request_data.decision_date.strftime('%Y-%m-%d') if request_data.decision_date else datetime.utcnow().strftime('%Y-%m-%d')
        pdf.cell(0, 8, fix_text(f"الرقم المرجعي: {request_data.tracking_id}"), ln=True, align='R')
        pdf.cell(0, 8, fix_text(f"تاريخ القرار: {decision_date}"), ln=True, align='R')
        pdf.ln(10)

        # Content Section
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Cairo', '', 12)
        full_name = f"{request_data.first_name} {request_data.last_name}"
        pdf.cell(0, 10, fix_text(f"إلى السيد(ة): {full_name}"), ln=True, align='R')
        pdf.ln(5)

        # Status Logic
        if request_data.status == 'accepted':
            status_txt = "الحالة: مقبول ✅"
            body_txt = f"يسرنا إبلاغكم بأنه قد تمت الموافقة على استفادتكم من {request_data.request_type}. نتمنى لكم شهراً مباركاً."
        elif request_data.status == 'rejected':
            status_txt = "الحالة: مرفوض ❌"
            body_txt = "نشكركم على ثقتكم. نأسف لإبلاغكم بأنه لم نتمكن من قبول طلبكم في هذه الفترة نظراً لمحدودية الموارد."
        else:
            status_txt = "الحالة: قيد المعالجة ⌛"
            body_txt = "هذا المستند يعتبر تأكيداً على استلام طلبكم وهو حالياً قيد الدراسة."

        pdf.set_font('Cairo', '', 14)
        pdf.cell(0, 10, fix_text(status_txt), ln=True, align='R')
        pdf.set_font('Cairo', '', 12)
        pdf.multi_cell(0, 10, fix_text(body_txt), align='R')
        pdf.ln(15)

        # Visitor Data Section
        pdf.set_fill_color(245, 245, 245)
        pdf.set_font('Cairo', '', 11)
        pdf.cell(0, 10, fix_text("بيانات مقدم الطلب"), ln=True, align='R', fill=True)
        pdf.ln(5)
        
        data_items = [
            ("الاسم كامل", full_name),
            ("رقم البطاقة", request_data.national_id),
            ("رقم الهاتف", request_data.phone),
            ("البريد الإلكتروني", request_data.email),
            ("نوع الطلب", request_data.request_type),
            ("المدينة", request_data.city),
        ]

        for label, val in data_items:
            pdf.cell(95, 10, fix_text(str(val)), align='R')
            pdf.set_font('Cairo', '', 11)
            pdf.cell(95, 10, fix_text(f"{label}:"), align='R', ln=True)

        # Footer Area
        pdf.ln(20)
        
        # Add Stamp Image if exists
        stamp_path = os.path.join(app.root_path, 'static', 'images', 'stamp.png')
        if os.path.exists(stamp_path):
            pdf.image(stamp_path, x=150, y=pdf.get_y(), w=40)
        
        pdf.ln(30)
        pdf.set_font('Cairo', '', 8)
        pdf.set_text_color(153, 153, 153)
        bottom_note = "هذا المستند تم استخراجه إلكترونياً ولا يحتاج إلى توقيع خطي في حال وجود الختم الإلكتروني."
        pdf.cell(0, 10, fix_text(bottom_note), ln=True, align='C')

        return pdf.output()
    except Exception as e:
        print(f"Error generating PDF (FPDF2): {e}")
        return None

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Home page."""
    stats = {
        'beneficiaries': BenefitRequest.query.filter_by(status='accepted').count() or 1250,
        'volunteers': 85,
        'meals': 15000,
        'cities': 12
    }
    return render_template('index.html', stats=stats)


@app.route('/about')
def about():
    """About us page."""
    return render_template('about.html')


@app.route('/program')
def program():
    """Iftar program page."""
    return render_template('program.html')


@app.route('/request', methods=['GET', 'POST'])
def benefit_request():
    """Benefit request form."""
    if request.method == 'POST':
        # Server-side validation
        required_fields = ['first_name', 'last_name', 'national_id', 'phone', 'email',
                          'city', 'family_members', 'marital_status', 'address', 'request_type']
        
        for field in required_fields:
            if not request.form.get(field, '').strip():
                flash('يرجى ملء جميع الحقول المطلوبة', 'error')
                return redirect(url_for('benefit_request'))
        
        if not request.form.get('privacy_agree'):
            flash('يجب الموافقة على سياسة الخصوصية', 'error')
            return redirect(url_for('benefit_request'))
        
        # Validate national ID (Moroccan CIN format)
        national_id = request.form['national_id'].strip()
        if len(national_id) < 4 or len(national_id) > 20:
            flash('رقم البطاقة الوطنية غير صالح', 'error')
            return redirect(url_for('benefit_request'))
        
        # Validate phone
        phone = request.form['phone'].strip()
        if len(phone) < 10:
            flash('رقم الهاتف غير صالح', 'error')
            return redirect(url_for('benefit_request'))
        
        try:
            family_members = int(request.form['family_members'])
            if family_members < 1 or family_members > 50:
                raise ValueError
        except ValueError:
            flash('عدد أفراد الأسرة غير صالح', 'error')
            return redirect(url_for('benefit_request'))
        
        # Create benefit request
        new_request = BenefitRequest(
            tracking_id=BenefitRequest.generate_tracking_id(),
            first_name=request.form['first_name'].strip(),
            last_name=request.form['last_name'].strip(),
            national_id=national_id,
            phone=phone,
            email=request.form['email'].strip(),
            city=request.form['city'].strip(),
            family_members=family_members,
            marital_status=request.form['marital_status'].strip(),
            address=request.form['address'].strip(),
            request_type=request.form['request_type'].strip(),
            description=request.form.get('description', '').strip(),
            status='pending'
        )
        
        db.session.add(new_request)
        db.session.commit()
        print(f"DEBUG: New request saved. Tracking ID: {new_request.tracking_id}")
        print(f"DEBUG: Current DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Generate PDF - No longer stored on disk for Vercel
        # pdf_content = generate_pdf(new_request) # Optional: generate only on demand or keep in memory
        
        return render_template('request_success.html', tracking_id=new_request.tracking_id)
        
        # Send email - Removed for privacy/Admin Dashboard reliance
        # email_sent = send_email_with_pdf(new_request, pdf_path)
        
        return render_template('request_success.html', tracking_id=new_request.tracking_id)
    
    return render_template('request.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message_text = request.form.get('message', '').strip()
        
        if not all([name, email, subject, message_text]):
            flash('يرجى ملء جميع الحقول', 'error')
            return redirect(url_for('contact'))
        
        msg = ContactMessage(
            name=name,
            email=email,
            subject=subject,
            message=message_text
        )
        db.session.add(msg)
        db.session.commit()
        
        flash('تم إرسال رسالتك بنجاح! سنتواصل معك قريباً.', 'success')
        return redirect(url_for('contact'))
    
    return render_template('contact.html')


@app.route('/privacy')
def privacy():
    """Privacy policy page."""
    return render_template('privacy.html')


# ============= AUTH ROUTES =============

@app.route('/hiraa-private-access', methods=['GET', 'POST'])
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('خطأ في اسم المستخدم أو كلمة المرور', 'error')
            return redirect(url_for('login'))
        
        login_user(user, remember=remember)
        return redirect(url_for('admin'))
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout action."""
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('login'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('admin'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        # Check against ASSOCIATION_EMAIL from .env
        if email == ASSOCIATION_EMAIL:
            # Create a secure token valid for 1 hour (3600 seconds)
            token = serializer.dumps(ASSOCIATION_EMAIL, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            
            try:
                # Send the email
                msg = Message("استعادة كلمة المرور - جمعية حراء",
                              recipients=[ASSOCIATION_EMAIL],
                              sender=app.config['MAIL_DEFAULT_SENDER'])
                
                html_body = render_template('reset_email.html',
                                            reset_url=reset_url,
                                            year=datetime.utcnow().year)
                msg.html = html_body
                mail.send(msg)
                
                flash('تم إرسال رابط استعادة كلمة المرور إلى بريدك الإلكتروني.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                import traceback
                print(f"CRITICAL: Failed to send reset email. Exception: {str(e)}")
                traceback.print_exc()
                flash('حدث خطأ أثناء إرسال البريد الإلكتروني. يرجى المحاولة لاحقاً.', 'error')
        else:
            flash('البريد الإلكتروني غير متطابق مع السجلات لدينا.', 'error')
            
    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('admin'))
        
    try:
        # Verify the token (max_age=3600 seconds = 1 hour)
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except Exception:
        flash('رابط استعادة كلمة المرور غير صالح أو منتهي الصلاحية.', 'error')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('كلمات المرور غير متطابقة.', 'error')
            return render_template('reset_password.html', token=token)
            
        # Get the admin user
        admin = User.query.filter_by(is_admin=True).first()
        if admin:
            if new_username and new_username.strip() != "":
                admin.username = new_username.strip()
            
            admin.set_password(new_password)
            db.session.commit()
            
            flash('تم تغيير كلمة المرور واسم المستخدم (إن وجد) بنجاح! يمكنك الآن تسجيل الدخول.', 'success')
            return redirect(url_for('login'))
        else:
            flash('حدث خطأ غير متوقع. لم يتم العثور على حساب المسؤول.', 'error')
            
    return render_template('reset_password.html', token=token)



# ==================== ADMIN ROUTES ====================

@app.route('/hiraa-dashboard-secret')
@login_required
def admin():
    """Admin dashboard."""
    status_filter = request.args.get('status', 'all')
    
    if status_filter == 'all':
        requests_list = BenefitRequest.query.order_by(BenefitRequest.created_at.desc()).all()
    else:
        requests_list = BenefitRequest.query.filter_by(status=status_filter).order_by(
            BenefitRequest.created_at.desc()).all()
    
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(10).all()
    
    stats = {
        'total': BenefitRequest.query.count(),
        'pending': BenefitRequest.query.filter_by(status='pending').count(),
        'accepted': BenefitRequest.query.filter_by(status='accepted').count(),
        'rejected': BenefitRequest.query.filter_by(status='rejected').count(),
        'messages': ContactMessage.query.count()
    }
    
    return render_template('admin.html',
                          requests=requests_list,
                          messages=messages,
                          stats=stats,
                          current_filter=status_filter)


@app.route('/hiraa-admin-secret/request/<int:request_id>/status', methods=['POST'])
@login_required
def update_request_status(request_id):
    """Update request status, set decision date, and send official PDF."""
    req = BenefitRequest.query.get_or_404(request_id)
    new_status = request.form.get('status')
    
    if new_status in ['accepted', 'rejected'] and req.status == 'pending':
        req.status = new_status
        req.decision_date = datetime.utcnow()
        db.session.commit()
        
        # Regenerate PDF in-memory as an official decision letter
        pdf_content = generate_pdf(req)
        db.session.commit()
        
        # Send email notification with in-memory attachment
        email_sent = send_status_email(req, pdf_content)
            
        status_ar = "مقبول" if new_status == 'accepted' else "مرفوض"
        if email_sent:
            flash(f'تم تحديث حالة الطلب {req.tracking_id} إلى {status_ar} وإرسال الإشعار الرسمي بالبريد.', 'success')
        else:
            flash(f'تم تحديث الحالة إلى {status_ar}، ولكن فشل إرسال البريد الإلكتروني. يرجى التحقق من إعدادات SMTP.', 'warning')
    else:
        flash('لا يمكن تغيير حالة طلب تمت معالجته مسبقاً', 'error')
        
    return redirect(url_for('admin'))


@app.route('/hiraa-admin-secret/request/<int:request_id>/pdf')
@login_required
def download_pdf(request_id):
    """Download or regenerate PDF in-memory."""
    req = BenefitRequest.query.get_or_404(request_id)
    
    pdf_content = generate_pdf(req)
    
    if not pdf_content:
        flash('عذراً، حدث خطأ أثناء إنشاء ملف PDF.', 'error')
        return redirect(url_for('admin'))
    
    return send_file(
        io.BytesIO(pdf_content),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{req.tracking_id}.pdf'
    )


@app.route('/hiraa-admin-secret/request/<int:request_id>/delete', methods=['POST'])
@login_required
def delete_request(request_id):
    """Delete a request."""
    req = BenefitRequest.query.get_or_404(request_id)
    if req.pdf_path and os.path.exists(req.pdf_path):
        os.remove(req.pdf_path)
    db.session.delete(req)
    db.session.commit()
    flash('تم حذف الطلب بنجاح', 'success')
    return redirect(url_for('admin'))


@app.route('/hiraa-admin-secret/test-email')
@login_required
def test_email_config():
    """Test SMTP configuration by sending a test email."""
    try:
        msg = Message("اختبار إعدادات البريد - جمعية حراء",
                      recipients=[ASSOCIATION_EMAIL],
                      sender=app.config['MAIL_DEFAULT_SENDER'])
        msg.body = "إذا وصلتكم هذه الرسالة، فإن إعدادات SMTP تعمل بشكل صحيح."
        mail.send(msg)
        flash('تم إرسال رسالة الاختبار بنجاح! تحقق من بريدك.', 'success')
    except Exception as e:
        flash(f'فشل إرسال رسالة الاختبار: {str(e)}', 'error')
    return redirect(url_for('admin'))


# ==================== INIT ====================

with app.app_context():
    db.create_all()
    # Create default admin user if not exists
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(username='admin')
        admin_user.set_password('admin123')  # Default password, user should change it
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user created: admin / admin123")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
