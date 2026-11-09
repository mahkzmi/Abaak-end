# prepare_upload.py
import pandas as pd

# خواندن داده‌های ۱۰۰ نقطه
df = pd.read_csv('soil_data_iran_100.csv')

# ============================================================
# تبدیل به فرمت CSV مورد نیاز پنل آزمایشگاه
# ============================================================

# ایجاد لیست نمونه‌ها
samples = []

for idx, row in df.iterrows():
    # تخمین ماده آلی برای عمق 30cm (داده SoilGrids برای 0-5cm است)
    om_30cm = row['organic_matter'] * 0.3
    n_30cm = row['nitrogen'] * 100 * 0.3
    
    sample = {
        'sample_code': f"SG-{idx+1:04d}",
        'sampling_date': '2024-07-15',
        'laboratory_name': 'SoilGrids (برآورد ماهواره‌ای)',
        'depth': 30,
        'ph': round(row['ph'], 1),
        'ec': 2.0,
        'organic_matter': round(om_30cm, 1),
        'nitrogen': round(n_30cm, 1),
        'phosphorus': 15,
        'potassium': 250,
        'texture': 'LOAM',
        'latitude': row['latitude'],
        'longitude': row['longitude'],
        'source': 'SATELLITE',
        'farm_name': f'مزرعه شاخص {idx+1}',
        'farmer_name': 'سیستم',
        'farmer_phone': '09120000000',
        'address': 'ایران'
    }
    samples.append(sample)

# تبدیل به DataFrame
df_upload = pd.DataFrame(samples)

# ذخیره فایل CSV
df_upload.to_csv('abak_ready_100_samples.csv', index=False, encoding='utf-8-sig')
print(f"✅ فایل abak_ready_100_samples.csv با {len(df_upload)} نمونه ایجاد شد")
print("\n📊 نمونه اول:")
print(df_upload.head())