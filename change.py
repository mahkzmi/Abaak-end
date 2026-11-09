import pandas as pd
from datetime import datetime

# ============================================================
# ۱. خواندن داده‌های جمع‌آوری‌شده
# ============================================================

df = pd.read_csv('soil_data_iran_500.csv')
print(f"✅ {len(df)} نمونه بارگذاری شد")

# ============================================================
# ۲. تبدیل به فرمت آپلود آباک (نسخه کامل)
# ============================================================

def convert_to_abak_format(df):
    """تبدیل داده‌های SoilGrids به فرمت آپلود آباک"""
    
    samples = []
    
    for idx, row in df.iterrows():
        # تخمین ماده آلی برای عمق 30cm (داده SoilGrids برای 0-5cm است)
        om_30cm = row['organic_matter'] * 0.3
        n_30cm = row['nitrogen'] * 100 * 0.3
        
        sample = {
            # ===== فیلدهای اجباری برای آپلود =====
            'sample_code': f"SG-{idx+1:04d}",
            'sampling_date': datetime.now().strftime('%Y-%m-%d'),
            'laboratory_name': 'SoilGrids (برآورد ماهواره‌ای)',
            'depth': 30,
            
            # ===== پارامترهای خاک =====
            'ph': round(row['ph'], 1),
            'ec': 2.0,  # تخمین اولیه
            'organic_matter': round(om_30cm, 1),
            'nitrogen': round(n_30cm, 1),
            'phosphorus': 15,  # تخمین اولیه
            'potassium': 250,  # تخمین اولیه
            
            # ===== ریزمغذی‌ها (اختیاری) =====
            'iron': None,
            'zinc': None,
            'manganese': None,
            'copper': None,
            
            # ===== بافت خاک =====
            'texture': 'LOAM',  # تخمین اولیه
            
            # ===== مختصات =====
            'latitude': row['latitude'],
            'longitude': row['longitude'],
            
            # ===== اطلاعات اضافی =====
            'source': 'SATELLITE',
            'is_verified': False,
            'farm_name': f'مزرعه شاخص {idx+1}',
            'farmer_name': 'سیستم',
            'farmer_phone': '09120000000',
            'address': 'ایران'
        }
        samples.append(sample)
    
    return samples

# ============================================================
# ۳. تبدیل و ذخیره
# ============================================================

samples = convert_to_abak_format(df)
df_upload = pd.DataFrame(samples)

# ذخیره فایل CSV برای آپلود در پنل
df_upload.to_csv('abak_279_samples.csv', index=False, encoding='utf-8-sig')

print(f"✅ {len(df_upload)} نمونه برای آپلود در آباک آماده شد")
print("\n📊 نمونه اول:")
print(df_upload.head())

# ============================================================
# ۴. نمایش خلاصه
# ============================================================

print("\n" + "="*60)
print("📊 خلاصه داده‌های آماده آپلود:")
print(f"   تعداد کل: {len(df_upload)}")
print(f"   محدوده pH: {df_upload['ph'].min()} - {df_upload['ph'].max()}")
print(f"   محدوده ماده آلی: {df_upload['organic_matter'].min()} - {df_upload['organic_matter'].max()}%")
print(f"   محدوده نیتروژن: {df_upload['nitrogen'].min()} - {df_upload['nitrogen'].max()} ppm")
print("="*60)