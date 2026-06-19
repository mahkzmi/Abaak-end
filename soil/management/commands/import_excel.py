import csv
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Farmer
from soil.models import Province, County, Farm, SoilSample


class Command(BaseCommand):
    help = 'وارد کردن داده‌های خاک از فایل CSV'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='مسیر فایل CSV')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        
        self.stdout.write(self.style.SUCCESS(f'شروع وارد کردن داده از {file_path}'))
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # ایجاد کاربر پیش‌فرض
                default_user, _ = User.objects.get_or_create(
                    username='farmer_default',
                    defaults={
                        'first_name': 'کاربر',
                        'last_name': 'پیش‌فرض',
                        'email': 'farmer@abak.ir'
                    }
                )
                
                count = 0
                for row in reader:
                    try:
                        # ایجاد استان
                        province, _ = Province.objects.get_or_create(
                            name=row['province'],
                            defaults={'code': row['province'][:3].upper()}
                        )
                        
                        # ایجاد شهرستان
                        county, _ = County.objects.get_or_create(
                            name=row['county'],
                            province=province,
                            defaults={'code': row['county'][:3].upper()}
                        )
                        
                        # ایجاد کشاورز
                        farmer, _ = Farmer.objects.get_or_create(
                            user=default_user,
                            defaults={
                                'national_id': f'F{count+1:05d}',
                                'phone': '0912' + f'{count+1:07d}',
                                'address': 'آدرس نمونه',
                                'province': province,
                                'county': county,
                            }
                        )
                        
                        # ایجاد مزرعه
                        farm, _ = Farm.objects.get_or_create(
                            name=row['farm_name'],
                            farmer=farmer,
                            defaults={
                                'area': float(row['area']),
                                'address': 'آدرس نمونه',
                                'province': province,
                                'county': county,
                            }
                        )
                        
                        # ایجاد نمونه خاک
                        SoilSample.objects.create(
                            farm=farm,
                            sample_code=row['sample_code'],
                            sampling_date=row['sampling_date'],
                            depth=float(row['depth']),
                            ph=float(row['ph']),
                            ec=float(row['ec']),
                            organic_matter=float(row['organic_matter']),
                            nitrogen=float(row['nitrogen']) if row['nitrogen'] else None,
                            phosphorus=float(row['phosphorus']) if row['phosphorus'] else None,
                            potassium=float(row['potassium']) if row['potassium'] else None,
                            texture=row['texture'],
                            latitude=float(row['latitude']),
                            longitude=float(row['longitude']),
                            source='LAB',
                            laboratory_name=row.get('laboratory', ''),
                        )
                        
                        count += 1
                        self.stdout.write(f'✓ نمونه {row["sample_code"]} وارد شد')
                        
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'خطا در سطر {count+1}: {str(e)}'))
                        continue
                
                self.stdout.write(self.style.SUCCESS(f'✅ {count} نمونه خاک با موفقیت وارد شد!'))
                
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ فایل {file_path} پیدا نشد.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ خطا: {str(e)}'))