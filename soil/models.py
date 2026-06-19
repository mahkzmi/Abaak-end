from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Province(models.Model):
    """استان"""
    name = models.CharField(max_length=100, verbose_name="نام استان")
    code = models.CharField(max_length=10, unique=True, verbose_name="کد استان")
    geometry = models.JSONField(null=True, blank=True, verbose_name="شکل هندسی")
    center_lat  = models.FloatField(null=True, blank=True, verbose_name="عرض مرکز")
    center_lng = models.FloatField(null=True, blank=True, verbose_name="طول مرکز")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class County(models.Model):
    """شهرستان"""
    name = models.CharField(max_length=100, verbose_name="نام شهرستان")
    code = models.CharField(max_length=10, unique=True, verbose_name="کد شهرستان")
    province = models.ForeignKey(
        Province, 
        on_delete=models.CASCADE, 
        related_name='counties',
        verbose_name="استان"
    )
    geometry = models.JSONField(null=True, blank=True, verbose_name="شکل هندسی")

    center_lat = models.FloatField(null=True, blank=True, verbose_name="عرض مرکز")
    center_lng = models.FloatField(null=True, blank=True, verbose_name="طول مرکز")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "شهرستان"
        verbose_name_plural = "شهرستان‌ها"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.province.name}"


class Farm(models.Model):
    farmer = models.ForeignKey(
        'accounts.Farmer', 
        on_delete=models.CASCADE, 
        related_name='farms',
        verbose_name="کشاورز"
    )
    name = models.CharField(max_length=200, verbose_name="نام مزرعه")
    area = models.FloatField(
        validators=[MinValueValidator(0.01)], 
        verbose_name="مساحت (هکتار)"
    )
    # به جای GeometryField، از JSONField استفاده کن
    geometry_coords = models.JSONField(
        default=list, 
        verbose_name="مختصات پلی‌گون",
        help_text="لیست نقاط به صورت [[lng, lat], ...]"
    )
    address = models.TextField(verbose_name="آدرس دقیق")
    province = models.ForeignKey(
        Province, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="استان"
    )
    county = models.ForeignKey(
        County, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="شهرستان"
    )
    village = models.CharField(max_length=100, blank=True, verbose_name="روستا")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "مزرعه"
        verbose_name_plural = "مزارع"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.farmer.user.get_full_name()}"
    
    def get_area_display(self):
        return f"{self.area:.2f} هکتار"


        
class SoilSample(models.Model):
    """نمونه خاک"""
    TEXTURE_CHOICES = [
        ('SANDY', 'شنی'),
        ('LOAMY_SAND', 'لوم شنی'),
        ('SANDY_LOAM', 'شنی لومی'),
        ('LOAM', 'لوم'),
        ('SILT_LOAM', 'لوم سیلتی'),
        ('SILT', 'سیلتی'),
        ('CLAY_LOAM', 'لوم رسی'),
        ('SILTY_CLAY_LOAM', 'لوم رسی سیلتی'),
        ('CLAY', 'رسی'),
    ]

# ============ عناصر ریزمغذی (جدید) ============
    iron = models.FloatField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0)],
        verbose_name="آهن (Fe) (ppm)"
    )
    zinc = models.FloatField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0)],
        verbose_name="روی (Zn) (ppm)"
    )
    manganese = models.FloatField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0)],
        verbose_name="منگنز (Mn) (ppm)"
    )
    copper = models.FloatField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0)],
        verbose_name="مس (Cu) (ppm)"
    )
    
    farm = models.ForeignKey(
        Farm, 
        on_delete=models.CASCADE, 
        related_name='soil_samples',
        verbose_name="مزرعه"
    )
    sample_code = models.CharField(max_length=50, unique=True, verbose_name="کد نمونه")
    sampling_date = models.DateField(verbose_name="تاریخ نمونه‌برداری")
    depth = models.FloatField(
        validators=[MinValueValidator(0)], 
        verbose_name="عمق نمونه‌برداری (سانتی‌متر)"
    )
        # فیلدهای تأیید
    is_verified = models.BooleanField(default=False, verbose_name="تأیید شده")
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verified_samples',
        verbose_name="تأیید شده توسط"
    )
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ تأیید")
    rejection_reason = models.TextField(blank=True, verbose_name="دلیل رد")
    
    # هشدارهای خودکار
    validation_warnings = models.JSONField(default=list, blank=True, verbose_name="هشدارهای اعتبارسنجی")


     
    def validate_sample(self):
        """
        اعتبارسنجی خودکار داده‌های نمونه
        برگرداندن لیستی از هشدارها
        """
        warnings = []
        
        # محدوده‌های معتبر
        if not (0 <= self.ph <= 14):
            warnings.append(f"pH خارج از محدوده معتبر (۰-۱۴): {self.ph}")
        elif self.ph < 4.5:
            warnings.append(f"pH بسیار اسیدی: {self.ph}")
        elif self.ph > 9.0:
            warnings.append(f"pH بسیار قلیایی: {self.ph}")
        
        if self.ec < 0:
            warnings.append(f"EC نامعتبر: {self.ec}")
        elif self.ec > 10:
            warnings.append(f"EC بسیار بالا: {self.ec} dS/m (احتمالاً شور)")
        
        if self.organic_matter < 0:
            warnings.append(f"ماده آلی نامعتبر: {self.organic_matter}%")
        elif self.organic_matter > 10:
            warnings.append(f"ماده آلی بسیار بالا: {self.organic_matter}%")
        
        if self.depth <= 0:
            warnings.append(f"عمق نامعتبر: {self.depth} سانتی‌متر")
        
        return warnings
    
    def save(self, *args, **kwargs):
        # اعتبارسنجی خودکار قبل از ذخیره
        if not self.pk:  # فقط برای نمونه‌های جدید
            self.validation_warnings = self.validate_sample()
        super().save(*args, **kwargs)

    
    # پارامترهای اصلی خاک
    ph = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(14)],
        verbose_name="pH"
    )
    ec = models.FloatField(
        validators=[MinValueValidator(0)],
        verbose_name="EC (dS/m)"
    )
    organic_matter = models.FloatField(
        validators=[MinValueValidator(0)],
        verbose_name="ماده آلی (%)"
    )
    nitrogen = models.FloatField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0)],
        verbose_name="نیتروژن (ppm)"
    )
    phosphorus = models.FloatField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0)],
        verbose_name="فسفر (ppm)"
    )
    potassium = models.FloatField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0)],
        verbose_name="پتاسیم (ppm)"
    )
    texture = models.CharField(
        max_length=20, 
        choices=TEXTURE_CHOICES, 
        verbose_name="بافت خاک"
    )
    
    # اطلاعات مکانی
    latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        verbose_name="عرض جغرافیایی"
    )
    longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        verbose_name="طول جغرافیایی"
    )
    
    # منبع داده
    SOURCE_CHOICES = [
        ('LAB', 'آزمایشگاه'),
        ('FIELD', 'نمونه‌برداری میدانی'),
        ('ESTIMATED', 'تخمینی'),
        ('SATELLITE', 'ماهواره‌ای'),
    ]
    source = models.CharField(
        max_length=10, 
        choices=SOURCE_CHOICES, 
        default='LAB', 
        verbose_name="منبع داده"
    )
    laboratory_name = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        verbose_name="نام آزمایشگاه"
    )
    laboratory_code = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="کد آزمایشگاه"
    )
    
    # وضعیت
    is_verified = models.BooleanField(default=False, verbose_name="تأیید شده")
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verified_samples',
        verbose_name="تأیید شده توسط"
    )
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ تأیید")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "نمونه خاک"
        verbose_name_plural = "نمونه‌های خاک"
        ordering = ['-sampling_date']
    
    def __str__(self):
        return f"{self.sample_code} - {self.farm.name}"
    
    def get_texture_display(self):
        return dict(self.TEXTURE_CHOICES).get(self.texture, self.texture)
    
    def save(self, *args, **kwargs):
        if not self.sample_code:
            import uuid
            self.sample_code = f"SOIL-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class SoilAnalysis(models.Model):
    """تحلیل خاک - جایی که هوش مصنوعی وارد می‌شود"""
    SOIL_HEALTH_LEVELS = [
        ('POOR', 'ضعیف'),
        ('FAIR', 'متوسط'),
        ('GOOD', 'خوب'),
        ('EXCELLENT', 'عالی'),
    ]
    
    soil_sample = models.OneToOneField(
        SoilSample, 
        on_delete=models.CASCADE, 
        related_name='analysis',
        verbose_name="نمونه خاک"
    )
    analyst = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='analyses',
        verbose_name="تحلیل‌گر"
    )
    
    # شاخص‌های ترکیبی
    soil_health_index = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="شاخص سلامت خاک (DSHI)"
    )
    soil_health_level = models.CharField(
        max_length=20, 
        choices=SOIL_HEALTH_LEVELS, 
        verbose_name="وضعیت سلامت خاک"
    )
    
    # توصیه‌ها
    recommended_crops = models.JSONField(default=list, verbose_name="محصولات پیشنهادی")
    fertilizer_recommendations = models.JSONField(default=dict, verbose_name="توصیه‌های کودی")
    irrigation_recommendations = models.TextField(blank=True, verbose_name="توصیه‌های آبیاری")
    management_tips = models.TextField(blank=True, verbose_name="نکات مدیریتی")
    
    # پیش‌بینی سود
    expected_yield = models.FloatField(
        validators=[MinValueValidator(0)],
        verbose_name="عملکرد پیش‌بینی شده (تن در هکتار)"
    )
    expected_profit = models.FloatField(
        validators=[MinValueValidator(0)],
        verbose_name="سود پیش‌بینی شده (تومان در هکتار)"
    )
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=70,
        verbose_name="درصد اطمینان پیش‌بینی"
    )
    
    # داده‌های اقتصادی
    input_cost = models.FloatField(
        null=True, 
        blank=True,
        verbose_name="هزینه نهاده‌ها (تومان در هکتار)"
    )
    market_price = models.FloatField(
        null=True, 
        blank=True,
        verbose_name="قیمت بازار (تومان در کیلوگرم)"
    )
    
    # وضعیت
    is_finalized = models.BooleanField(default=False, verbose_name="نهایی شده")
    finalized_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ نهایی‌سازی")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "تحلیل خاک"
        verbose_name_plural = "تحلیل‌های خاک"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"تحلیل {self.soil_sample.sample_code}"
    
    def get_health_level_display(self):
        return dict(self.SOIL_HEALTH_LEVELS).get(self.soil_health_level, self.soil_health_level)


class CropRecommendation(models.Model):
    """توصیه محصول برای یک تحلیل خاص"""
    analysis = models.ForeignKey(
        SoilAnalysis, 
        on_delete=models.CASCADE, 
        related_name='crop_recommendations',
        verbose_name="تحلیل"
    )
    crop_name = models.CharField(max_length=100, verbose_name="نام محصول")
    crop_type = models.CharField(max_length=100, verbose_name="نوع محصول")
    
    # امتیاز تناسب (۰ تا ۱۰۰)
    suitability_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="امتیاز تناسب"
    )
    
    # پیش‌بینی عملکرد
    predicted_yield = models.FloatField(verbose_name="عملکرد پیش‌بینی شده (تن در هکتار)")
    predicted_profit = models.FloatField(verbose_name="سود پیش‌بینی شده (تومان در هکتار)")
    
    # توصیه‌های خاص این محصول
    fertilizer_advice = models.TextField(verbose_name="توصیه کودی")
    irrigation_advice = models.TextField(verbose_name="توصیه آبیاری")
    planting_advice = models.TextField(verbose_name="توصیه کاشت")
    harvest_advice = models.TextField(verbose_name="توصیه برداشت")
    
    # اولویت (از نظر سودآوری)
    priority = models.PositiveIntegerField(default=0, verbose_name="اولویت")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "توصیه محصول"
        verbose_name_plural = "توصیه‌های محصولات"
        ordering = ['-suitability_score', 'priority']
    
    def __str__(self):
        return f"{self.crop_name} - {self.analysis.soil_sample.sample_code}"


class FertilizerRecommendation(models.Model):
    """توصیه کودی دقیق"""
    analysis = models.ForeignKey(
        SoilAnalysis, 
        on_delete=models.CASCADE, 
        related_name='fertilizer_recommendation_items',
        verbose_name="تحلیل"
    )
    crop_recommendation = models.ForeignKey(
        CropRecommendation, 
        on_delete=models.CASCADE, 
        related_name='fertilizers',
        verbose_name="توصیه محصول"
    )
    
    FERTILIZER_TYPES = [
        ('N', 'نیتروژن'),
        ('P', 'فسفر'),
        ('K', 'پتاسیم'),
        ('NPK', 'NPK'),
        ('UREA', 'اوره'),
        ('COMPOST', 'کمپوست'),
        ('MANURE', 'کود دامی'),
    ]
    
    fertilizer_type = models.CharField(max_length=20, choices=FERTILIZER_TYPES, verbose_name="نوع کود")
    amount = models.FloatField(verbose_name="مقدار (کیلوگرم در هکتار)")
    timing = models.CharField(max_length=200, verbose_name="زمان مصرف")
    method = models.CharField(max_length=200, verbose_name="روش مصرف")
    cost_per_hectare = models.FloatField(verbose_name="هزینه (تومان در هکتار)")
    priority = models.PositiveIntegerField(default=0, verbose_name="اولویت")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "توصیه کودی"
        verbose_name_plural = "توصیه‌های کودی"
        ordering = ['priority']
    
    def __str__(self):
        return f"{self.get_fertilizer_type_display()} - {self.amount} kg/ha"


class SoilMonitoringLog(models.Model):
    """لاگ پایش مستمر خاک - برای روند تغییرات"""
    farm = models.ForeignKey(
        Farm, 
        on_delete=models.CASCADE, 
        related_name='monitoring_logs',
        verbose_name="مزرعه"
    )
    log_date = models.DateField(auto_now_add=True, verbose_name="تاریخ پایش")
    
    # پارامترهای اندازه‌گیری شده
    ph = models.FloatField(verbose_name="pH")
    ec = models.FloatField(verbose_name="EC (dS/m)")
    organic_matter = models.FloatField(verbose_name="ماده آلی (%)")
    moisture = models.FloatField(null=True, blank=True, verbose_name="رطوبت (%)")
    temperature = models.FloatField(null=True, blank=True, verbose_name="دمای خاک (°C)")
    
    # شاخص سلامت
    soil_health_index = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="شاخص سلامت خاک (DSHI)"
    )
    
    # اطلاعات مکانی
    latitude = models.FloatField(verbose_name="عرض جغرافیایی")
    longitude = models.FloatField(verbose_name="طول جغرافیایی")
    
    # منبع داده
    source = models.CharField(max_length=50, default='FIELD', verbose_name="منبع داده")
    notes = models.TextField(blank=True, verbose_name="یادداشت‌ها")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "لاگ پایش خاک"
        verbose_name_plural = "لاگ‌های پایش خاک"
        ordering = ['-log_date']
    
    def __str__(self):
        return f"پایش {self.farm.name} - {self.log_date}"
    


class ExpertRequest(models.Model):
    """مدل درخواست اعزام کارشناس"""
    
    STATUS_CHOICES = [
        ('PENDING', 'در انتظار بررسی'),
        ('ACCEPTED', 'پذیرفته شده'),
        ('IN_PROGRESS', 'در حال انجام'),
        ('COMPLETED', 'انجام شده'),
        ('REJECTED', 'رد شده'),
    ]
    
    farmer = models.ForeignKey(
        'accounts.Farmer',
        on_delete=models.CASCADE,
        related_name='expert_requests',
        verbose_name="کشاورز"
    )
    farm = models.ForeignKey(
        'Farm',
        on_delete=models.CASCADE,
        related_name='expert_requests',
        verbose_name="مزرعه"
    )
    expert = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_requests',
        verbose_name="کارشناس"
    )
    
    title = models.CharField(max_length=200, verbose_name="عنوان درخواست")
    description = models.TextField(verbose_name="توضیحات")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="وضعیت"
    )
    
    # اطلاعات مکانی
    latitude = models.FloatField(null=True, blank=True, verbose_name="عرض جغرافیایی")
    longitude = models.FloatField(null=True, blank=True, verbose_name="طول جغرافیایی")
    
    # زمان‌بندی
    preferred_date = models.DateField(null=True, blank=True, verbose_name="تاریخ ترجیحی")
    preferred_time = models.TimeField(null=True, blank=True, verbose_name="ساعت ترجیحی")
    
    # پاسخ کارشناس
    expert_response = models.TextField(blank=True, verbose_name="پاسخ کارشناس")
    completion_note = models.TextField(blank=True, verbose_name="یادداشت تکمیل")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "درخواست کارشناس"
        verbose_name_plural = "درخواست‌های کارشناس"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.farmer.user.get_full_name()}"
    
    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    


class ClimateData(models.Model):
    """مدل داده‌های اقلیمی برای هر منطقه"""
    
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        related_name='climate_data',
        verbose_name="استان"
    )
    month = models.IntegerField(verbose_name="ماه (۱-۱۲)")
    year = models.IntegerField(verbose_name="سال")
    
    # داده‌های اقلیمی
    avg_temperature = models.FloatField(verbose_name="میانگین دما (درجه سانتی‌گراد)")
    min_temperature = models.FloatField(verbose_name="حداقل دما (درجه سانتی‌گراد)")
    max_temperature = models.FloatField(verbose_name="حداکثر دما (درجه سانتی‌گراد)")
    rainfall = models.FloatField(verbose_name="بارندگی (میلی‌متر)")
    humidity = models.FloatField(verbose_name="رطوبت نسبی (%)")
    sunny_days = models.IntegerField(verbose_name="تعداد روزهای آفتابی")
    
    # منبع داده
    source = models.CharField(max_length=100, default='SIMULATED', verbose_name="منبع داده")
    is_verified = models.BooleanField(default=False, verbose_name="تأیید شده")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "داده اقلیمی"
        verbose_name_plural = "داده‌های اقلیمی"
        unique_together = [['province', 'month', 'year']]
        ordering = ['-year', 'month']
    
    def __str__(self):
        return f"{self.province.name} - {self.year}/{self.month}"
    
class SoilHealthHistory(models.Model):
    """تاریخچه شاخص سلامت خاک برای هر مزرعه"""
    
    farm = models.ForeignKey(
        'Farm',
        on_delete=models.CASCADE,
        related_name='health_history',
        verbose_name="مزرعه"
    )
    analysis = models.ForeignKey(
        'SoilAnalysis',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='health_history',
        verbose_name="تحلیل مرتبط"
    )
    health_index = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="شاخص سلامت خاک (DSHI)"
    )
    health_level = models.CharField(
        max_length=20,
        choices=SoilAnalysis.SOIL_HEALTH_LEVELS,
        verbose_name="سطح سلامت"
    )
    
    # پارامترهای اصلی در زمان ثبت
    ph = models.FloatField(verbose_name="pH")
    ec = models.FloatField(verbose_name="EC (dS/m)")
    organic_matter = models.FloatField(verbose_name="ماده آلی (%)")
    
    record_date = models.DateField(auto_now_add=True, verbose_name="تاریخ ثبت")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "تاریخچه سلامت خاک"
        verbose_name_plural = "تاریخچه سلامت خاک"
        ordering = ['record_date']
    
    def __str__(self):
        return f"{self.farm.name} - {self.record_date} - {self.health_index}%"