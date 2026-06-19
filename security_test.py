import requests
import json

# ============================================================
# تنظیمات
# ============================================================
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/login/"
ANALYZE_URL = f"{BASE_URL}/api/analyses/analyze/"

# ============================================================
# ۱. دریافت توکن
# ============================================================
def get_token():
    # اطلاعات کاربر تست
    credentials = {
        "username": "test_user",  # ← این رو با کاربر واقعی عوض کن
        "password": "test123456"   # ← این رو با رمز واقعی عوض کن
    }
    
    try:
        response = requests.post(LOGIN_URL, json=credentials)
        
        if response.status_code == 200:
            token = response.json().get('access')
            print(f"✅ توکن دریافت شد: {token[:20]}...")
            return token
        else:
            print(f"❌ خطا در دریافت توکن: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ خطا: {e}")
        return None

# ============================================================
# ۲. تست SQL Injection
# ============================================================
def test_sql_injection(token):
    print("\n🔴 تست SQL Injection...")
    
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "ph": "7.2 OR 1=1",
        "ec": "0.8",
        "organic_matter": "2.1",
        "texture": "LOAM"
    }
    
    try:
        response = requests.post(ANALYZE_URL, headers=headers, json=data)
        
        if response.status_code == 400:
            print("✅ SQL Injection blocked - Status: 400")
            print(f"   Response: {response.json()}")
        else:
            print(f"⚠️ SQL Injection - Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ خطا: {e}")

# ============================================================
# ۳. تست XSS
# ============================================================
def test_xss(token):
    print("\n🔴 تست XSS...")
    
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "ph": "7.2",
        "ec": "0.8",
        "organic_matter": "2.1",
        "texture": "LOAM<script>alert(1)</script>"
    }
    
    try:
        response = requests.post(ANALYZE_URL, headers=headers, json=data)
        
        if response.status_code == 400:
            print("✅ XSS blocked - Status: 400")
            print(f"   Response: {response.json()}")
        else:
            print(f"⚠️ XSS - Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ خطا: {e}")

# ============================================================
# ۴. تست داده‌های معتبر (کنترل)
# ============================================================
def test_valid_data(token):
    print("\n🟢 تست داده‌های معتبر (کنترل)...")
    
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "ph": 7.2,
        "ec": 0.8,
        "organic_matter": 2.1,
        "texture": "LOAM"
    }
    
    try:
        response = requests.post(ANALYZE_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            print("✅ داده‌های معتبر پذیرفته شد - Status: 200")
            result = response.json()
            print(f"   شاخص سلامت: {result.get('soil_health_index', 'N/A')}%")
        else:
            print(f"⚠️ داده‌های معتبر - Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ خطا: {e}")

# ============================================================
# ۵. تست دسترسی غیرمجاز
# ============================================================
def test_unauthorized():
    print("\n🔴 تست دسترسی غیرمجاز (بدون توکن)...")
    
    data = {
        "ph": "7.2",
        "ec": "0.8",
        "organic_matter": "2.1",
        "texture": "LOAM"
    }
    
    try:
        response = requests.post(ANALYZE_URL, json=data)
        
        if response.status_code == 401:
            print("✅ دسترسی غیرمجاز blocked - Status: 401")
        else:
            print(f"⚠️ دسترسی غیرمجاز - Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ خطا: {e}")

# ============================================================
# اجرای تست‌ها
# ============================================================
if __name__ == "__main__":
    print("🛡️ شروع تست‌های امنیتی آباک")
    print("=" * 40)
    
    token = get_token()
    if not token:
        print("❌ تست متوقف شد")
        exit()
    
    test_valid_data(token)      # کنترل - داده‌های سالم
    test_sql_injection(token)   # تست SQL Injection
    test_xss(token)             # تست XSS
    test_unauthorized()         # تست بدون توکن
    
    print("\n" + "=" * 40)
    print("✅ تست‌های امنیتی کامل شد")