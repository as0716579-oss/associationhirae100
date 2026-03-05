# ==========================================
# إعدادات PythonAnywhere (WSGI Configuration)
# ==========================================

import sys
import os
from dotenv import load_dotenv

# 1. تحديد مسار المشروع (استبدل 'yourusername' باسم حسابك)
project_home = '/home/yourusername/associationhirae'

if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# 2. تحميل متغيرات البيئة من ملف .env
load_dotenv(os.path.join(project_home, '.env'))

# 3. استدعاء التطبيق
from app import app as application
