from django.core.management.base import BaseCommand
from accounts.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'ایجاد طرح‌های اشتراک اولیه'

    def handle(self, *args, **kwargs):
        plans = [
            {
                'name': 'رایگان',
                'plan_type': 'FREE',
                'price': 0,
                'monthly_analyses': 1,
                'description': 'یک تحلیل رایگان در ماه',
                'features': ['۱ تحلیل در ماه', 'تحلیل پایه خاک', 'دسترسی به نقشه', 'مشاهده نتایج']
            },
            {
                'name': 'حرفه‌ای',
                'plan_type': 'PRO',
                'price': 290000,
                'monthly_analyses': 10,
                'description': '۱۰ تحلیل در ماه با امکانات کامل',
                'features': ['۱۰ تحلیل در ماه', 'تحلیل پیشرفته خاک', 'توصیه‌های تخصصی', 'گزارش‌های تحلیلی', 'پشتیبانی اختصاصی']
            },
            {
                'name': 'سازمانی',
                'plan_type': 'ENTERPRISE',
                'price': 590000,
                'monthly_analyses': 999999,
                'description': 'تحلیل نامحدود برای شرکت‌ها',
                'features': ['تحلیل نامحدود', 'تحلیل فوق‌تخصصی', 'گزارش‌های سفارشی', 'API دسترسی', 'اولویت پشتیبانی', 'مدیریت چند کاربره']
            }
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                plan_type=plan_data['plan_type'],
                defaults={
                    'name': plan_data['name'],
                    'price': plan_data['price'],
                    'monthly_analyses': plan_data['monthly_analyses'],
                    'description': plan_data['description'],
                    'features': plan_data['features']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ طرح {plan.name} ایجاد شد'))
            else:
                self.stdout.write(f'⏳ طرح {plan.name} قبلاً وجود داشت')

        self.stdout.write(self.style.SUCCESS('✅ همه طرح‌ها با موفقیت ایجاد شدند!'))