from django.contrib import admin
from .models import (
    Province, County, Farm, SoilSample, SoilAnalysis,
    CropRecommendation, FertilizerRecommendation, SoilMonitoringLog, ExpertRequest
)


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'province']
    list_filter = ['province']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ['name', 'farmer', 'area', 'get_area_display', 'province', 'county', 'created_at']
    list_filter = ['province', 'county', 'is_active']
    search_fields = ['name', 'farmer__user__first_name', 'farmer__user__last_name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_area_display(self, obj):
        return f"{obj.area:.2f} هکتار"
    get_area_display.short_description = "مساحت"


@admin.register(SoilSample)
class SoilSampleAdmin(admin.ModelAdmin):
    list_display = ['sample_code', 'farm', 'sampling_date', 'ph', 'ec', 'organic_matter', 'texture', 'source']
    list_filter = ['source', 'texture', 'is_verified', 'sampling_date']
    search_fields = ['sample_code', 'farm__name', 'laboratory_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-sampling_date']


@admin.register(SoilAnalysis)
class SoilAnalysisAdmin(admin.ModelAdmin):
    list_display = ['soil_sample', 'soil_health_index', 'soil_health_level', 'expected_yield', 'expected_profit', 'created_at']
    list_filter = ['soil_health_level', 'is_finalized']
    search_fields = ['soil_sample__sample_code', 'soil_sample__farm__name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(CropRecommendation)
class CropRecommendationAdmin(admin.ModelAdmin):
    list_display = ['crop_name', 'analysis', 'suitability_score', 'predicted_yield', 'predicted_profit']
    list_filter = ['crop_name']
    search_fields = ['crop_name']
    ordering = ['-suitability_score']


@admin.register(FertilizerRecommendation)
class FertilizerRecommendationAdmin(admin.ModelAdmin):
    list_display = ['fertilizer_type', 'crop_recommendation', 'amount', 'cost_per_hectare']
    list_filter = ['fertilizer_type']
    search_fields = ['fertilizer_type']


@admin.register(SoilMonitoringLog)
class SoilMonitoringLogAdmin(admin.ModelAdmin):
    list_display = ['farm', 'log_date', 'ph', 'ec', 'organic_matter', 'soil_health_index']
    list_filter = ['log_date']
    search_fields = ['farm__name']
    ordering = ['-log_date']

@admin.register(ExpertRequest)
class ExpertRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'farmer', 'farm', 'status', 'expert', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'description', 'farmer__user__first_name', 'farmer__user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']