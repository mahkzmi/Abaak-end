from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import pandas as pd
import io
import re

from xhtml2pdf import pisa

from accounts.permissions import (
    IsAdmin, IsExpert, IsLab, IsFarmer, 
    IsAdminOrExpert, IsLabOrExpert, IsVerifiedLabSample
)

from .models import Province, County, Farm, SoilSample, SoilAnalysis, CropRecommendation, ExpertRequest, SoilHealthHistory
from .serializers import (
    ProvinceSerializer, CountySerializer, FarmSerializer,
    SoilSampleSerializer, SoilAnalysisSerializer, SoilAnalysisInputSerializer,
    LabSampleInputSerializer, ExpertRequestSerializer, ExpertRequestCreateSerializer
)
from .analysis_engine import SoilAnalysisEngine


# ============ توابع اعتبارسنجی ============

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
        except:
            errors.append("pH نامعتبر است")
    
    if 'ec' in data and data['ec'] is not None:
        try:
            ec = float(data['ec'])
            if ec < 0:
                errors.append("EC باید مثبت باشد")
        except:
            errors.append("EC نامعتبر است")
    
    if 'organic_matter' in data and data['organic_matter'] is not None:
        try:
            om = float(data['organic_matter'])
            if om < 0:
                errors.append("ماده آلی باید مثبت باشد")
        except:
            errors.append("ماده آلی نامعتبر است")
    
    if errors:
        raise ValidationError(errors)
    
    return data


# ============ کلاس‌های ViewSet ============

class ProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    """API برای دریافت استان‌ها"""
    queryset = Province.objects.all().order_by('name')
    serializer_class = ProvinceSerializer
    permission_classes = [AllowAny]


class CountyViewSet(viewsets.ReadOnlyModelViewSet):
    """API برای دریافت شهرستان‌های یک استان"""
    serializer_class = CountySerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        province_id = self.request.query_params.get('province_id')
        if province_id:
            return County.objects.filter(province_id=province_id).order_by('name')
        return County.objects.all().order_by('name')


class SoilSampleViewSet(viewsets.ModelViewSet):
    """API برای مدیریت نمونه‌های خاک"""
    queryset = SoilSample.objects.all().order_by('-sampling_date')
    serializer_class = SoilSampleSerializer
    permission_classes = [AllowAny]


class FarmViewSet(viewsets.ModelViewSet):
    """API برای مدیریت مزارع"""
    queryset = Farm.objects.all().order_by('-created_at')
    serializer_class = FarmSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """فقط مزارع کاربر فعلی را برگردان"""
        user = self.request.user
        try:
            farmer = user.farmer_profile
            return Farm.objects.filter(farmer=farmer).order_by('-created_at')
        except:
            return Farm.objects.none()
    
    @action(detail=True, methods=['put'], url_path='update')
    def update_farm(self, request, pk=None):
        """به‌روزرسانی اطلاعات مزرعه"""
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
        """حذف مزرعه"""
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


@method_decorator(csrf_exempt, name='dispatch')
class SoilAnalysisViewSet(viewsets.ModelViewSet):
    """API برای مدیریت تحلیل‌های خاک"""
    queryset = SoilAnalysis.objects.all().order_by('-created_at')
    serializer_class = SoilAnalysisSerializer
    
    def get_permissions(self):
        if self.action in ['lab_register_sample', 'upload_bulk_samples']:
            permission_classes = [IsVerifiedLabSample]
        elif self.action in ['verify_sample', 'reject_sample', 'pending_verification', 'verification_stats']:
            permission_classes = [IsAdminOrExpert]
        elif self.action in ['create_farm']:
            permission_classes = [AllowAny]
        elif self.action in ['lab_list_samples']:
            permission_classes = [IsLabOrExpert]
        elif self.action in ['generate_pdf']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # ==================== سلامت خاک ====================
    
    @action(detail=False, methods=['get'], url_path='health-history')
    def health_history(self, request):
        """دریافت تاریخچه DSHI برای مزرعه مشخص"""
        farm_id = request.query_params.get('farm_id')
        if not farm_id:
            return Response(
                {'error': 'شناسه مزرعه الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            farm = get_object_or_404(Farm, id=farm_id)
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
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ==================== تسک ۱: ثبت مزرعه ====================
    
    @action(detail=False, methods=['post'], url_path='create-farm')
    def create_farm(self, request):
        """ثبت مزرعه جدید بر اساس پلی‌گون رسم‌شده روی نقشه"""
        from django.contrib.auth.models import User
        from accounts.models import Farmer
        
        print("📥 داده دریافتی:", request.data)
        
        # ============ دریافت کاربر واقعی ============
        user = request.user
        if not user.is_authenticated:
            # اگر کاربر لاگین نکرده، از کاربر پیش‌فرض استفاده کن
            default_user, _ = User.objects.get_or_create(
                username='farmer_default',
                defaults={
                    'first_name': 'کاربر',
                    'last_name': 'پیش‌فرض',
                    'email': 'farmer@abak.ir'
                }
            )
            user = default_user
            print("⚠️ کاربر لاگین نکرده، از کاربر پیش‌فرض استفاده شد")
        else:
            print(f"✅ کاربر لاگین شده: {user.username}")
        
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
            
            print(f"📐 مساحت محاسبه‌شده: {area_ha:.2f} هکتار")
            
            # ============ پیدا کردن یا ساختن کشاورز برای کاربر واقعی ============
            farmer, _ = Farmer.objects.get_or_create(
                user=user,
                defaults={
                    'national_id': f'F{user.id:05d}',
                    'phone': '0912' + f'{user.id:07d}',
                    'address': 'آدرس نامشخص',
                    'province': None,
                    'county': None,
                }
            )
            
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
            
            print(f"✅ مزرعه با ID {farm.id} برای کاربر {user.username} ثبت شد")
            
            serializer = FarmSerializer(farm)
            return Response({
                'success': True,
                'farm': serializer.data,
                'message': f'مزرعه {farm_name} با مساحت {area_ha:.2f} هکتار ثبت شد'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            print("❌ خطا:", str(e))
            traceback.print_exc()
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    # ==================== تسک ۲: تحلیل خاک ====================
    
    @swagger_auto_schema(
        operation_description="تحلیل خاک بر اساس داده‌های ورودی",
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
                    enum=['SANDY', 'LOAMY_SAND', 'SANDY_LOAM', 'LOAM', 'SILT_LOAM', 'SILT', 'CLAY_LOAM', 'SILTY_CLAY_LOAM', 'CLAY'],
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
        """تحلیل خاک بر اساس داده‌های ورودی"""
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
        
        try:
            if farm_id:
                farm = get_object_or_404(Farm, id=farm_id)
                if farm.province:
                    province_name = farm.province.name
                else:
                    province_name = 'تهران'
                    print("⚠️ استان مشخص نشد، از تهران به عنوان پیش‌فرض استفاده شد")
            
            result = SoilAnalysisEngine.analyze_soil(data, province_name)
            
            if farm_id and farm:
                soil_sample, created = SoilSample.objects.get_or_create(
                    farm=farm,
                    sample_code=f"ANALYSIS-{farm_id}-{data['ph']}-{data.get('texture', 'LOAM')}",
                    defaults={
                        'sampling_date': timezone.now().date(),
                        'depth': 30,
                        'ph': data['ph'],
                        'ec': data['ec'],
                        'organic_matter': data['organic_matter'],
                        'nitrogen': data.get('nitrogen'),
                        'phosphorus': data.get('phosphorus'),
                        'potassium': data.get('potassium'),
                        'texture': data['texture'],
                        'latitude': data.get('latitude', 35.0),
                        'longitude': data.get('longitude', 51.0),
                        'source': 'ESTIMATED',
                        'iron': data.get('iron'),
                        'zinc': data.get('zinc'),
                        'manganese': data.get('manganese'),
                        'copper': data.get('copper'),
                    }
                )
                
                analysis, created = SoilAnalysis.objects.get_or_create(
                    soil_sample=soil_sample,
                    defaults={
                        'soil_health_index': result['soil_health_index'],
                        'soil_health_level': result['soil_health_level'],
                        'recommended_crops': [{
                            'name': rec['crop_name'],
                            'score': rec['suitability_score']
                        } for rec in result['recommended_crops'][:5]],
                        'fertilizer_recommendations': {
                            'main': result['recommended_crops'][0]['fertilizer_advice'] if result['recommended_crops'] else '',
                        },
                        'irrigation_recommendations': result['recommended_crops'][0]['irrigation_advice'] if result['recommended_crops'] else '',
                        'management_tips': result['summary'],
                        'expected_yield': result['best_crop']['predicted_yield'] if result['best_crop'] else 0,
                        'expected_profit': result['best_crop']['predicted_profit'] if result['best_crop'] else 0,
                    }
                )
                
                if not created:
                    analysis.soil_health_index = result['soil_health_index']
                    analysis.soil_health_level = result['soil_health_level']
                    analysis.recommended_crops = [{
                        'name': rec['crop_name'],
                        'score': rec['suitability_score']
                    } for rec in result['recommended_crops'][:5]]
                    analysis.fertilizer_recommendations = {
                        'main': result['recommended_crops'][0]['fertilizer_advice'] if result['recommended_crops'] else '',
                    }
                    analysis.irrigation_recommendations = result['recommended_crops'][0]['irrigation_advice'] if result['recommended_crops'] else ''
                    analysis.management_tips = result['summary']
                    analysis.expected_yield = result['best_crop']['predicted_yield'] if result['best_crop'] else 0
                    analysis.expected_profit = result['best_crop']['predicted_profit'] if result['best_crop'] else 0
                    analysis.save()
                
                result['analysis_id'] = analysis.id
                result['sample_code'] = soil_sample.sample_code
                
                SoilHealthHistory.objects.create(
                    farm=farm,
                    analysis=analysis,
                    health_index=result['soil_health_index'],
                    health_level=result['soil_health_level'],
                    ph=data['ph'],
                    ec=data['ec'],
                    organic_matter=data['organic_matter'],
                )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            print("❌ خطا:", str(e))
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # ==================== PDF ====================
    
    @action(detail=True, methods=['get'], url_path='pdf')
    def generate_pdf(self, request, pk=None):
        """تولید PDF از تحلیل خاک"""
        analysis = get_object_or_404(SoilAnalysis, pk=pk)
        sample = analysis.soil_sample
        farm = sample.farm
        
        context = {
            'analysis': analysis,
            'sample': sample,
            'farm': farm,
            'farmer': farm.farmer,
            'analysis_date': analysis.created_at.strftime('%Y/%m/%d'),
            'health_level_display': analysis.get_health_level_display(),
            'recommended_crops': analysis.recommended_crops[:3] if analysis.recommended_crops else [],
            'fertilizer_recommendations': analysis.fertilizer_recommendations or {},
            'soil_health_index': analysis.soil_health_index,
            'expected_yield': analysis.expected_yield,
            'expected_profit': analysis.expected_profit,
            'management_tips': analysis.management_tips or '',
        }
        
        template = get_template('soil/pdf_report.html')
        html = template.render(context)
        
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="analysis_{analysis.id}.pdf"'
            return response
        
        return HttpResponse('خطا در تولید PDF', status=500)

    # ==================== تسک ۳: پنل LIMS ====================
    
    @action(detail=False, methods=['post'], url_path='lab-register')
    def lab_register_sample(self, request):
        """ثبت نمونه خاک از طریق آزمایشگاه (LIMS)"""
        from django.contrib.auth.models import User
        from accounts.models import Farmer
        
        print("📥 داده دریافتی lab-register:", request.data)
        
        serializer = LabSampleInputSerializer(data=request.data)
        if not serializer.is_valid():
            print("❌ خطاهای Serializer:", serializer.errors)
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
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='lab-samples')
    def lab_list_samples(self, request):
        """لیست نمونه‌های ثبت‌شده توسط آزمایشگاه"""
        samples = SoilSample.objects.filter(source='LAB').order_by('-sampling_date')
        serializer = SoilSampleSerializer(samples, many=True)
        return Response(serializer.data)

    # ==================== تسک ۴: سیستم تأیید ====================
    
    @action(detail=False, methods=['get'], url_path='pending-verification')
    def pending_verification(self, request):
        """لیست نمونه‌های در انتظار تأیید"""
        samples = SoilSample.objects.filter(is_verified=False, rejection_reason='').order_by('-created_at')
        serializer = SoilSampleSerializer(samples, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='verification-stats')
    def verification_stats(self, request):
        """دریافت آمار تأیید نمونه‌ها"""
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
        """دریافت جزئیات کامل یک نمونه"""
        sample = get_object_or_404(SoilSample, pk=pk)
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
        """تأیید یک نمونه توسط کارشناس"""
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
        """رد یک نمونه توسط کارشناس با ذکر دلیل"""
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

    # ==================== تسک ۵: آپلود انبوه Excel ====================
    
    @action(detail=False, methods=['post'], url_path='upload-bulk')
    def upload_bulk_samples(self, request):
        """آپلود انبوه نمونه‌های خاک از طریق فایل Excel"""
        from django.contrib.auth.models import User
        from accounts.models import Farmer
        
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
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            required_columns = ['sample_code', 'sampling_date', 'ph', 'ec', 'organic_matter', 'texture']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
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
            
            for index, row in df.iterrows():
                try:
                    errors = []
                    
                    sample_code = str(row.get('sample_code', '')).strip()
                    if not sample_code:
                        errors.append('کد نمونه الزامی است')
                    
                    try:
                        ph = float(row.get('ph', 0))
                        if not (0 <= ph <= 14):
                            errors.append(f'pH نامعتبر: {ph} (باید بین ۰ تا ۱۴ باشد)')
                    except:
                        errors.append('pH نامعتبر')
                        ph = 7.0
                    
                    try:
                        ec = float(row.get('ec', 0))
                        if ec < 0:
                            errors.append(f'EC نامعتبر: {ec} (باید مثبت باشد)')
                    except:
                        errors.append('EC نامعتبر')
                        ec = 0.5
                    
                    try:
                        organic_matter = float(row.get('organic_matter', 0))
                        if organic_matter < 0:
                            errors.append(f'ماده آلی نامعتبر: {organic_matter} (باید مثبت باشد)')
                    except:
                        errors.append('ماده آلی نامعتبر')
                        organic_matter = 1.5
                    
                    texture = str(row.get('texture', '')).strip().upper()
                    valid_textures = ['SANDY', 'LOAMY_SAND', 'SANDY_LOAM', 'LOAM', 
                                      'SILT_LOAM', 'SILT', 'CLAY_LOAM', 'SILTY_CLAY_LOAM', 'CLAY']
                    if texture not in valid_textures:
                        errors.append(f'بافت خاک نامعتبر: {texture}')
                        texture = 'LOAM'
                    
                    latitude = 35.0
                    longitude = 51.0
                    try:
                        if 'latitude' in row and pd.notna(row['latitude']):
                            latitude = float(row['latitude'])
                        if 'longitude' in row and pd.notna(row['longitude']):
                            longitude = float(row['longitude'])
                    except:
                        pass
                    
                    depth = 30
                    try:
                        if 'depth' in row and pd.notna(row['depth']):
                            depth = float(row['depth'])
                    except:
                        pass
                    
                    sampling_date = '2024-01-01'
                    try:
                        if 'sampling_date' in row and pd.notna(row['sampling_date']):
                            sampling_date = pd.to_datetime(row['sampling_date']).strftime('%Y-%m-%d')
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
                        nitrogen=float(row.get('nitrogen', 0)) if pd.notna(row.get('nitrogen')) else None,
                        phosphorus=float(row.get('phosphorus', 0)) if pd.notna(row.get('phosphorus')) else None,
                        potassium=float(row.get('potassium', 0)) if pd.notna(row.get('potassium')) else None,
                        texture=texture,
                        latitude=latitude,
                        longitude=longitude,
                        source='LAB',
                        laboratory_name=request.data.get('laboratory_name', 'آزمایشگاه'),
                        is_verified=False,
                        iron=float(row.get('iron', 0)) if pd.notna(row.get('iron')) else None,
                        zinc=float(row.get('zinc', 0)) if pd.notna(row.get('zinc')) else None,
                        manganese=float(row.get('manganese', 0)) if pd.notna(row.get('manganese')) else None,
                        copper=float(row.get('copper', 0)) if pd.notna(row.get('copper')) else None,
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

    # ==================== تسک ۹: CRM ====================
    
    @action(detail=False, methods=['post'], url_path='expert-request')
    def create_expert_request(self, request):
        """ایجاد درخواست جدید برای کارشناس (فقط کشاورز)"""
        from accounts.models import Farmer
        
        if not request.user.is_authenticated:
            return Response({'error': 'لطفاً وارد شوید'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            farmer = request.user.farmer_profile
        except:
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
        """دریافت لیست درخواست‌های کاربر (کشاورز)"""
        if not request.user.is_authenticated:
            return Response({'error': 'لطفاً وارد شوید'}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            farmer = request.user.farmer_profile
            requests = ExpertRequest.objects.filter(farmer=farmer).order_by('-created_at')
            serializer = ExpertRequestSerializer(requests, many=True)
            return Response(serializer.data)
        except:
            return Response({'error': 'پروفایل کشاورز یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'], url_path='expert-requests')
    def expert_requests_list(self, request):
        """لیست تمام درخواست‌ها برای کارشناسان (فقط Admin و Expert)"""
        if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
            return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user.profile.role not in ['ADMIN', 'EXPERT']:
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
        """پذیرش درخواست توسط کارشناس"""
        if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
            return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user.profile.role not in ['ADMIN', 'EXPERT']:
            return Response({'error': 'فقط کارشناسان و مدیران دسترسی دارند'}, status=status.HTTP_403_FORBIDDEN)
        
        request_obj = get_object_or_404(ExpertRequest, pk=pk)
        
        if request_obj.status != 'PENDING':
            return Response({'error': 'این درخواست قبلاً بررسی شده است'}, status=status.HTTP_400_BAD_REQUEST)
        
        request_obj.expert = request.user.profile
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
        """رد درخواست توسط کارشناس"""
        if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
            return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user.profile.role not in ['ADMIN', 'EXPERT']:
            return Response({'error': 'فقط کارشناسان و مدیران دسترسی دارند'}, status=status.HTTP_403_FORBIDDEN)
        
        request_obj = get_object_or_404(ExpertRequest, pk=pk)
        
        if request_obj.status != 'PENDING':
            return Response({'error': 'این درخواست قبلاً بررسی شده است'}, status=status.HTTP_400_BAD_REQUEST)
        
        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': 'لطفاً دلیل رد را وارد کنید'}, status=status.HTTP_400_BAD_REQUEST)
        
        request_obj.expert = request.user.profile
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
        """تکمیل درخواست توسط کارشناس"""
        if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
            return Response({'error': 'دسترسی غیرمجاز'}, status=status.HTTP_403_FORBIDDEN)
        
        if request.user.profile.role not in ['ADMIN', 'EXPERT']:
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

    # ==================== تسک ۱۷: لایه‌های خاک ====================
    
    @action(detail=False, methods=['get'], url_path='soil-layers')
    def soil_layers(self, request):
        """دریافت داده‌های خاک برای نمایش روی نقشه (GeoJSON)"""
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