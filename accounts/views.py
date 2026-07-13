from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


from .models import Farmer, Company, UserProfile, Subscription, SubscriptionPlan
from .serializers import (
    RegisterSerializer, UserSerializer, FarmerSerializer, UserProfileSerializer,
    UserProfileDetailSerializer, ProfileUpdateSerializer,
    SubscriptionPlanSerializer, SubscriptionSerializer
)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="ثبت‌نام کاربر جدید",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'password', 'password2', 'phone', 'national_id'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='نام کاربری'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='ایمیل (اختیاری)'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='رمز عبور'),
                'password2': openapi.Schema(type=openapi.TYPE_STRING, description='تکرار رمز عبور'),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='نام (اختیاری)'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='نام خانوادگی (اختیاری)'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='شماره موبایل'),
                'national_id': openapi.Schema(type=openapi.TYPE_STRING, description='کد ملی'),
                'role': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['EXPERT', 'LAB', 'FARMER', 'VIEWER'],
                    description='نقش کاربر (پیش‌فرض: FARMER)'
                ),
            }
        ),
        responses={
            201: openapi.Response('ثبت‌نام با موفقیت انجام شد'),
            400: openapi.Response('داده‌های ورودی نامعتبر'),
        }
    )
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'success': True,
                'message': 'ثبت‌نام با موفقیت انجام شد',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'success': True, 'message': 'با موفقیت خارج شدید'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        



class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        profile = user.profile if hasattr(user, 'profile') else None
        data = UserSerializer(user).data
        if profile:
            data['role'] = profile.role
            data['role_display'] = profile.get_role_display()
            data['phone'] = profile.phone
            data['is_verified'] = profile.is_verified
        return Response(data)
    
    def put(self, request):
        user = request.user
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name = request.data.get('last_name', user.last_name)
        user.email = request.data.get('email', user.email)
        user.save()
        
        # به‌روزرسانی پروفایل
        if hasattr(user, 'profile'):
            profile = user.profile
            profile.phone = request.data.get('phone', profile.phone)
            profile.save()
        
        return Response(UserSerializer(user).data)
    

from django.shortcuts import get_object_or_404
from soil.models import Farm, SoilSample, SoilAnalysis
from soil.serializers import FarmSerializer, SoilSampleSerializer, SoilAnalysisSerializer


class ProfileDetailView(APIView):
    """دریافت اطلاعات کامل پروفایل کاربر"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        profile = request.user.profile if hasattr(request.user, 'profile') else None
        if not profile:
            return Response({'error': 'پروفایل یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)


class ProfileUpdateView(APIView):
    """ویرایش اطلاعات پروفایل کاربر"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        profile = request.user.profile if hasattr(request.user, 'profile') else None
        if not profile:
            return Response({'error': 'پروفایل یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'اطلاعات با موفقیت به‌روزرسانی شد',
                'data': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserFarmsView(APIView):
    """دریافت لیست مزارع کاربر"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            farmer = request.user.farmer_profile
            farms = Farm.objects.filter(farmer=farmer).order_by('-created_at')
            serializer = FarmSerializer(farms, many=True)
            return Response(serializer.data)
        except:
            return Response({'error': 'کشاورز یافت نشد'}, status=status.HTTP_404_NOT_FOUND)


class UserAnalysesView(APIView):
    """دریافت تاریخچه تحلیل‌های کاربر"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            farmer = request.user.farmer_profile
            farms = Farm.objects.filter(farmer=farmer)
            soil_samples = SoilSample.objects.filter(farm__in=farms).order_by('-created_at')
            
            results = []
            for sample in soil_samples:
                try:
                    analysis = SoilAnalysis.objects.get(soil_sample=sample)
                    results.append({
                        'sample': SoilSampleSerializer(sample).data,
                        'analysis': SoilAnalysisSerializer(analysis).data
                    })
                except SoilAnalysis.DoesNotExist:
                    results.append({
                        'sample': SoilSampleSerializer(sample).data,
                        'analysis': None
                    })
            
            return Response(results)
        except:
            return Response({'error': 'کشاورز یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        

class SubscriptionListView(APIView):
    """دریافت لیست طرح‌های اشتراک"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        from .models import SubscriptionPlan
        from .serializers import SubscriptionPlanSerializer
        
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)


class UserSubscriptionView(APIView):
    """دریافت وضعیت اشتراک کاربر فعلی"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from .models import Subscription, SubscriptionPlan
        from .serializers import SubscriptionSerializer
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            subscription = request.user.subscription
            serializer = SubscriptionSerializer(subscription)
            data = serializer.data
            data['can_analyze'] = subscription.can_analyze()
            data['analyses_remaining'] = subscription.analyses_remaining
            return Response(data)
        except:
            # اگر اشتراکی وجود نداشت، اشتراک رایگان ایجاد کن
            free_plan = SubscriptionPlan.objects.get(plan_type='FREE')
            subscription = Subscription.objects.create(
                user=request.user,
                plan=free_plan,
                analyses_remaining=free_plan.monthly_analyses,
                end_date=timezone.now() + timedelta(days=30)
            )
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data)


class PurchaseSubscriptionView(APIView):
    """خرید اشتراک جدید (شبیه‌سازی پرداخت)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from .models import Subscription, SubscriptionPlan
        from .serializers import SubscriptionSerializer
        from django.utils import timezone
        from datetime import timedelta
        
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response({'error': 'شناسه طرح الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'طرح مورد نظر یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
        
        # ایجاد یا به‌روزرسانی اشتراک
        subscription, created = Subscription.objects.get_or_create(
            user=request.user,
            defaults={
                'plan': plan,
                'analyses_remaining': plan.monthly_analyses,
                'status': 'ACTIVE',
                'end_date': timezone.now() + timedelta(days=30)
            }
        )
        
        if not created:
            subscription.plan = plan
            subscription.status = 'ACTIVE'
            subscription.analyses_used = 0
            subscription.analyses_remaining = plan.monthly_analyses
            subscription.end_date = timezone.now() + timedelta(days=30)
            subscription.save()
        
        # سریالایزر رو با context درست صدا بزن
        serializer = SubscriptionSerializer(subscription, context={'request': request})
        return Response({
            'success': True,
            'message': f'اشتراک {plan.name} با موفقیت خریداری شد',
            'subscription': serializer.data
        })
    

from soil.models import Farm, SoilSample, SoilAnalysis
from django.db.models import Count, Avg

class DashboardStatsView(APIView):
    """دریافت آمار داشبورد کاربر"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            farmer = request.user.farmer_profile
            farms = Farm.objects.filter(farmer=farmer)
            
            # آمار پایه
            total_farms = farms.count()
            total_analyses = SoilAnalysis.objects.filter(
                soil_sample__farm__in=farms
            ).count()
            
            # آخرین تحلیل
            last_analysis = SoilAnalysis.objects.filter(
                soil_sample__farm__in=farms
            ).order_by('-created_at').first()
            
            last_analysis_data = None
            if last_analysis:
                last_analysis_data = {
                    'id': last_analysis.id,
                    'farm_name': last_analysis.soil_sample.farm.name,
                    'soil_health_index': last_analysis.soil_health_index,
                    'soil_health_level': last_analysis.soil_health_level,
                    'created_at': last_analysis.created_at,
                }
            
            # میانگین سلامت خاک
            avg_health = SoilAnalysis.objects.filter(
                soil_sample__farm__in=farms
            ).aggregate(avg=Avg('soil_health_index'))['avg'] or 0
            
            # سطح سلامت غالب
            health_levels = SoilAnalysis.objects.filter(
                soil_sample__farm__in=farms
            ).values('soil_health_level').annotate(count=Count('id')).order_by('-count')
            
            dominant_health = health_levels[0]['soil_health_level'] if health_levels else 'NO_DATA'
            health_display = dict(SoilAnalysis.SOIL_HEALTH_LEVELS).get(dominant_health, 'نامشخص')
            
            # وضعیت اشتراک
            subscription = getattr(request.user, 'subscription', None)
            subscription_data = None
            if subscription:
                subscription_data = {
                    'plan_name': subscription.plan.name,
                    'plan_type': subscription.plan.plan_type,
                    'status': subscription.status,
                    'status_display': subscription.get_status_display(),
                    'analyses_remaining': subscription.analyses_remaining,
                    'can_analyze': subscription.can_analyze(),
                }
            
            return Response({
                'total_farms': total_farms,
                'total_analyses': total_analyses,
                'avg_health': round(avg_health, 1),
                'dominant_health': health_display,
                'last_analysis': last_analysis_data,
                'subscription': subscription_data,
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
