from django.core.management.base import BaseCommand
from soil.models import Province, ClimateData
import random


class Command(BaseCommand):
    help = 'ایجاد داده‌های اقلیمی شبیه‌سازی‌شده برای استان‌ها'

    def handle(self, *args, **kwargs):
        provinces = Province.objects.all()
        
        if not provinces:
            self.stdout.write(self.style.WARNING('⚠️ هیچ استانی در دیتابیس وجود ندارد!'))
            return
        
        # مشخصات اقلیمی هر استان (تقریبی)
        climate_profiles = {
            'تهران': {'temp': 18, 'rain': 250, 'humid': 40, 'sunny': 280},
            'اصفهان': {'temp': 16, 'rain': 150, 'humid': 35, 'sunny': 300},
            'فارس': {'temp': 20, 'rain': 300, 'humid': 45, 'sunny': 290},
            'خوزستان': {'temp': 25, 'rain': 350, 'humid': 55, 'sunny': 280},
            'گیلان': {'temp': 16, 'rain': 1200, 'humid': 75, 'sunny': 200},
            'مازندران': {'temp': 17, 'rain': 800, 'humid': 70, 'sunny': 210},
            'خراسان رضوی': {'temp': 15, 'rain': 200, 'humid': 40, 'sunny': 300},
        }
        
        count = 0
        for province in provinces:
            profile = climate_profiles.get(province.name, {'temp': 18, 'rain': 300, 'humid': 50, 'sunny': 260})
            
            for year in [2022, 2023, 2024]:
                for month in range(1, 13):
                    # ایجاد تغییرات فصلی
                    if month in [12, 1, 2]:
                        temp_offset = -8
                        rain_factor = 0.5
                    elif month in [3, 4, 5]:
                        temp_offset = 5
                        rain_factor = 1.2
                    elif month in [6, 7, 8]:
                        temp_offset = 12
                        rain_factor = 0.3
                    else:  # 9, 10, 11
                        temp_offset = 2
                        rain_factor = 0.8
                    
                    avg_temp = profile['temp'] + temp_offset + random.uniform(-3, 3)
                    min_temp = avg_temp - random.uniform(5, 10)
                    max_temp = avg_temp + random.uniform(5, 10)
                    rainfall = profile['rain'] * rain_factor * random.uniform(0.6, 1.4)
                    humidity = profile['humid'] + random.uniform(-10, 10)
                    sunny_days = int(profile['sunny'] / 12 * (1 + random.uniform(-0.2, 0.2)))
                    
                    ClimateData.objects.get_or_create(
                        province=province,
                        month=month,
                        year=year,
                        defaults={
                            'avg_temperature': round(avg_temp, 1),
                            'min_temperature': round(min_temp, 1),
                            'max_temperature': round(max_temp, 1),
                            'rainfall': round(rainfall, 1),
                            'humidity': round(max(0, min(100, humidity)), 1),
                            'sunny_days': max(0, sunny_days),
                            'source': 'SIMULATED',
                            'is_verified': False,
                        }
                    )
                    count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ {count} رکورد داده‌های اقلیمی ایجاد شد!'))