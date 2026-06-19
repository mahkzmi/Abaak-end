from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Farmer, UserProfile, SubscriptionPlan, Subscription


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(write_only=True, required=True)
    national_id = serializers.CharField(write_only=True, required=True)
    role = serializers.ChoiceField(
            choices=['ADMIN', 'EXPERT', 'LAB', 'CRM', 'FARMER', 'VIEWER'],
            required=False,
            default='FARMER'
        )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name', 'phone', 'national_id', 'role']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'رمز عبور و تکرار آن مطابقت ندارند'})
        return attrs

    def create(self, validated_data):
        # حذف فیلدهای اضافی
        phone = validated_data.pop('phone')
        national_id = validated_data.pop('national_id')
        password2 = validated_data.pop('password2')
        role = validated_data.pop('role', 'FARMER')
        
        # ایجاد کاربر
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        user.set_password(validated_data['password'])
        user.save()
        
        # ایجاد پروفایل کشاورز
        farmer = Farmer.objects.create(
            user=user,
            national_id=national_id,
            phone=phone,
            address='',
            province=None,
            county=None,
        )
        
        # ایجاد UserProfile با نقش مشخص
        UserProfile.objects.create(
            user=user,
            role=role,
            phone=phone,
            is_verified=False,
        )
        
        return user


class FarmerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Farmer
        fields = '__all__'


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = '__all__'


class UserProfileDetailSerializer(serializers.ModelSerializer):
    """سریالایزر کامل برای پروفایل کاربر با اطلاعات مرتبط"""
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    first_name = serializers.ReadOnlyField(source='user.first_name')
    last_name = serializers.ReadOnlyField(source='user.last_name')
    full_name = serializers.SerializerMethodField()
    role_display = serializers.ReadOnlyField(source='get_role_display')
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'phone', 'is_verified', 'profile_picture',
            'province', 'county', 'created_at'
        ]
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """سریالایزر برای ویرایش پروفایل"""
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    email = serializers.EmailField(source='user.email', required=False)
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'first_name', 'last_name', 'email', 'province', 'county', 'profile_picture']
    
    def update(self, instance, validated_data):
        # به‌روزرسانی User
        user_data = validated_data.pop('user', {})
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
        
        # به‌روزرسانی UserProfile
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


# ==================== سریالایزرهای اشتراک ====================

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    plan_type_display = serializers.ReadOnlyField(source='get_plan_type_display')
    
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.ReadOnlyField(source='plan.name')
    plan_type = serializers.ReadOnlyField(source='plan.plan_type')
    plan_type_display = serializers.ReadOnlyField(source='plan.get_plan_type_display')
    user_name = serializers.ReadOnlyField(source='user.get_full_name')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'user', 'user_name', 'plan', 'plan_name', 'plan_type', 'plan_type_display',
            'status', 'status_display', 'start_date', 'end_date',
            'analyses_used', 'analyses_remaining', 'last_reset_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']