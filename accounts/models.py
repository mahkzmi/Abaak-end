
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Company(models.Model):
    """مدل شرکت‌های کشاورزی (برای همراه اول و سازمان‌ها)"""
    name = models.CharField(max_length=200, verbose_name="نام شرکت")
    registration_number = models.CharField(max_length=50, unique=True, verbose_name="شماره ثبت")
    economic_code = models.CharField(max_length=20, unique=True, verbose_name="کد اقتصادی")
    phone = models.CharField(max_length=11, verbose_name="شماره تماس")
    address = models.TextField(verbose_name="آدرس")
    province = models.ForeignKey(
        'soil.Province', 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="استان"
    )
    county = models.ForeignKey(
        'soil.County', 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="شهرستان"
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "شرکت"
        verbose_name_plural = "شرکت‌ها"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """پروفایل توسعه‌یافته برای کاربران سیستم"""
    ROLE_CHOICES = [
        ('ADMIN', 'مدیر سیستم'),
        ('EXPERT', 'کارشناس کشاورزی'),
        ('CRM', 'پشتیبانی و CRM'),
        ('LAB', 'کارشناس آزمایشگاه'),
        ('FARMER', 'کشاورز'),
        ('VIEWER', 'بیننده'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        verbose_name="کاربر"
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='FARMER', 
        verbose_name="نقش"
    )
    phone = models.CharField(max_length=11, verbose_name="شماره موبایل")
    company = models.ForeignKey(
        Company, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="شرکت"
    )
    province = models.ForeignKey(
        'soil.Province', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="استان"
    )
    county = models.ForeignKey(
        'soil.County', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="شهرستان"
    )
    profile_picture = models.ImageField(
        upload_to='profiles/', 
        null=True, 
        blank=True, 
        verbose_name="تصویر پروفایل"
    )
    is_verified = models.BooleanField(default=False, verbose_name="تأیید شده")
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="آخرین IP")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل‌های کاربران"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"
    
    def get_full_name(self):
        return self.user.get_full_name()


class Farmer(models.Model):
    """مدل کشاورز (تکمیل‌کننده UserProfile)"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='farmer_profile',
        verbose_name="کاربر"
    )
    national_id = models.CharField(max_length=10, unique=True, verbose_name="کد ملی")
    phone = models.CharField(max_length=11, verbose_name="شماره موبایل")
    address = models.TextField(verbose_name="آدرس")
    province = models.ForeignKey(
        'soil.Province', 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="استان"
    )
    county = models.ForeignKey(
        'soil.County', 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="شهرستان"
    )
    farm_experience_years = models.PositiveIntegerField(
        default=0, 
        verbose_name="سال‌های تجربه کشاورزی"
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "کشاورز"
        verbose_name_plural = "کشاورزان"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.phone}"
    
    def get_full_name(self):
        return self.user.get_full_name()
    

class SubscriptionPlan(models.Model):
    """مدل طرح‌های اشتراک"""
    
    PLAN_TYPES = [
        ('FREE', 'رایگان'),
        ('PRO', 'حرفه‌ای'),
        ('ENTERPRISE', 'سازمانی'),
    ]
    
    name = models.CharField(max_length=50, verbose_name="نام طرح")
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True, verbose_name="نوع طرح")
    price = models.BigIntegerField(default=0, verbose_name="قیمت (تومان)")
    monthly_analyses = models.IntegerField(default=0, verbose_name="تعداد تحلیل در ماه")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    features = models.JSONField(default=list, verbose_name="امکانات", help_text="لیست امکانات طرح")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "طرح اشتراک"
        verbose_name_plural = "طرح‌های اشتراک"
        ordering = ['price']
    
    def __str__(self):
        return f"{self.get_plan_type_display()} - {self.price:,} تومان"


class Subscription(models.Model):
    """مدل اشتراک کاربران"""
    
    STATUS_CHOICES = [
        ('ACTIVE', 'فعال'),
        ('EXPIRED', 'منقضی شده'),
        ('CANCELLED', 'لغو شده'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name="کاربر"
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name="طرح اشتراک"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        verbose_name="وضعیت"
    )
    start_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ شروع")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پایان")
    analyses_used = models.IntegerField(default=0, verbose_name="تعداد تحلیل‌های استفاده شده")
    analyses_remaining = models.IntegerField(default=0, verbose_name="تعداد تحلیل‌های باقی‌مانده")
    last_reset_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آخرین بازنشانی")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "اشتراک"
        verbose_name_plural = "اشتراک‌ها"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.plan.get_plan_type_display()}"
    
    def can_analyze(self):
        """بررسی اینکه کاربر می‌تواند تحلیل جدید انجام دهد"""
        if self.status != 'ACTIVE':
            return False
        if self.plan.plan_type == 'ENTERPRISE':
            return True
        return self.analyses_remaining > 0
    
    def use_analysis(self):
        """استفاده از یک تحلیل"""
        if not self.can_analyze():
            return False
        
        if self.plan.plan_type != 'ENTERPRISE':
            self.analyses_used += 1
            self.analyses_remaining -= 1
        
        self.save()
        return True
    
    def reset_monthly_analyses(self):
        """بازنشانی تعداد تحلیل‌های ماهانه"""
        if self.plan.plan_type != 'ENTERPRISE':
            self.analyses_used = 0
            self.analyses_remaining = self.plan.monthly_analyses
            self.last_reset_date = timezone.now()
            self.save()


class SubscriptionPlan(models.Model):
    """مدل طرح‌های اشتراک"""
    
    PLAN_TYPES = [
        ('FREE', 'رایگان'),
        ('PRO', 'حرفه‌ای'),
        ('ENTERPRISE', 'سازمانی'),
    ]
    
    name = models.CharField(max_length=50, verbose_name="نام طرح")
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True, verbose_name="نوع طرح")
    price = models.BigIntegerField(default=0, verbose_name="قیمت (تومان)")
    monthly_analyses = models.IntegerField(default=0, verbose_name="تعداد تحلیل در ماه")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    features = models.JSONField(default=list, verbose_name="امکانات", help_text="لیست امکانات طرح")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "طرح اشتراک"
        verbose_name_plural = "طرح‌های اشتراک"
        ordering = ['price']
    
    def __str__(self):
        return f"{self.get_plan_type_display()} - {self.price:,} تومان"


class Subscription(models.Model):
    """مدل اشتراک کاربران"""
    
    STATUS_CHOICES = [
        ('ACTIVE', 'فعال'),
        ('EXPIRED', 'منقضی شده'),
        ('CANCELLED', 'لغو شده'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name="کاربر"
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name="طرح اشتراک"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        verbose_name="وضعیت"
    )
    start_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ شروع")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پایان")
    analyses_used = models.IntegerField(default=0, verbose_name="تعداد تحلیل‌های استفاده شده")
    analyses_remaining = models.IntegerField(default=0, verbose_name="تعداد تحلیل‌های باقی‌مانده")
    last_reset_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ آخرین بازنشانی")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "اشتراک"
        verbose_name_plural = "اشتراک‌ها"
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.plan.get_plan_type_display()}"
    
    def can_analyze(self):
        """بررسی اینکه کاربر می‌تواند تحلیل جدید انجام دهد"""
        if self.status != 'ACTIVE':
            return False
        if self.plan.plan_type == 'ENTERPRISE':
            return True
        return self.analyses_remaining > 0
    
    def use_analysis(self):
        """استفاده از یک تحلیل"""
        if not self.can_analyze():
            return False
        
        if self.plan.plan_type != 'ENTERPRISE':
            self.analyses_used += 1
            self.analyses_remaining -= 1
        
        self.save()
        return True
    
    def reset_monthly_analyses(self):
        """بازنشانی تعداد تحلیل‌های ماهانه"""
        if self.plan.plan_type != 'ENTERPRISE':
            self.analyses_used = 0
            self.analyses_remaining = self.plan.monthly_analyses
            self.last_reset_date = timezone.now()
            self.save()