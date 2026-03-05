from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class BenefitRequest(db.Model):
    __tablename__ = 'benefit_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    national_id = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    family_members = db.Column(db.Integer, nullable=False)
    marital_status = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    request_type = db.Column(db.String(100), nullable=False, default='طلب استفادة عام')
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    decision_date = db.Column(db.DateTime, nullable=True)
    decision_comment = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(150), nullable=False)
    pdf_path = db.Column(db.String(300), nullable=True)

    def __repr__(self):
        return f'<BenefitRequest {self.tracking_id}>'

    @staticmethod
    def generate_tracking_id():
        date_part = datetime.utcnow().strftime('%Y%m%d')
        unique_part = uuid.uuid4().hex[:4].upper()
        return f'HIR-{date_part}-{unique_part}'


class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ContactMessage {self.name}>'
