from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Province, County, Farm, SoilSample, 
    SoilAnalysis, CropRecommendation, FertilizerRecommendation, ExpertRequest, SoilHealthHistory
)


class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ['id', 'name', 'code']


class CountySerializer(serializers.ModelSerializer):
    province_name = serializers.ReadOnlyField(source='province.name')
    
    class Meta:
        model = County
        fields = ['id', 'name', 'code', 'province', 'province_name']


class FarmSerializer(serializers.ModelSerializer):
    farmer_name = serializers.ReadOnlyField(source='farmer.user.get_full_name')
    area_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Farm
        fields = ['id', 'name', 'farmer', 'farmer_name', 'area', 'area_display', 
                  'geometry_coords', 'address', 'province', 'county', 'created_at']
        # توجه: geometry رو برداشتم و geometry_coords رو جایگزین کردم
    
    def get_area_display(self, obj):
        return f"{obj.area:.2f} هکتار"
    def get_geometry_coords(self, obj):
        """بازگرداندن مختصات پلی‌گون به صورت لیست برای استفاده در نقشه"""
        if obj.geometry:
            coords = obj.geometry.coords[0]
            return [[lng, lat] for lng, lat in coords]  # [[lng, lat], ...]
        return []

class SoilSampleSerializer(serializers.ModelSerializer):
    farm_name = serializers.ReadOnlyField(source='farm.name')
    texture_display = serializers.ReadOnlyField(source='get_texture_display')
    
    class Meta:
        model = SoilSample
        fields = '__all__'
        read_only_fields = [
            'created_at', 'updated_at', 'is_verified', 'verified_by',
            'verified_at', 'rejection_reason', 'validation_warnings',
            'source', 'laboratory_name',
        ]



class SoilAnalysisInputSerializer(serializers.Serializer):
    """سریالایزر برای ورودی تحلیل خاک"""
    farm_id = serializers.IntegerField(required=False, help_text="شناسه مزرعه (اختیاری)")
    ph = serializers.FloatField(required=True, help_text="pH خاک (۰ تا ۱۴)")
    ec = serializers.FloatField(required=True, help_text="EC (dS/m)")
    organic_matter = serializers.FloatField(required=True, help_text="ماده آلی (%)")
    nitrogen = serializers.FloatField(required=False, allow_null=True, help_text="نیتروژن (ppm)")
    phosphorus = serializers.FloatField(required=False, allow_null=True, help_text="فسفر (ppm)")
    potassium = serializers.FloatField(required=False, allow_null=True, help_text="پتاسیم (ppm)")
    texture = serializers.ChoiceField(
        choices=['SANDY', 'LOAMY_SAND', 'SANDY_LOAM', 'LOAM', 
                 'SILT_LOAM', 'SILT', 'CLAY_LOAM', 'SILTY_CLAY_LOAM', 'CLAY'],
        required=True,
        help_text="بافت خاک"
    )
    latitude = serializers.FloatField(required=False, allow_null=True, help_text="عرض جغرافیایی")
    longitude = serializers.FloatField(required=False, allow_null=True, help_text="طول جغرافیایی")
    
    # عناصر ریزمغذی
    iron = serializers.FloatField(required=False, allow_null=True, help_text="آهن (Fe) (ppm)")
    zinc = serializers.FloatField(required=False, allow_null=True, help_text="روی (Zn) (ppm)")
    manganese = serializers.FloatField(required=False, allow_null=True, help_text="منگنز (Mn) (ppm)")
    copper = serializers.FloatField(required=False, allow_null=True, help_text="مس (Cu) (ppm)")

    

class CropRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropRecommendation
        fields = '__all__'


class FertilizerRecommendationSerializer(serializers.ModelSerializer):
    fertilizer_type_display = serializers.ReadOnlyField(source='get_fertilizer_type_display')
    
    class Meta:
        model = FertilizerRecommendation
        fields = '__all__'


class SoilAnalysisSerializer(serializers.ModelSerializer):
    sample_code = serializers.ReadOnlyField(source='soil_sample.sample_code')
    farm_name = serializers.ReadOnlyField(source='soil_sample.farm.name')
    crop_recommendations = CropRecommendationSerializer(many=True, read_only=True)
    fertilizer_recommendations = FertilizerRecommendationSerializer(many=True, read_only=True)
    health_level_display = serializers.ReadOnlyField(source='get_health_level_display')
    
    class Meta:
        model = SoilAnalysis
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class SoilAnalysisInputSerializer(serializers.Serializer):
    """سریالایزر برای ورودی تحلیل خاک"""
    farm_id = serializers.IntegerField(required=False, help_text="شناسه مزرعه (اختیاری)")
    ph = serializers.FloatField(required=True, help_text="pH خاک (۰ تا ۱۴)")
    ec = serializers.FloatField(required=True, help_text="EC (dS/m)")
    organic_matter = serializers.FloatField(required=True, help_text="ماده آلی (%)")
    nitrogen = serializers.FloatField(required=False, help_text="نیتروژن (ppm)")
    phosphorus = serializers.FloatField(required=False, help_text="فسفر (ppm)")
    potassium = serializers.FloatField(required=False, help_text="پتاسیم (ppm)")
    texture = serializers.ChoiceField(
        choices=['SANDY', 'LOAMY_SAND', 'SANDY_LOAM', 'LOAM', 
                 'SILT_LOAM', 'SILT', 'CLAY_LOAM', 'SILTY_CLAY_LOAM', 'CLAY'],
        required=True,
        help_text="بافت خاک"
    )
    latitude = serializers.FloatField(required=False, help_text="عرض جغرافیایی")
    longitude = serializers.FloatField(required=False, help_text="طول جغرافیایی")



class LabSampleInputSerializer(serializers.Serializer):
    """سریالایزر برای ورود داده از آزمایشگاه"""
    sample_code = serializers.CharField(max_length=50, required=True, help_text="کد نمونه")
    farm_id = serializers.IntegerField(required=False, help_text="شناسه مزرعه (اختیاری)")
    farm_name = serializers.CharField(max_length=200, required=False, help_text="نام مزرعه (اگر مزرعه جدید است)")
    farmer_name = serializers.CharField(max_length=200, required=False, help_text="نام کشاورز")
    farmer_phone = serializers.CharField(max_length=11, required=False, help_text="شماره موبایل کشاورز")
    
    # پارامترهای خاک
    sampling_date = serializers.DateField(required=True)
    depth = serializers.FloatField(required=True, help_text="عمق (سانتی‌متر)")
    ph = serializers.FloatField(required=True)
    ec = serializers.FloatField(required=True)
    organic_matter = serializers.FloatField(required=True)
    nitrogen = serializers.FloatField(required=False)
    phosphorus = serializers.FloatField(required=False)
    potassium = serializers.FloatField(required=False)
    texture = serializers.ChoiceField(
        choices=['SANDY', 'LOAMY_SAND', 'SANDY_LOAM', 'LOAM', 
                 'SILT_LOAM', 'SILT', 'CLAY_LOAM', 'SILTY_CLAY_LOAM', 'CLAY'],
        required=True
    )
    
    # اطلاعات مکانی
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    
    # اطلاعات آزمایشگاه
    laboratory_name = serializers.CharField(max_length=200, required=True)

class LabSampleInputSerializer(serializers.Serializer):
    """سریالایزر برای ورود داده از آزمایشگاه"""
    # فیلدهای اجباری
    sample_code = serializers.CharField(max_length=50, required=True)
    sampling_date = serializers.DateField(required=True)
    ph = serializers.FloatField(required=True)
    ec = serializers.FloatField(required=True)
    organic_matter = serializers.FloatField(required=True)
    texture = serializers.ChoiceField(
        choices=['SANDY', 'LOAMY_SAND', 'SANDY_LOAM', 'LOAM', 
                 'SILT_LOAM', 'SILT', 'CLAY_LOAM', 'SILTY_CLAY_LOAM', 'CLAY'],
        required=True
    )
    laboratory_name = serializers.CharField(max_length=200, required=True)
    
    # فیلدهای اختیاری (با required=False و allow_null=True)
    farm_id = serializers.IntegerField(required=False, allow_null=True)
    farm_name = serializers.CharField(max_length=200, required=False, allow_null=True, allow_blank=True)
    farmer_name = serializers.CharField(max_length=200, required=False, allow_null=True, allow_blank=True)
    farmer_phone = serializers.CharField(max_length=11, required=False, allow_null=True, allow_blank=True)
    
    depth = serializers.FloatField(required=False, allow_null=True)
    nitrogen = serializers.FloatField(required=False, allow_null=True)
    phosphorus = serializers.FloatField(required=False, allow_null=True)
    potassium = serializers.FloatField(required=False, allow_null=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

class ExpertRequestSerializer(serializers.ModelSerializer):
    farmer_name = serializers.ReadOnlyField(source='farmer.user.get_full_name')
    farm_name = serializers.ReadOnlyField(source='farm.name')
    expert_name = serializers.SerializerMethodField()
    status_display = serializers.ReadOnlyField(source='get_status_display')
    
    class Meta:
        model = ExpertRequest
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_expert_name(self, obj):
        if obj.expert:
            return obj.expert.user.get_full_name()
        return None


class ExpertRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpertRequest
        fields = ['farm', 'title', 'description', 'latitude', 'longitude', 'preferred_date', 'preferred_time']


class SoilHealthHistorySerializer(serializers.ModelSerializer):
    health_level_display = serializers.ReadOnlyField(source='get_health_level_display')
    farm_name = serializers.ReadOnlyField(source='farm.name')
    
    class Meta:
        model = SoilHealthHistory
        fields = '__all__'