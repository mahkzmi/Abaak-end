from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# ============ تنظیمات Swagger ============
schema_view = get_schema_view(
    openapi.Info(
        title="آباک - API سامانه تحلیل خاک",
        default_version='v1.0',
        description="""
🌾 **سامانه هوشمند تحلیل خاک و توصیه کشاورزی**

این API برای سامانه آباک توسعه داده شده است و شامل موارد زیر می‌باشد:

### 🔐 احراز هویت
- برای دسترسی به APIهای محافظت‌شده، ابتدا توکن JWT دریافت کنید
- توکن را در هدر `Authorization: Bearer <token>` ارسال کنید

### 📊 قابلیت‌های اصلی
- **تحلیل خاک:** دریافت داده‌های خاک و دریافت توصیه‌های هوشمند
- **مدیریت مزارع:** ثبت، ویرایش و حذف مزارع
- **نمونه‌های خاک:** ثبت نمونه‌های خاک از آزمایشگاه‌ها
- **تأیید نمونه‌ها:** تأیید یا رد نمونه‌های خاک توسط کارشناسان
- **تاریخچه سلامت:** مشاهده روند تغییرات شاخص سلامت خاک
- **گزارش‌گیری:** دریافت گزارش PDF از تحلیل‌ها

### 👤 نقش‌های کاربری
- **ADMIN:** دسترسی کامل
- **EXPERT:** تأیید نمونه‌ها و مدیریت درخواست‌ها
- **LAB:** ثبت نمونه‌های خاک
- **FARMER:** مدیریت مزارع و تحلیل خاک
- **VIEWER:** مشاهده محدود

### 📄 مستندات بیشتر
برای اطلاعات بیشتر با پشتیبانی تماس بگیرید.
        """,
        terms_of_service="https://www.abak-agri.ir/terms/",
        contact=openapi.Contact(email="info@abak-agri.ir"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # ============ Swagger ============
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    
    # ============ صفحات اصلی ============
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),
    path('map/', TemplateView.as_view(template_name='soil/map.html'), name='home'),
    path('', include('accounts.urls')),
    path('', include('soil.urls')),
    path('lab/', TemplateView.as_view(template_name='soil/lab_panel.html'), name='lab_panel'),
    path('verify/', TemplateView.as_view(template_name='soil/verify_panel.html'), name='verify_panel'),
    path('register/', TemplateView.as_view(template_name='accounts/register.html'), name='register'),
    path('login/', TemplateView.as_view(template_name='accounts/login.html'), name='login'),
    path('profile/', TemplateView.as_view(template_name='accounts/profile.html'), name='profile'),
    path('subscription/', TemplateView.as_view(template_name='accounts/subscription_plans.html'), name='subscription_plans'),
    path('expert-request/', TemplateView.as_view(template_name='soil/expert_request.html'), name='expert_request'),
    path('health-chart/', TemplateView.as_view(template_name='soil/health_chart.html'), name='health_chart'),
    path('farms/', TemplateView.as_view(template_name='soil/farms.html'), name='farms'),
    path('dashboard/', TemplateView.as_view(template_name='accounts/dashboard.html'), name='dashboard'),
]