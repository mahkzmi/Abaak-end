"""
views.py - کنترلرهای API سامانه آباک
"""

import io
import re
import logging
import time
import traceback
import math

from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

import pandas as pd
from xhtml2pdf import pisa

from accounts.permissions import (
    IsAdmin, IsExpert, IsLab, IsFarmer,
    IsAdminOrExpert, IsLabOrExpert, IsVerifiedLabSample
)
from accounts.models import Farmer, UserProfile

from .models import (
    Province, County, Farm, SoilSample, SoilAnalysis,
    CropRecommendation, ExpertRequest, SoilHealthHistory
)
from .serializers import (
    ProvinceSerializer, CountySerializer, FarmSerializer,
    SoilSampleSerializer, SoilAnalysisSerializer, SoilAnalysisInputSerializer,
    LabSampleInputSerializer, ExpertRequestSerializer, ExpertRequestCreateSerializer
)
from .analysis_engine import SoilAnalysisEngine

logger = logging.getLogger(__name__)


# ================================================================
# 1. توابع اعتبارسنجی
# ================================================================

def validate_soil_data(data):
    """اعتبارسنجی داده‌های خاک برای جلوگیری از حملات"""
    errors = []

    for field, value in data.items():
        if isinstance(value, str):
            cleaned = re.sub(r'[<>\'";]', '', value)
            if cleaned != value:
                errors.append(f"کاراکترهای غیرمجاز در فیلد {field}")

    if 'ph' in data and data['ph'] is not None:
        try:
            ph = float(data['ph'])
            if ph < 0 or ph > 14:
                errors.append("pH باید بین ۰ تا ۱۴ باشد")
        except (ValueError, TypeError):
            errors.append("pH نامعتبر است")

    if 'ec' in data and data['ec'] is not None:
        try:
            ec = float(data['ec'])
            if ec < 0:
                errors.append("EC باید مثبت باشد")
        except (ValueError, TypeError):
            errors.append("EC نامعتبر است")

    if 'organic_matter' in data and data['organic_matter'] is not None:
        try:
            om = float(data['organic_matter'])
            if om < 0:
                errors.append("ماده آلی باید مثبت باشد")
        except (ValueError, TypeError):
            errors.append("ماده آلی نامعتبر است")

    if errors:
        raise ValidationError(errors)

    return data


# ================================================================
# 2. کلاس‌های View (صفحات HTML)
# ================================================================

class ExpertDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    پنل کارشناس - فقط کاربران با نقش EXPERT یا ADMIN دسترسی دارند
    """
    template_name = 'soil/expert_dashboard.html'
    
    def test_func(self):
        """بررسی دسترسی کاربر"""
        user = self.request.user
        if not user.is_authenticated:
            return False
        
        try:
            profile = UserProfile.objects.get(user=user)
            return profile.role in ['EXPERT', 'ADMIN']
        except UserProfile.DoesNotExist:
            return user.is_superuser
    
    def handle_no_permission(self):
        return redirect_to_user_dashboard(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


def redirect_to_user_dashboard(user):
    """هدایت کاربر به داشبورد مناسب بر اساس نقش"""
    try:
        profile = UserProfile.objects.get(user=user)
        role = profile.role
        role_redirects = {
            'FARMER': '/map/',
            'LAB': '/lab/',
            'EXPERT': '/expert/dashboard/',
            'ADMIN': '/admin/',
            'CRM': '/expert-request/',
        }
        return HttpResponseRedirect(role_redirects.get(role, '/'))
    except UserProfile.DoesNotExist:
        return HttpResponseRedirect('/')


def expert_dashboard(request):
    """نمایش پنل کارشناس (Fallback)"""
    if not request.user.is_authenticated:
        return redirect_to_login()
    
    try:
        profile = UserProfile.objects.get(user=request.user)
        if profile.role not in ['EXPERT', 'ADMIN']:
            return redirect_to_user_dashboard(request.user)
    except UserProfile.DoesNotExist:
        if not request.user.is_superuser:
            return redirect_to_user_dashboard(request.user)
    
    return render(request, 'soil/expert_dashboard.html')


# ================================================================
# 3. ViewSet استان‌ها و شهرستان‌ها
# ================================================================

class ProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Province.objects.all().order_by('name')
    serializer_class = ProvinceSerializer
    permission_classes = [AllowAny]


class CountyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CountySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        province_id = self.request.query_params.get('province_id')
        if province_id:
            return County.objects.filter(province_id=province_id).order_by('name')
        return County.objects.all().order_by('name')


# ================================================================
# 4. ViewSet نمونه‌های خاک
# ================================================================

class SoilSampleViewSet(viewsets.ModelViewSet):
    serializer_class = SoilSampleSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminOrExpert()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'profile', None)
        role = profile.role if profile else None
        if user.is_superuser or role in ['ADMIN', 'EXPERT']:
            return SoilSample.objects.all().order_by('-sampling_date')
        if role == 'FARMER':
            return SoilSample.objects.filter(farm__farmer__user=user).order_by('-sampling_date')
        if role == 'LAB' and profile.is_verified:
            return SoilSample.objects.filter(source='LAB').order_by('-sampling_date')
        return SoilSample.objects.none()

    def perform_create(self, serializer):
        farm = serializer.validated_data['farm']
        user = self.request.user
        profile = getattr(user, 'profile', None)
        role = profile.role if profile else None
        if not (user.is_superuser or role in ['ADMIN', 'EXPERT']):
            if role != 'FARMER' or farm.farmer.user_id != user.id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('اجازه ثبت نمونه برای این مزرعه را ندارید.')
        serializer.save(source='FIELD')


# ================================================================
# 5. ViewSet مزارع
# ================================================================

class FarmViewSet(viewsets.ModelViewSet):
    queryset = Farm.objects.all().order_by('-created_at')
    serializer_class = FarmSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'profile', None)
        role = profile.role if profile else None
        if user.is_superuser or role in ['ADMIN', 'EXPERT']:
            return Farm.objects.all().order_by('-created_at')
        try:
            farmer = user.farmer_profile
            return Farm.objects.filter(farmer=farmer).order_by('-created_at')
        except (AttributeError, Farmer.DoesNotExist):
            return Farm.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        profile = getattr(user, 'profile', None)
        if not profile or profile.role != 'FARMER':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('فقط حساب کشاورز مجاز به ثبت مزرعه است.')
        try:
            farmer = user.farmer_profile
        except Farmer.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('حساب کاربری به پروفایل کشاورز متصل نیست.')
        serializer.save(farmer=farmer)

    @action(detail=True, methods=['put'], url_path='update')
    def update_farm(self, request, pk=None):
        farm = get_object_or_404(Farm, pk=pk)

        if farm.farmer.user != request.user:
            return Response(
                {'error': 'شما دسترسی به این مزرعه ندارید'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data
        farm.name = data.get('name', farm.name)
        farm.address = data.get('address', farm.address)
        farm.area = data.get('area', farm.area)

        province_name = data.get('province')
        if province_name:
            province, _ = Province.objects.get_or_create(
                name=province_name,
                defaults={'code': province_name[:3].upper()}
            )
            farm.province = province

        farm.save()
        serializer = FarmSerializer(farm)
        return Response({
            'success': True,
            'message': 'مزرعه با موفقیت به‌روزرسانی شد',
            'farm': serializer.data
        })

    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_farm(self, request, pk=None):
        farm = get_object_or_404(Farm, pk=pk)

        if farm.farmer.user != request.user:
            return Response(
                {'error': 'شما دسترسی به این مزرعه ندارید'},
                status=status.HTTP_403_FORBIDDEN
            )

        farm_name = farm.name
        farm.delete()
        return Response({
            'success': True,
            'message': f'مزرعه {farm_name} با موفقیت حذف شد'
        })


# ================================================================
# 6. ViewSet اصلی تحلیل خاک
# ================================================================

@method_decorator(csrf_exempt, name='dispatch')
class SoilAnalysisViewSet(viewsets.ModelViewSet):
    queryset = SoilAnalysis.objects.all().order_by('-created_at')
    serializer_class = SoilAnalysisSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return SoilAnalysis.objects.none()
        profile = getattr(user, 'profile', None)
        role = profile.role if profile else None
        queryset = SoilAnalysis.objects.select_related('soil_sample__farm__farmer__user')
        if user.is_superuser or role in ['ADMIN', 'EXPERT']:
            return queryset.order_by('-created_at')
        if role == 'FARMER':
            return queryset.filter(soil_sample__farm__farmer__user=user).order_by('-created_at')
        if role == 'LAB' and profile.is_verified:
            return queryset.filter(soil_sample__source='LAB').order_by('-created_at')
        return SoilAnalysis.objects.none()

    def get_permissions(self):
        permission_map = {
            'lab_register_sample': IsVerifiedLabSample,
            'upload_bulk_samples': IsVerifiedLabSample,
            'verify_sample': IsAdminOrExpert,
            'reject_sample': IsAdminOrExpert,
            'pending_verification': IsAdminOrExpert,
            'verification_stats': IsAdminOrExpert,
            'create_farm': IsAuthenticated,
            'create': IsAdminOrExpert,
            'update': IsAdminOrExpert,
            'partial_update': IsAdminOrExpert,
            'destroy': IsAdminOrExpert,
            'lab_list_samples': IsLabOrExpert,
            'generate_pdf': IsAuthenticated,
            'sample_details': IsAuthenticated,
            'health_history': IsAuthenticated,
            'analyze_soil': IsAuthenticated,
            'expert_requests_list': IsAdminOrExpert,
            'accept_expert_request': IsAdminOrExpert,
            'reject_expert_request': IsAdminOrExpert,
            'complete_expert_request': IsAdminOrExpert,
        }
        permission_class = permission_map.get(self.action, IsAuthenticated)
        return [permission_class()]

    # ===================== تاریخچه سلامت خاک =====================

    @action(detail=False, methods=['get'], url_path='health-history')
    def health_history(self, request):
        farm_id = request.query_params.get('farm_id')
        if not farm_id:
            return Response(
                {'error': 'شناسه مزرعه الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            farm = get_object_or_404(Farm, id=farm_id)
            profile = getattr(request.user, 'profile', None)
            role = profile.role if profile else None
            if not (
                request.user.is_superuser
                or role in ['ADMIN', 'EXPERT']
                or farm.farmer.user_id == request.user.id
            ):
                return Response(
                    {'error': 'شما به تاریخچه این مزرعه دسترسی ندارید'},
                    status=status.HTTP_403_FORBIDDEN
                )
            history = SoilHealthHistory.objects.filter(farm=farm).order_by('record_date')

            data = {
                'farm_name': farm.name,
                'history': [
                    {
                        'date': h.record_date.strftime('%Y-%m-%d'),
                        'health_index': h.health_index,
                        'health_level': h.get_health_level_display(),
                        'ph': h.ph,
                        'ec': h.ec,
                        'organic_matter': h.organic_matter,
                    }
                    for h in history
                ]
            }

            if len(data['history']) >= 2:
                first = data['history'][0]['health_index']
                last = data['history'][-1]['health_index']
                data['trend'] = 'improving' if last > first else 'declining' if last < first else 'stable'
                data['trend_percent'] = round(((last - first) / first) * 100, 1) if first > 0 else 0
            else:
                data['trend'] = 'insufficient_data'
                data['trend_percent'] = 0

            return Response(data)

        except Exception as e:
            logger.error(f"خطا در دریافت تاریخچه سلامت: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ===================== ثبت مزرعه =====================

    @action(detail=False, methods=['post'], url_path='create-farm')
    def create_farm(self, request):
        logger.info(f"📥 داده دریافتی create-farm: {request.data}")

        user = request.user
        if not user.is_authenticated:
            return Response(
                {'error': 'برای ثبت مزرعه ابتدا وارد حساب کاربری شوید'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        profile = getattr(user, 'profile', None)
        if not profile or profile.role != 'FARMER':
            return Response(
                {'error': 'فقط حساب کشاورز مجاز به ثبت مزرعه است.'},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            farmer = user.farmer_profile
        except Farmer.DoesNotExist:
            return Response(
                {'error': 'پروفایل کشاورز برای این حساب ثبت نشده است.'},
                status=status.HTTP_403_FORBIDDEN
            )

        farm_name = request.data.get('name')
        coordinates = request.data.get('coordinates')
        address = request.data.get('address', '')
        province_name = request.data.get('province')

        if not farm_name:
            return Response(
                {'error': 'نام مزرعه الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not coordinates or len(coordinates) < 4:
            return Response(
                {'error': f'حداقل ۴ نقطه نیاز است. دریافت شد: {len(coordinates) if coordinates else 0}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if isinstance(coordinates[0], list) and len(coordinates[0]) == 2:
                if isinstance(coordinates[0][0], (int, float)):
                    polygon_coords = coordinates
                else:
                    polygon_coords = [[lng, lat] for lat, lng in coordinates]
            else:
                return Response(
                    {'error': 'فرمت مختصات نامعتبر است'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if polygon_coords[0] != polygon_coords[-1]:
                polygon_coords.append(polygon_coords[0])

            area = 0
            n = len(polygon_coords)
            for i in range(n - 1):
                x1, y1 = polygon_coords[i]
                x2, y2 = polygon_coords[i + 1]
                area += (x1 * y2 - x2 * y1)
            area = abs(area) / 2.0
            area_ha = max(area * 100, 0.01)

            logger.info(f"📐 مساحت محاسبه‌شده: {area_ha:.2f} هکتار")

            province = None
            if province_name:
                province, _ = Province.objects.get_or_create(
                    name=province_name,
                    defaults={'code': province_name[:3].upper()}
                )

            farm = Farm.objects.create(
                farmer=farmer,
                name=farm_name,
                area=area_ha,
                geometry_coords=polygon_coords,
                address=address or 'آدرس نامشخص',
                province=province,
                county=None,
            )

            logger.info(f"✅ مزرعه با ID {farm.id} برای کاربر {user.username} ثبت شد")

            serializer = FarmSerializer(farm)
            return Response({
                'success': True,
                'farm': serializer.data,
                'message': f'مزرعه {farm_name} با مساحت {area_ha:.2f} هکتار ثبت شد'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"❌ خطا در ثبت مزرعه: {e}")
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # ===================== تحلیل خاک با درون‌یابی =====================

    @swagger_auto_schema(
        operation_description="تحلیل خاک بر اساس داده‌های ورودی با درون‌یابی",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['ph', 'ec', 'organic_matter', 'texture'],
            properties={
                'farm_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='شناسه مزرعه (اختیاری)'),
                'ph': openapi.Schema(type=openapi.TYPE_NUMBER, description='pH خاک (۰ تا ۱۴)'),
                'ec': openapi.Schema(type=openapi.TYPE_NUMBER, description='هدایت الکتریکی (dS/m)'),
                'organic_matter': openapi.Schema(type=openapi.TYPE_NUMBER, description='ماده آلی (%)'),
                'nitrogen': openapi.Schema(type=openapi.TYPE_NUMBER, description='نیتروژن (ppm) - اختیاری'),
                'phosphorus': openapi.Schema(type=openapi.TYPE_NUMBER, description='فسفر (ppm) - اختیاری'),
                'potassium': openapi.Schema(type=openapi.TYPE_NUMBER, description='پتاسیم (ppm) - اختیاری'),
                'iron': openapi.Schema(type=openapi.TYPE_NUMBER, description='آهن (ppm) - اختیاری'),
                'zinc': openapi.Schema(type=openapi.TYPE_NUMBER, description='روی (ppm) - اختیاری'),
                'manganese': openapi.Schema(type=openapi.TYPE_NUMBER, description='منگنز (ppm) - اختیاری'),
                'copper': openapi.Schema(type=openapi.TYPE_NUMBER, description='مس (ppm) - اختیاری'),
                'texture': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['SANDY', 'LOAMY_SAND', 'SANDY_LOAM', 'LOAM', 'SILT_LOAM',
                          'SILT', 'CLAY_LOAM', 'SILTY_CLAY_LOAM', 'CLAY'],
                    description='بافت خاک'
                ),
                'latitude': openapi.Schema(type=openapi.TYPE_NUMBER, description='عرض جغرافیایی - اختیاری'),
                'longitude': openapi.Schema(type=openapi.TYPE_NUMBER, description='طول جغرافیایی - اختیاری'),
            }
        ),
        responses={
            200: openapi.Response('تحلیل با موفقیت انجام شد'),
            400: openapi.Response('داده‌های ورودی نامعتبر'),
            401: openapi.Response('احراز هویت نشده'),
            403: openapi.Response('تعداد تحلیل‌ها به پایان رسیده است'),
        }
    )
    @action(detail=False, methods=['post'], url_path='analyze')
    def analyze_soil(self, request):
        """
        تحلیل خاک بر اساس داده‌های ورودی با پشتیبانی از درون‌یابی
        """
        try:
            validated_data = validate_soil_data(request.data)
        except ValidationError as e:
            return Response({'errors': e.messages}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SoilAnalysisInputSerializer(data=validated_data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        farm_id = data.get('farm_id')
        farm = None
        province_name = None

        logger.info(f"🔍 شروع تحلیل خاک با داده‌ها: {data}")

        try:
            # دریافت مزرعه
            if farm_id:
                farm = get_object_or_404(Farm, id=farm_id)
                profile = getattr(request.user, 'profile', None)
                role = profile.role if profile else None
                if not (
                    request.user.is_superuser
                    or role in ['ADMIN', 'EXPERT']
                    or farm.farmer.user_id == request.user.id
                ):
                    return Response(
                        {'error': 'شما به این مزرعه دسترسی ندارید'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                province_name = farm.province.name if farm.province else 'تهران'
                if not farm.province:
                    logger.warning("⚠️ استان مشخص نشد، از تهران به عنوان پیش‌فرض استفاده شد")

            # ===== دریافت همه نمونه‌ها برای درون‌یابی =====
            all_samples = []
            try:
                verified_samples = SoilSample.objects.filter(is_verified=True)
                for sample in verified_samples:
                    all_samples.append({
                        'latitude': sample.latitude,
                        'longitude': sample.longitude,
                        'ph': sample.ph,
                        'ec': sample.ec,
                        'organic_matter': sample.organic_matter,
                        'nitrogen': sample.nitrogen,
                        'phosphorus': sample.phosphorus,
                        'potassium': sample.potassium,
                    })
                logger.info(f"📊 {len(all_samples)} نمونه برای درون‌یابی بارگذاری شد")
            except Exception as e:
                logger.warning(f"⚠️ خطا در بارگذاری نمونه‌ها: {e}")

            # ===== اجرای تحلیل با درون‌یابی =====
            result = SoilAnalysisEngine.analyze_soil(
                data,
                province_name,
            )
            logger.info(f"✅ تحلیل با موفقیت انجام شد. DSHI: {result['soil_health_index']}")

            # ذخیره نمونه خاک (همیشه جدید)
            if farm_id and farm:
                unique_code = f"ANALYSIS-{farm_id}-{int(time.time())}-{hash(str(data)) % 10000:04d}"

                soil_sample = SoilSample.objects.create(
                    farm=farm,
                    sample_code=unique_code,
                    sampling_date=timezone.now().date(),
                    depth=30,
                    ph=data['ph'],
                    ec=data['ec'],
                    organic_matter=data['organic_matter'],
                    nitrogen=data.get('nitrogen'),
                    phosphorus=data.get('phosphorus'),
                    potassium=data.get('potassium'),
                    texture=data['texture'],
                    latitude=data.get('latitude', 35.0),
                    longitude=data.get('longitude', 51.0),
                    source='ESTIMATED',
                    iron=data.get('iron'),
                    zinc=data.get('zinc'),
                    manganese=data.get('manganese'),
                    copper=data.get('copper'),
                )
                logger.info(f"📝 نمونه خاک جدید ایجاد شد: {soil_sample.sample_code}")

                analysis = SoilAnalysis.objects.create(
                    soil_sample=soil_sample,
                    soil_health_index=result['soil_health_index'],
                    soil_health_level=result['soil_health_level'],
                    recommended_crops=[
                        {
                            'name': rec['crop_name'],
                            'score': rec['suitability_score'],
                            'profit': rec.get('predicted_profit', 0),
                            'yield': rec.get('predicted_yield', 0),
                        }
                        for rec in result['recommended_crops'][:5]
                    ],
                    fertilizer_recommendations={
                        'main': result['recommended_crops'][0]['fertilizer_advice'] if result['recommended_crops'] else [],
                    },
                    irrigation_recommendations=result['recommended_crops'][0]['irrigation_advice'] if result['recommended_crops'] else '',
                    management_tips=result['summary'],
                    expected_yield=result['best_crop']['predicted_yield'] if result['best_crop'] else 0,
                    expected_profit=result['best_crop']['predicted_profit'] if result['best_crop'] else 0,
                )
                logger.info(f"📊 تحلیل جدید ایجاد شد: ID {analysis.id}")

                SoilHealthHistory.objects.create(
                    farm=farm,
                    analysis=analysis,
                    health_index=result['soil_health_index'],
                    health_level=result['soil_health_level'],
                    ph=data['ph'],
                    ec=data['ec'],
                    organic_matter=data['organic_matter'],
                )

                result['analysis_id'] = analysis.id
                result['sample_code'] = soil_sample.sample_code

            # ===== اضافه کردن درجه اطمینان به خروجی =====
            result['confidence'] = result.get('confidence', 70)

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"❌ خطا در تحلیل: {e}")
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ===================== تولید PDF انگلیسی =====================

    @action(detail=True, methods=['get'], url_path='pdf')
    def generate_pdf(self, request, pk=None):
        """
        Generate and download English PDF report
        """
        analysis = get_object_or_404(SoilAnalysis, pk=pk)
        sample = analysis.soil_sample
        farm = sample.farm
        profile = getattr(request.user, 'profile', None)
        role = profile.role if profile else None
        if not (
            request.user.is_superuser
            or role in ['ADMIN', 'EXPERT']
            or farm.farmer.user_id == request.user.id
        ):
            return Response(
                {'error': 'شما اجازه دریافت این گزارش را ندارید'},
                status=status.HTTP_403_FORBIDDEN
            )

        # ===== Context in English =====
        context = {
            'analysis_id': analysis.id,
            'farm_name': farm.name,
            'province': farm.province,
            'analysis_date': analysis.created_at.strftime('%Y/%m/%d %H:%M'),
            'soil_health_index': analysis.soil_health_index or 0,
            'health_level': analysis.get_health_level_display(),
            'ph': sample.ph or 'N/A',
            'ec': sample.ec or 'N/A',
            'organic_matter': sample.organic_matter or 'N/A',
            'nitrogen': sample.nitrogen or 'N/A',
            'phosphorus': sample.phosphorus or 'N/A',
            'potassium': sample.potassium or 'N/A',
            'expected_yield': analysis.expected_yield or 0,
            'expected_profit': analysis.expected_profit or 0,
            'recommended_crops': analysis.recommended_crops[:3] if analysis.recommended_crops else [],
            'management_tips': analysis.management_tips or 'No specific recommendations',
        }

        # ===== Use English template =====
        template = get_template('soil/pdf_report_en.html')
        html = template.render(context)

        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), result)

        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="analysis_report_{analysis.id}.pdf"'
            response['Content-Length'] = result.getbuffer().nbytes
            return response

        return HttpResponse('PDF generation failed', status=500)

    # ===================== پنل LIMS =====================

    @action(detail=False, methods=['post'], url_path='lab-register')
    def lab_register_sample(self, request):
        logger.info(f"📥 داده دریافتی lab-register: {request.data}")

        serializer = LabSampleInputSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"❌ خطاهای Serializer: {serializer.errors}")
            return Response(
                {'error': 'داده‌های ورودی نامعتبر', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data

        try:
            farm = None
            if data.get('farm_id'):
                farm = get_object_or_404(Farm, id=data['farm_id'])
            elif data.get('farm_name') and data.get('farmer_phone'):
                farmer, _ = Farmer.objects.get_or_create(
                    phone=data['farmer_phone'],
                    defaults={
                        'user': User.objects.get_or_create(
                            username=f"farmer_{data['farmer_phone']}",
                            defaults={
                                'first_name': data.get('farmer_name', 'کاربر')[:50],
                                'last_name': 'آزمایشگاه'
                            }
                        )[0],
                        'national_id': f"F{data['farmer_phone'][:8]}",
                        'address': 'آدرس نامشخص',
                        'province': None,
                        'county': None,
                    }
                )

                farm = Farm.objects.create(
                    farmer=farmer,
                    name=data['farm_name'],
                    area=1.0,
                    geometry_coords=[],
                    address='آدرس نامشخص',
                    province=None,
                    county=None,
                )
            else:
                return Response(
                    {'error': 'لطفاً farm_id یا (farm_name + farmer_phone) را وارد کنید'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            soil_sample = SoilSample.objects.create(
                farm=farm,
                sample_code=data['sample_code'],
                sampling_date=data['sampling_date'],
                depth=data.get('depth', 30) or 30,
                ph=data['ph'],
                ec=data['ec'],
                organic_matter=data['organic_matter'],
                nitrogen=data.get('nitrogen'),
                phosphorus=data.get('phosphorus'),
                potassium=data.get('potassium'),
                texture=data['texture'],
                latitude=data.get('latitude', 35.0) or 35.0,
                longitude=data.get('longitude', 51.0) or 51.0,
                source='LAB',
                laboratory_name=data['laboratory_name'],
                is_verified=False,
                iron=data.get('iron'),
                zinc=data.get('zinc'),
                manganese=data.get('manganese'),
                copper=data.get('copper'),
            )

            serializer = SoilSampleSerializer(soil_sample)
            return Response({
                'success': True,
                'sample': serializer.data,
                'message': f'نمونه {data["sample_code"]} با موفقیت ثبت شد'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"❌ خطا در ثبت نمونه آزمایشگاهی: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='lab-samples')
    def lab_list_samples(self, request):
        samples = SoilSample.objects.filter(source='LAB').order_by('-sampling_date')
        serializer = SoilSampleSerializer(samples, many=True)
        return Response(serializer.data)

    # ===================== سیستم تأیید =====================

    @action(detail=False, methods=['get'], url_path='pending-verification')
    def pending_verification(self, request):
        samples = SoilSample.objects.filter(is_verified=False, rejection_reason='').order_by('-created_at')
        serializer = SoilSampleSerializer(samples, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='verification-stats')
    def verification_stats(self, request):
        total = SoilSample.objects.count()
        pending = SoilSample.objects.filter(is_verified=False, rejection_reason='').count()
        verified = SoilSample.objects.filter(is_verified=True).count()
        rejected = SoilSample.objects.filter(rejection_reason__isnull=False, rejection_reason__gt='').count()

        return Response({
            'total': total,
            'pending': pending,
            'verified': verified,
            'rejected': rejected,
        })

    @action(detail=True, methods=['get'], url_path='details')
    def sample_details(self, request, pk=None):
        sample = get_object_or_404(SoilSample, pk=pk)
        profile = getattr(request.user, 'profile', None)
        role = profile.role if profile else None
        if not (
            request.user.is_superuser
            or role in ['ADMIN', 'EXPERT']
            or sample.farm.farmer.user_id == request.user.id
            or (role == 'LAB' and profile.is_verified and sample.source == 'LAB')
        ):
            return Response(
                {'error': 'شما به این نمونه دسترسی ندارید'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = SoilSampleSerializer(sample)

        data = serializer.data
        try:
            analysis = SoilAnalysis.objects.get(soil_sample=sample)
            data['analysis'] = {
                'id': analysis.id,
                'soil_health_index': analysis.soil_health_index,
                'soil_health_level': analysis.soil_health_level,
                'expected_yield': analysis.expected_yield,
                'expected_profit': analysis.expected_profit,
                'recommended_crops': analysis.recommended_crops,
                'created_at': analysis.created_at,
            }
        except SoilAnalysis.DoesNotExist:
            data['analysis'] = None

        return Response(data)

    @action(detail=True, methods=['post'], url_path='verify')
    def verify_sample(self, request, pk=None):
        sample = get_object_or_404(SoilSample, pk=pk)

        if sample.is_verified:
            return Response(
                {'error': 'این نمونه قبلاً تأیید شده است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        sample.is_verified = True
        sample.verified_by = request.user if request.user.is_authenticated else None
        sample.verified_at = timezone.now()
        sample.rejection_reason = ''
        sample.save()

        return Response({
            'success': True,
            'message': f'نمونه {sample.sample_code} با موفقیت تأیید شد',
            'sample_id': sample.id,
            'verified_by': request.user.username if request.user.is_authenticated else 'سیستم',
            'verified_at': sample.verified_at,
        })

    @action(detail=True, methods=['post'], url_path='reject')
    def reject_sample(self, request, pk=None):
        sample = get_object_or_404(SoilSample, pk=pk)

        if sample.is_verified:
            return Response(
                {'error': 'این نمونه قبلاً تأیید شده است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'لطفاً دلیل رد را وارد کنید'},
                status=status.HTTP_400_BAD_REQUEST
            )

        sample.rejection_reason = reason
        sample.is_verified = False
        sample.verified_by = request.user if request.user.is_authenticated else None
        sample.verified_at = timezone.now()
        sample.save()

        return Response({
            'success': True,
            'message': f'نمونه {sample.sample_code} با موفقیت رد شد',
            'reason': reason,
            'rejected_by': request.user.username if request.user.is_authenticated else 'سیستم',
        })

    # ===================== آپلود انبوه Excel =====================

    @action(detail=False, methods=['post'], url_path='upload-bulk')
    def upload_bulk_samples(self, request):
        """آپلود انبوه نمونه‌های خاک از طریق فایل Excel"""
        import csv
        from openpyxl import load_workbook

        if 'file' not in request.FILES:
            return Response(
                {'error': 'هیچ فایلی ارسال نشده است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES['file']

        if not file.name.endswith(('.xlsx', '.xls', '.csv')):
            return Response(
                {'error': 'فرمت فایل پشتیبانی نمی‌شود. فقط Excel (xlsx, xls) و CSV مجاز است.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            rows = []

            if file.name.endswith('.csv'):
                text = file.read().decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(text))
                rows = list(csv_reader)
            else:
                workbook = load_workbook(file)
                sheet = workbook.active
                headers = [cell.value for cell in sheet[1]]
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    row_dict = {}
                    for i, header in enumerate(headers):
                        if i < len(row) and row[i] is not None:
                            row_dict[header] = row[i]
                    if row_dict:
                        rows.append(row_dict)

            if not rows:
                return Response(
                    {'error': 'فایل خالی است یا داده‌ای ندارد'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            required_columns = ['sample_code', 'ph', 'ec', 'organic_matter']
            missing_columns = [col for col in required_columns if col not in rows[0]]
            if missing_columns:
                return Response({
                    'error': f'ستون‌های زیر در فایل وجود ندارند: {", ".join(missing_columns)}',
                    'required_columns': required_columns
                }, status=status.HTTP_400_BAD_REQUEST)

            results = {
                'success_count': 0,
                'error_count': 0,
                'errors': [],
                'samples': []
            }

            default_user, _ = User.objects.get_or_create(
                username='farmer_default',
                defaults={
                    'first_name': 'کاربر',
                    'last_name': 'پیش‌فرض',
                    'email': 'farmer@abak.ir'
                }
            )

            for index, row in enumerate(rows):
                try:
                    errors = []

                    sample_code = str(row.get('sample_code', '')).strip()
                    if not sample_code:
                        errors.append('کد نمونه الزامی است')

                    try:
                        ph = float(row.get('ph', 0))
                        if not (0 <= ph <= 14):
                            errors.append(f'pH نامعتبر: {ph}')
                    except:
                        errors.append('pH نامعتبر')
                        ph = 7.0

                    try:
                        ec = float(row.get('ec', 0))
                        if ec < 0:
                            errors.append(f'EC نامعتبر: {ec}')
                    except:
                        errors.append('EC نامعتبر')
                        ec = 0.5

                    try:
                        organic_matter = float(row.get('organic_matter', 0))
                        if organic_matter < 0:
                            errors.append(f'ماده آلی نامعتبر: {organic_matter}')
                    except:
                        errors.append('ماده آلی نامعتبر')
                        organic_matter = 1.5

                    texture = str(row.get('texture', 'LOAM')).strip().upper()
                    valid_textures = ['SANDY', 'LOAMY_SAND', 'SANDY_LOAM', 'LOAM',
                                      'SILT_LOAM', 'SILT', 'CLAY_LOAM', 'SILTY_CLAY_LOAM', 'CLAY']
                    if texture not in valid_textures:
                        errors.append(f'بافت خاک نامعتبر: {texture}')
                        texture = 'LOAM'

                    latitude = 35.0
                    longitude = 51.0
                    try:
                        if 'latitude' in row and row['latitude']:
                            latitude = float(row['latitude'])
                        if 'longitude' in row and row['longitude']:
                            longitude = float(row['longitude'])
                    except:
                        pass

                    depth = 30
                    try:
                        if 'depth' in row and row['depth']:
                            depth = float(row['depth'])
                    except:
                        pass

                    sampling_date = '2024-01-01'
                    try:
                        if 'sampling_date' in row and row['sampling_date']:
                            sampling_date = str(row['sampling_date'])[:10]
                    except:
                        errors.append('تاریخ نمونه‌برداری نامعتبر')

                    if errors:
                        results['error_count'] += 1
                        results['errors'].append({
                            'row': index + 2,
                            'sample_code': sample_code or f'ROW-{index+2}',
                            'errors': errors
                        })
                        continue

                    farmer, _ = Farmer.objects.get_or_create(
                        user=default_user,
                        defaults={
                            'national_id': f'F{index+1:05d}',
                            'phone': '0912' + f'{index+1:07d}',
                            'address': 'آدرس نامشخص',
                            'province': None,
                            'county': None,
                        }
                    )

                    farm_name = row.get('farm_name', f'مزرعه {index+1}')
                    farm, _ = Farm.objects.get_or_create(
                        name=farm_name,
                        farmer=farmer,
                        defaults={
                            'area': 1.0,
                            'geometry_coords': [],
                            'address': row.get('address', 'آدرس نامشخص'),
                            'province': None,
                            'county': None,
                        }
                    )

                    soil_sample = SoilSample.objects.create(
                        farm=farm,
                        sample_code=sample_code,
                        sampling_date=sampling_date,
                        depth=depth,
                        ph=ph,
                        ec=ec,
                        organic_matter=organic_matter,
                        nitrogen=float(row.get('nitrogen', 0)) if row.get('nitrogen') else None,
                        phosphorus=float(row.get('phosphorus', 0)) if row.get('phosphorus') else None,
                        potassium=float(row.get('potassium', 0)) if row.get('potassium') else None,
                        texture=texture,
                        latitude=latitude,
                        longitude=longitude,
                        source='LAB',
                        laboratory_name=request.data.get('laboratory_name', 'آزمایشگاه'),
                        is_verified=False,
                        iron=float(row.get('iron', 0)) if row.get('iron') else None,
                        zinc=float(row.get('zinc', 0)) if row.get('zinc') else None,
                        manganese=float(row.get('manganese', 0)) if row.get('manganese') else None,
                        copper=float(row.get('copper', 0)) if row.get('copper') else None,
                    )

                    results['success_count'] += 1
                    results['samples'].append({
                        'sample_code': sample_code,
                        'farm_name': farm_name,
                        'ph': ph,
                        'ec': ec,
                        'organic_matter': organic_matter,
                    })

                except Exception as e:
                    results['error_count'] += 1
                    results['errors'].append({
                        'row': index + 2,
                        'sample_code': row.get('sample_code', f'ROW-{index+2}'),
                        'errors': [str(e)]
                    })

            return Response({
                'success': True,
                'message': f'{results["success_count"]} نمونه با موفقیت ثبت شد',
                'results': results
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'خطا در پردازش فایل: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ===================== درخواست‌های کارشناس (CRM) =====================

    @action(detail=False, methods=['post'], url_path='expert-request')
    def create_expert_request(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'لطفاً وارد شوید'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            farmer = request.user.farmer_profile
        except (AttributeError, Farmer.DoesNotExist):
            return Response({'error': 'پروفایل کشاورز یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ExpertRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        request_obj = ExpertRequest.objects.create(
            farmer=farmer,
            **serializer.validated_data
        )

        result = ExpertRequestSerializer(request_obj).data
        return Response({
            'success': True,
            'message': 'درخواست شما با موفقیت ثبت شد',
            'request': result
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='my-requests')
    def my_expert_requests(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'لطفاً وارد شوید'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            farmer = request.user.farmer_profile
            requests = ExpertRequest.objects.filter(farmer=farmer).order_by('-created_at')
            serializer = ExpertRequestSerializer(requests, many=True)
            return Response(serializer.data)
        except (AttributeError, Farmer.DoesNotExist):
            return Response({'error': 'پروفایل کشاورز یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='expert-requests')
    def expert_requests_list(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)

        try:
            user_profile = request.user.profile
        except AttributeError:
            return Response({'error': 'پروفایل کاربر یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

        if user_profile.role not in ['ADMIN', 'EXPERT']:
            return Response({'error': 'فقط کارشناسان و مدیران دسترسی دارند'}, status=status.HTTP_403_FORBIDDEN)

        status_filter = request.query_params.get('status', 'PENDING')
        if status_filter:
            requests = ExpertRequest.objects.filter(status=status_filter).order_by('-created_at')
        else:
            requests = ExpertRequest.objects.all().order_by('-created_at')

        serializer = ExpertRequestSerializer(requests, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='accept-request')
    def accept_expert_request(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)

        try:
            user_profile = request.user.profile
        except AttributeError:
            return Response({'error': 'پروفایل کاربر یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

        if user_profile.role not in ['ADMIN', 'EXPERT']:
            return Response({'error': 'فقط کارشناسان و مدیران دسترسی دارند'}, status=status.HTTP_403_FORBIDDEN)

        request_obj = get_object_or_404(ExpertRequest, pk=pk)

        if request_obj.status != 'PENDING':
            return Response({'error': 'این درخواست قبلاً بررسی شده است'}, status=status.HTTP_400_BAD_REQUEST)

        request_obj.expert = user_profile
        request_obj.status = 'ACCEPTED'
        request_obj.expert_response = request.data.get('response', '')
        request_obj.save()

        return Response({
            'success': True,
            'message': 'درخواست با موفقیت پذیرفته شد',
            'request': ExpertRequestSerializer(request_obj).data
        })

    @action(detail=True, methods=['post'], url_path='reject-request')
    def reject_expert_request(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)

        try:
            user_profile = request.user.profile
        except AttributeError:
            return Response({'error': 'پروفایل کاربر یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

        if user_profile.role not in ['ADMIN', 'EXPERT']:
            return Response({'error': 'فقط کارشناسان و مدیران دسترسی دارند'}, status=status.HTTP_403_FORBIDDEN)

        request_obj = get_object_or_404(ExpertRequest, pk=pk)

        if request_obj.status != 'PENDING':
            return Response({'error': 'این درخواست قبلاً بررسی شده است'}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': 'لطفاً دلیل رد را وارد کنید'}, status=status.HTTP_400_BAD_REQUEST)

        request_obj.expert = user_profile
        request_obj.status = 'REJECTED'
        request_obj.expert_response = reason
        request_obj.save()

        return Response({
            'success': True,
            'message': 'درخواست با موفقیت رد شد',
            'request': ExpertRequestSerializer(request_obj).data
        })

    @action(detail=True, methods=['post'], url_path='complete-request')
    def complete_expert_request(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)

        try:
            user_profile = request.user.profile
        except AttributeError:
            return Response({'error': 'پروفایل کاربر یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

        if user_profile.role not in ['ADMIN', 'EXPERT']:
            return Response({'error': 'فقط کارشناسان و مدیران دسترسی دارند'}, status=status.HTTP_403_FORBIDDEN)

        request_obj = get_object_or_404(ExpertRequest, pk=pk)

        if request_obj.status != 'ACCEPTED':
            return Response({'error': 'این درخواست در وضعیت قابل تکمیل نیست'}, status=status.HTTP_400_BAD_REQUEST)

        request_obj.status = 'COMPLETED'
        request_obj.completion_note = request.data.get('note', '')
        request_obj.save()

        return Response({
            'success': True,
            'message': 'درخواست با موفقیت تکمیل شد',
            'request': ExpertRequestSerializer(request_obj).data
        })

    # ===================== لایه‌های خاک =====================

    @action(detail=False, methods=['get'], url_path='soil-layers')
    def soil_layers(self, request):
        layer_type = request.query_params.get('layer', 'ph')
        samples = SoilSample.objects.filter(is_verified=True).select_related('farm')

        features = []
        for sample in samples:
            color = '#808080'
            value = 0

            if layer_type == 'ph':
                value = sample.ph
                if value < 6.5:
                    color = '#ff4444'
                elif value < 7.5:
                    color = '#44bb44'
                else:
                    color = '#4444ff'
            elif layer_type == 'organic_matter':
                value = sample.organic_matter
                if value < 1.0:
                    color = '#ffaa00'
                elif value < 2.0:
                    color = '#44bb44'
                else:
                    color = '#006600'
            elif layer_type == 'texture':
                texture_colors = {
                    'SANDY': '#ffdd99',
                    'LOAMY_SAND': '#eebb77',
                    'SANDY_LOAM': '#dd9955',
                    'LOAM': '#88aa55',
                    'SILT_LOAM': '#7799aa',
                    'SILT': '#6688aa',
                    'CLAY_LOAM': '#aa7755',
                    'SILTY_CLAY_LOAM': '#996655',
                    'CLAY': '#885544',
                }
                color = texture_colors.get(sample.texture, '#808080')
                value = sample.texture

            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [sample.longitude, sample.latitude]
                },
                'properties': {
                    'sample_code': sample.sample_code,
                    'farm_name': sample.farm.name if sample.farm else 'نامشخص',
                    'value': value,
                    'color': color,
                    'ph': sample.ph,
                    'ec': sample.ec,
                    'organic_matter': sample.organic_matter,
                    'texture': sample.texture,
                    'texture_display': sample.get_texture_display(),
                    'nitrogen': sample.nitrogen,
                    'phosphorus': sample.phosphorus,
                    'potassium': sample.potassium,
                    'iron': sample.iron,
                    'zinc': sample.zinc,
                    'manganese': sample.manganese,
                    'copper': sample.copper,
                }
            })

        return Response({
            'type': 'FeatureCollection',
            'features': features,
            'layer_type': layer_type,
            'count': len(features)
        })

    # ===================== درون‌یابی (API جدید) =====================

    @action(detail=False, methods=['post'], url_path='interpolate')
    def interpolate_soil(self, request):
        """
        درون‌یابی داده‌های خاک برای یک نقطه مشخص
        """
        try:
            lat = request.data.get('latitude')
            lng = request.data.get('longitude')
            radius = request.data.get('radius', 100)

            if not lat or not lng:
                return Response(
                    {'error': 'مختصات جغرافیایی الزامی است'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # دریافت نمونه‌های تأیید شده
            samples = SoilSample.objects.filter(is_verified=True)
            sample_list = []

            for sample in samples:
                sample_list.append({
                    'latitude': sample.latitude,
                    'longitude': sample.longitude,
                    'ph': sample.ph,
                    'ec': sample.ec,
                    'organic_matter': sample.organic_matter,
                    'nitrogen': sample.nitrogen,
                    'phosphorus': sample.phosphorus,
                    'potassium': sample.potassium,
                })

            # اجرای درون‌یابی
            result = SoilAnalysisEngine.interpolate_values(sample_list, lat, lng, radius)

            if not result:
                return Response(
                    {'error': 'هیچ نمونه‌ای در محدوده مشخص شده یافت نشد'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # محاسبه تعداد نمونه‌های استفاده شده
            samples_used = len([s for s in sample_list if
                               math.sqrt((s['latitude'] - lat)**2 + (s['longitude'] - lng)**2) * 111 <= radius])

            return Response({
                'success': True,
                'data': result,
                'latitude': lat,
                'longitude': lng,
                'radius': radius,
                'samples_used': samples_used
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )