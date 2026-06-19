from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Farmer, Company, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'پروفایل کاربر'


class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return 'نامشخص'
    get_role.short_description = 'نقش'


# ثبت مجدد User با ادمین سفارشی
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ['user', 'national_id', 'phone', 'province', 'county', 'is_active']
    list_filter = ['is_active', 'province', 'county']
    search_fields = ['user__first_name', 'user__last_name', 'national_id', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'registration_number', 'economic_code', 'phone', 'province', 'is_active']
    list_filter = ['is_active', 'province']
    search_fields = ['name', 'registration_number', 'economic_code']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']


# ============ حذف این بخش ============
# @admin.register(UserProfile)  # ← این خط رو کامنت کن یا پاک کن
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = ['user', 'role', 'phone', 'is_verified']
#     list_filter = ['role', 'is_verified']
#     search_fields = ['user__username', 'user__first_name', 'user__last_name', 'phone']

from .models import SubscriptionPlan, Subscription

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price', 'monthly_analyses', 'is_active']
    list_filter = ['plan_type', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['price']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'analyses_used', 'analyses_remaining', 'end_date']
    list_filter = ['status', 'plan']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']