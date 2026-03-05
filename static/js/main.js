// =============================================
//  جمعية حراء — Main JavaScript
// =============================================

document.addEventListener('DOMContentLoaded', function () {
    // Hide loader
    const loader = document.getElementById('loader');
    if (loader) {
        setTimeout(() => {
            loader.classList.add('hidden');
            setTimeout(() => loader.remove(), 500);
        }, 600);
    }

    // Auto-hide flash messages
    const flashMessages = document.querySelectorAll('.flash-msg');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(-50%) translateY(-20px)';
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });

    // ==================== Navbar Scroll Effect ====================
    const navbar = document.getElementById('navbar');
    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 80) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
        // Check on load
        if (window.scrollY > 80) navbar.classList.add('scrolled');
    }

    // ==================== Mobile Menu ====================
    window.toggleMenu = function () {
        const navLinks = document.getElementById('navLinks');
        const toggle = document.getElementById('mobileToggle');
        if (navLinks && toggle) {
            navLinks.classList.toggle('active');
            toggle.classList.toggle('active');
        }
    };

    // Close menu on link click
    const navLinks = document.querySelectorAll('.nav-links a');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            const menu = document.getElementById('navLinks');
            const toggle = document.getElementById('mobileToggle');
            if (menu) menu.classList.remove('active');
            if (toggle) toggle.classList.remove('active');
        });
    });

    // ==================== Scroll Animations ====================
    const animateElements = document.querySelectorAll('.animate-on-scroll');

    const observerOptions = {
        root: null,
        rootMargin: '0px 0px -80px 0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                // Stagger the animations
                setTimeout(() => {
                    entry.target.classList.add('in-view');
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    animateElements.forEach(el => observer.observe(el));

    // ==================== Animated Counters ====================
    const statNumbers = document.querySelectorAll('.stat-number[data-count]');

    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const target = parseInt(el.dataset.count);
                animateCounter(el, target);
                counterObserver.unobserve(el);
            }
        });
    }, { threshold: 0.5 });

    statNumbers.forEach(el => counterObserver.observe(el));

    function animateCounter(element, target) {
        const duration = 2000;
        const start = 0;
        const startTime = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.floor(eased * target);

            element.textContent = current.toLocaleString('ar-MA');

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                element.textContent = target.toLocaleString('ar-MA');
            }
        }

        requestAnimationFrame(update);
    }

    // ==================== Form Validation ====================
    const benefitForm = document.getElementById('benefitForm');
    if (benefitForm) {
        benefitForm.addEventListener('submit', function (e) {
            let isValid = true;

            // Clear previous errors
            document.querySelectorAll('.form-control').forEach(el => {
                el.classList.remove('is-invalid', 'is-valid');
            });
            document.querySelectorAll('.invalid-feedback').forEach(el => {
                el.textContent = '';
            });

            // Required fields
            const requiredFields = [
                { id: 'firstName', error: 'firstNameError', msg: 'يرجى إدخال الاسم' },
                { id: 'lastName', error: 'lastNameError', msg: 'يرجى إدخال النسب' },
                { id: 'nationalId', error: 'nationalIdError', msg: 'يرجى إدخال رقم البطاقة الوطنية' },
                { id: 'phone', error: 'phoneError', msg: 'يرجى إدخال رقم الهاتف' },
                { id: 'city', error: 'cityError', msg: 'يرجى اختيار المدينة' },
                { id: 'address', error: 'addressError', msg: 'يرجى إدخال العنوان' },
                { id: 'familyMembers', error: 'familyMembersError', msg: 'يرجى إدخال عدد أفراد الأسرة' },
                { id: 'maritalStatus', error: 'maritalStatusError', msg: 'يرجى اختيار الحالة الاجتماعية' }
            ];

            requiredFields.forEach(field => {
                const el = document.getElementById(field.id);
                const errorEl = document.getElementById(field.error);
                if (el && !el.value.trim()) {
                    el.classList.add('is-invalid');
                    if (errorEl) errorEl.textContent = field.msg;
                    isValid = false;
                } else if (el) {
                    el.classList.add('is-valid');
                }
            });

            // Phone validation
            const phone = document.getElementById('phone');
            if (phone && phone.value.trim() && phone.value.trim().length < 10) {
                phone.classList.add('is-invalid');
                phone.classList.remove('is-valid');
                const errorEl = document.getElementById('phoneError');
                if (errorEl) errorEl.textContent = 'رقم الهاتف يجب أن يكون 10 أرقام على الأقل';
                isValid = false;
            }

            // Privacy checkbox
            const privacy = document.getElementById('privacyAgree');
            if (privacy && !privacy.checked) {
                isValid = false;
                alert('يجب الموافقة على سياسة الخصوصية');
            }

            if (!isValid) {
                e.preventDefault();
                // Scroll to first error
                const firstError = document.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstError.focus();
                }
            } else {
                // Disable submit button
                const btn = document.getElementById('submitBtn');
                if (btn) {
                    btn.disabled = true;
                    btn.innerHTML = '⏳ جاري الإرسال...';
                }
            }
        });

        // Live validation
        document.querySelectorAll('.form-control').forEach(input => {
            input.addEventListener('blur', function () {
                if (this.required && !this.value.trim()) {
                    this.classList.add('is-invalid');
                    this.classList.remove('is-valid');
                } else if (this.value.trim()) {
                    this.classList.add('is-valid');
                    this.classList.remove('is-invalid');
                    // Clear error message
                    const errorId = this.id + 'Error';
                    const errorEl = document.getElementById(errorId);
                    if (errorEl) errorEl.textContent = '';
                }
            });
        });
    }

    // ==================== Smooth Scroll ====================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ==================== Gallery Lightbox (simple) ====================
    const galleryItems = document.querySelectorAll('.gallery-item');
    galleryItems.forEach(item => {
        item.addEventListener('click', function () {
            const img = this.querySelector('img');
            if (!img) return;

            const overlay = document.createElement('div');
            overlay.style.cssText = `
                position: fixed; inset: 0; z-index: 10000;
                background: rgba(0,0,0,0.9); display: flex;
                align-items: center; justify-content: center;
                cursor: pointer; animation: fadeIn 0.3s ease;
            `;

            const bigImg = document.createElement('img');
            bigImg.src = img.src;
            bigImg.alt = img.alt;
            bigImg.style.cssText = `
                max-width: 90vw; max-height: 90vh;
                border-radius: 12px; box-shadow: 0 8px 40px rgba(0,0,0,0.5);
            `;

            overlay.appendChild(bigImg);
            document.body.appendChild(overlay);
            document.body.style.overflow = 'hidden';

            overlay.addEventListener('click', () => {
                overlay.style.opacity = '0';
                setTimeout(() => {
                    overlay.remove();
                    document.body.style.overflow = '';
                }, 300);
            });
        });
    });
});
