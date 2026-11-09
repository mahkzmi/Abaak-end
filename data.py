# download_iran_soil_data.py
import pandas as pd
import requests
import io
import time
from tqdm import tqdm

# ============================================================
# ۱. دریافت داده از SoilGrids با روش مطمئن‌تر
# ============================================================

def get_soil_data_simple(lat, lon):
    """دریافت داده با روش ساده‌تر و مطمئن‌تر"""
    url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon}&lat={lat}&property=phh2o&property=soc&property=nitrogen&depth=0-5cm"
    
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            data = response.json()
            return extract_simple_data(data, lat, lon)
        else:
            return None
    except:
        return None

def extract_simple_data(data, lat, lon):
    """استخراج ساده داده‌ها"""
    result = {
        'latitude': lat,
        'longitude': lon,
        'ph': None,
        'organic_matter': None,
        'nitrogen': None
    }
    
    layers = data.get('properties', {}).get('layers', [])
    for layer in layers:
        name = layer.get('name')
        depths = layer.get('depths', [])
        if depths:
            values = depths[0].get('values', {})
            mean = values.get('mean')
            if mean is None:
                continue
            if name == 'phh2o':
                result['ph'] = round(mean / 10, 1)
            elif name == 'nitrogen':
                result['nitrogen'] = round(mean / 100, 2)
            elif name == 'soc':
                result['organic_matter'] = round((mean / 10) * 1.724, 2)
    
    return result

# ============================================================
# ۲. ایجاد نقاط با فاصله کمتر برای داده‌های بیشتر
# ============================================================

def create_points():
    """ایجاد ۵۰۰ نقطه در سراسر ایران"""
    points = []
    lat = 25.0
    while lat <= 40.0:
        lon = 44.0
        while lon <= 63.0:
            points.append((round(lat, 2), round(lon, 2)))
            lon += 0.5
        lat += 0.5
    return points

# ============================================================
# ۳. جمع‌آوری داده با تاخیر مناسب
# ============================================================

def collect_data(points, max_samples=500):
    """جمع‌آوری داده با تاخیر برای جلوگیری از محدودیت"""
    results = []
    
    print(f"🔄 شروع جمع‌آوری داده برای {min(len(points), max_samples)} نقطه...")
    
    for i, (lat, lon) in enumerate(tqdm(points[:max_samples])):
        data = get_soil_data_simple(lat, lon)
        if data and data['ph'] is not None:
            results.append(data)
        
        # تاخیر برای جلوگیری از محدودیت (۲ ثانیه)
        time.sleep(2)
        
        # نمایش پیشرفت هر ۱۰ نقطه
        if (i + 1) % 10 == 0:
            print(f"✅ {len(results)} نمونه معتبر از {i+1} نقطه")
    
    return results

# ============================================================
# ۴. اجرا
# ============================================================

def main():
    print("🌍 شروع جمع‌آوری داده خاک ایران")
    print("="*50)
    
    # ایجاد نقاط
    points = create_points()
    print(f"✅ {len(points)} نقطه ایجاد شد")
    
    # جمع‌آوری داده
    results = collect_data(points, max_samples=500)
    
    # تبدیل به DataFrame
    df = pd.DataFrame(results)
    
    # ذخیره
    if len(df) > 0:
        df.to_csv('soil_data_iran_500.csv', index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ {len(df)} نمونه در soil_data_iran_500.csv ذخیره شد")
        print("\n📊 آمار:")
        print(df.describe())
    else:
        print("❌ هیچ داده‌ای دریافت نشد!")

if __name__ == "__main__":
    main()