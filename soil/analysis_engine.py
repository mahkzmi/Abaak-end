"""
موتور تحلیل هوشمند خاک آباک
بر اساس داده‌های واقعی و الگوریتم‌های هوش مصنوعی
"""

from django.utils import timezone


class SoilAnalysisEngine:
    """کلاس اصلی تحلیل خاک"""
    
    # محدوده‌های بهینه برای هر پارامتر
    OPTIMAL_RANGES = {
        'ph': {'min': 6.0, 'max': 7.5, 'optimal': 6.8},
        'ec': {'min': 0.0, 'max': 2.0, 'optimal': 0.5},
        'organic_matter': {'min': 2.0, 'max': 5.0, 'optimal': 3.0},
        'nitrogen': {'min': 40, 'max': 80, 'optimal': 60},
        'phosphorus': {'min': 15, 'max': 30, 'optimal': 22},
        'potassium': {'min': 150, 'max': 300, 'optimal': 220},
        'iron': {'min': 4.5, 'max': 10.0, 'optimal': 7.0, 'unit': 'ppm'},
        'zinc': {'min': 0.8, 'max': 2.0, 'optimal': 1.5, 'unit': 'ppm'},
        'manganese': {'min': 2.0, 'max': 5.0, 'optimal': 3.5, 'unit': 'ppm'},
        'copper': {'min': 0.2, 'max': 0.8, 'optimal': 0.5, 'unit': 'ppm'},
    }

    # ============ وزن‌های اختصاصی برای هر محصول ============
    CROP_WEIGHTS = {
        'گندم': {
            'ph': 0.25,
            'ec': 0.15,
            'organic_matter': 0.25,
            'texture': 0.20,
            'nitrogen': 0.10,
            'phosphorus': 0.03,
            'potassium': 0.02,
        },
        'پسته': {
            'ph': 0.30,
            'ec': 0.25,
            'organic_matter': 0.10,
            'texture': 0.20,
            'nitrogen': 0.05,
            'phosphorus': 0.05,
            'potassium': 0.05,
        },
        'برنج': {
            'ph': 0.20,
            'ec': 0.15,
            'organic_matter': 0.30,
            'texture': 0.25,
            'nitrogen': 0.05,
            'phosphorus': 0.03,
            'potassium': 0.02,
        },
        'ذرت': {
            'ph': 0.20,
            'ec': 0.15,
            'organic_matter': 0.20,
            'texture': 0.20,
            'nitrogen': 0.15,
            'phosphorus': 0.05,
            'potassium': 0.05,
        },
        'چغندر قند': {
            'ph': 0.25,
            'ec': 0.20,
            'organic_matter': 0.20,
            'texture': 0.20,
            'nitrogen': 0.10,
            'phosphorus': 0.03,
            'potassium': 0.02,
        },
        'پنبه': {
            'ph': 0.20,
            'ec': 0.20,
            'organic_matter': 0.15,
            'texture': 0.20,
            'nitrogen': 0.10,
            'phosphorus': 0.08,
            'potassium': 0.07,
        },
        'زعفران': {
            'ph': 0.30,
            'ec': 0.20,
            'organic_matter': 0.20,
            'texture': 0.15,
            'nitrogen': 0.05,
            'phosphorus': 0.05,
            'potassium': 0.05,
        },
    }
    
    # تطابق محصول با شرایط خاک
    CROP_MATCHING = {
        'گندم': {
            'ph': {'min': 6.0, 'max': 8.0},
            'ec': {'max': 4.0},
            'texture': ['LOAM', 'SILT_LOAM', 'CLAY_LOAM'],
            'organic_matter': {'min': 1.5},
            'min_profit': 15000000,  # تومان در هکتار
            'avg_yield': 4.5,  # تن در هکتار
            'micronutrients': {'iron': 4.5, 'zinc': 1.0, 'manganese': 2.5, 'copper': 0.3}
        },
        'پسته': {
            'ph': {'min': 7.0, 'max': 8.5},
            'ec': {'max': 3.0},
            'texture': ['SANDY_LOAM', 'LOAM', 'SANDY'],
            'organic_matter': {'min': 1.0},
            'min_profit': 45000000,
            'avg_yield': 2.5,
            'micronutrients': {'iron': 5.0, 'zinc': 1.5, 'manganese': 3.0, 'copper': 0.4}
        },
        'برنج': {
            'ph': {'min': 5.5, 'max': 6.5},
            'ec': {'max': 1.5},
            'texture': ['CLAY', 'SILT_LOAM', 'CLAY_LOAM'],
            'organic_matter': {'min': 2.0},
            'min_profit': 20000000,
            'avg_yield': 5.0,
            'micronutrients': {'iron': 5.0, 'zinc': 0.8, 'manganese': 2.0, 'copper': 0.3}
        },
        'ذرت': {
            'ph': {'min': 6.0, 'max': 7.5},
            'ec': {'max': 2.5},
            'texture': ['LOAM', 'SANDY_LOAM', 'SILT_LOAM'],
            'organic_matter': {'min': 1.5},
            'min_profit': 18000000,
            'avg_yield': 8.0,
            'micronutrients': {'iron': 4.5, 'zinc': 1.0, 'manganese': 2.5, 'copper': 0.3}
        },
        'چغندر قند': {
            'ph': {'min': 6.5, 'max': 7.5},
            'ec': {'max': 2.0},
            'texture': ['LOAM', 'SANDY_LOAM', 'SILT_LOAM'],
            'organic_matter': {'min': 1.5},
            'min_profit': 25000000,
            'avg_yield': 40.0,
            'micronutrients': {'iron': 5.0, 'zinc': 1.0, 'manganese': 2.0, 'copper': 0.3}
        },
        'پنبه': {
            'ph': {'min': 6.0, 'max': 8.0},
            'ec': {'max': 3.5},
            'texture': ['LOAM', 'SANDY_LOAM', 'CLAY_LOAM'],
            'organic_matter': {'min': 1.0},
            'min_profit': 22000000,
            'avg_yield': 3.5,
            'micronutrients': {'iron': 5.0, 'zinc': 1.5, 'manganese': 3.0, 'copper': 0.4}
        },
        'زعفران': {
            'ph': {'min': 7.0, 'max': 8.0},
            'ec': {'max': 2.0},
            'texture': ['LOAM', 'SANDY_LOAM'],
            'organic_matter': {'min': 1.5},
            'min_profit': 80000000,
            'avg_yield': 0.5,
            'micronutrients': {'iron': 5.0, 'zinc': 1.0, 'manganese': 2.5, 'copper': 0.3}
        },
    }

    # ============ کودهای موجود و مشخصات آنها ============
    FERTILIZERS = {
        'UREA': {
            'name': 'اوره',
            'n_percent': 46,
            'p_percent': 0,
            'k_percent': 0,
            'price_per_kg': 15000,
            'description': 'کود نیتروژنه'
        },
        'AMMONIUM_NITRATE': {
            'name': 'نیترات آمونیوم',
            'n_percent': 34,
            'p_percent': 0,
            'k_percent': 0,
            'price_per_kg': 18000,
            'description': 'کود نیتروژنه'
        },
        'SUPER_PHOSPHATE': {
            'name': 'سوپر فسفات',
            'n_percent': 0,
            'p_percent': 20,
            'k_percent': 0,
            'price_per_kg': 12000,
            'description': 'کود فسفره'
        },
        'POTASSIUM_SULFATE': {
            'name': 'سولفات پتاسیم',
            'n_percent': 0,
            'p_percent': 0,
            'k_percent': 50,
            'price_per_kg': 22000,
            'description': 'کود پتاسه'
        },
        'POTASSIUM_CHLORIDE': {
            'name': 'کلرید پتاسیم',
            'n_percent': 0,
            'p_percent': 0,
            'k_percent': 60,
            'price_per_kg': 18000,
            'description': 'کود پتاسه'
        },
        'IRON_SULFATE': {
            'name': 'سولفات آهن',
            'n_percent': 0,
            'p_percent': 0,
            'k_percent': 0,
            'price_per_kg': 25000,
            'description': 'کود ریزمغذی آهن'
        },
        'ZINC_SULFATE': {
            'name': 'سولفات روی',
            'n_percent': 0,
            'p_percent': 0,
            'k_percent': 0,
            'price_per_kg': 28000,
            'description': 'کود ریزمغذی روی'
        },
        'MANGANESE_SULFATE': {
            'name': 'سولفات منگنز',
            'n_percent': 0,
            'p_percent': 0,
            'k_percent': 0,
            'price_per_kg': 24000,
            'description': 'کود ریزمغذی منگنز'
        },
        'COPPER_SULFATE': {
            'name': 'سولفات مس',
            'n_percent': 0,
            'p_percent': 0,
            'k_percent': 0,
            'price_per_kg': 30000,
            'description': 'کود ریزمغذی مس'
        },
        'COMPOST': {
            'name': 'کمپوست',
            'n_percent': 1.5,
            'p_percent': 0.5,
            'k_percent': 1.0,
            'price_per_kg': 2000,
            'description': 'کود آلی'
        },
        'MANURE': {
            'name': 'کود دامی پوسیده',
            'n_percent': 2.0,
            'p_percent': 1.0,
            'k_percent': 2.0,
            'price_per_kg': 1500,
            'description': 'کود آلی'
        },
    }

    # ============ نیاز کودی هر محصول ============
    CROP_FERTILIZER_NEEDS = {
        'گندم': {
            'nitrogen': {'min': 120, 'max': 180, 'optimal': 150},
            'phosphorus': {'min': 60, 'max': 100, 'optimal': 80},
            'potassium': {'min': 80, 'max': 120, 'optimal': 100},
            'iron': {'min': 0, 'max': 20, 'optimal': 10},
            'zinc': {'min': 0, 'max': 10, 'optimal': 5},
            'manganese': {'min': 0, 'max': 10, 'optimal': 5},
        },
        'پسته': {
            'nitrogen': {'min': 80, 'max': 120, 'optimal': 100},
            'phosphorus': {'min': 40, 'max': 80, 'optimal': 60},
            'potassium': {'min': 100, 'max': 160, 'optimal': 130},
            'iron': {'min': 5, 'max': 25, 'optimal': 15},
            'zinc': {'min': 5, 'max': 15, 'optimal': 10},
            'manganese': {'min': 0, 'max': 15, 'optimal': 8},
        },
        'برنج': {
            'nitrogen': {'min': 100, 'max': 150, 'optimal': 130},
            'phosphorus': {'min': 50, 'max': 80, 'optimal': 65},
            'potassium': {'min': 60, 'max': 100, 'optimal': 80},
            'iron': {'min': 0, 'max': 15, 'optimal': 8},
            'zinc': {'min': 0, 'max': 8, 'optimal': 4},
            'manganese': {'min': 0, 'max': 10, 'optimal': 5},
        },
        'ذرت': {
            'nitrogen': {'min': 150, 'max': 220, 'optimal': 180},
            'phosphorus': {'min': 60, 'max': 100, 'optimal': 80},
            'potassium': {'min': 100, 'max': 160, 'optimal': 130},
            'iron': {'min': 0, 'max': 20, 'optimal': 10},
            'zinc': {'min': 0, 'max': 10, 'optimal': 5},
            'manganese': {'min': 0, 'max': 10, 'optimal': 5},
        },
        'چغندر قند': {
            'nitrogen': {'min': 100, 'max': 160, 'optimal': 130},
            'phosphorus': {'min': 50, 'max': 90, 'optimal': 70},
            'potassium': {'min': 120, 'max': 180, 'optimal': 150},
            'iron': {'min': 0, 'max': 15, 'optimal': 8},
            'zinc': {'min': 0, 'max': 10, 'optimal': 5},
            'manganese': {'min': 0, 'max': 10, 'optimal': 5},
        },
        'پنبه': {
            'nitrogen': {'min': 120, 'max': 180, 'optimal': 150},
            'phosphorus': {'min': 40, 'max': 80, 'optimal': 60},
            'potassium': {'min': 80, 'max': 140, 'optimal': 110},
            'iron': {'min': 0, 'max': 20, 'optimal': 10},
            'zinc': {'min': 5, 'max': 15, 'optimal': 10},
            'manganese': {'min': 0, 'max': 10, 'optimal': 5},
        },
        'زعفران': {
            'nitrogen': {'min': 40, 'max': 80, 'optimal': 60},
            'phosphorus': {'min': 30, 'max': 60, 'optimal': 45},
            'potassium': {'min': 60, 'max': 100, 'optimal': 80},
            'iron': {'min': 0, 'max': 15, 'optimal': 8},
            'zinc': {'min': 0, 'max': 8, 'optimal': 4},
            'manganese': {'min': 0, 'max': 10, 'optimal': 5},
        },
    }

    # ==================== توابع اقلیمی ====================
    
    @classmethod
    def get_climate_factors(cls, province_name, month):
        """
        دریافت عوامل اقلیمی برای استان و ماه مشخص
        """
        from .models import ClimateData, Province
        
        try:
            province = Province.objects.get(name=province_name)
            climate = ClimateData.objects.filter(
                province=province,
                month=month,
                year=2024
            ).first()
            
            if not climate:
                return {
                    'avg_temperature': 20,
                    'rainfall': 30,
                    'humidity': 50,
                    'sunny_days': 25,
                }
            
            return {
                'avg_temperature': climate.avg_temperature,
                'rainfall': climate.rainfall,
                'humidity': climate.humidity,
                'sunny_days': climate.sunny_days,
            }
        except:
            return {
                'avg_temperature': 20,
                'rainfall': 30,
                'humidity': 50,
                'sunny_days': 25,
            }
    
    @classmethod
    def get_crop_suitability_with_climate(cls, crop_name, soil_data, climate_data):
        """
        محاسبه تناسب محصول با در نظر گرفتن شرایط اقلیمی
        """
        climate_requirements = {
            'گندم': {'temp': {'min': 10, 'max': 25}, 'rain': {'min': 200, 'max': 600}},
            'پسته': {'temp': {'min': 15, 'max': 35}, 'rain': {'min': 150, 'max': 400}},
            'برنج': {'temp': {'min': 20, 'max': 35}, 'rain': {'min': 600, 'max': 1500}},
            'ذرت': {'temp': {'min': 18, 'max': 32}, 'rain': {'min': 400, 'max': 800}},
            'چغندر قند': {'temp': {'min': 10, 'max': 25}, 'rain': {'min': 300, 'max': 600}},
            'پنبه': {'temp': {'min': 20, 'max': 38}, 'rain': {'min': 400, 'max': 800}},
            'زعفران': {'temp': {'min': 5, 'max': 25}, 'rain': {'min': 200, 'max': 400}},
        }
        
        req = climate_requirements.get(crop_name, {})
        if not req:
            return 50
        
        temp = climate_data.get('avg_temperature', 20)
        temp_score = 50
        if req['temp']['min'] <= temp <= req['temp']['max']:
            temp_score = 100
        elif temp < req['temp']['min']:
            temp_score = max(0, (temp / req['temp']['min']) * 70)
        else:
            temp_score = max(0, (req['temp']['max'] / temp) * 70)
        
        rain = climate_data.get('rainfall', 30) * 12
        rain_score = 50
        if req['rain']['min'] <= rain <= req['rain']['max']:
            rain_score = 100
        elif rain < req['rain']['min']:
            rain_score = max(0, (rain / req['rain']['min']) * 70)
        else:
            rain_score = max(0, (req['rain']['max'] / rain) * 70)
        
        return (temp_score * 0.6 + rain_score * 0.4)
    
    # ==================== توابع محاسبه امتیاز ====================
    
    @classmethod
    def calculate_crop_score(cls, crop_name, ph, ec, organic_matter, texture, 
                            nitrogen=None, phosphorus=None, potassium=None):
        """
        محاسبه امتیاز تناسب محصول با وزن‌های اختصاصی
        """
        crop_data = cls.CROP_MATCHING.get(crop_name)
        if not crop_data:
            return 50
        
        weights = cls.CROP_WEIGHTS.get(crop_name, {})
        if not weights:
            return 50
        
        total_score = 0
        total_weight = 0
        
        # ۱. امتیاز pH
        if 'ph' in weights:
            ph_score = 50
            if crop_data['ph']['min'] <= ph <= crop_data['ph']['max']:
                ph_score = 100
            elif ph < crop_data['ph']['min']:
                ph_score = max(0, (ph / crop_data['ph']['min']) * 70)
            else:
                ph_score = max(0, (crop_data['ph']['max'] / ph) * 70)
            total_score += ph_score * weights['ph']
            total_weight += weights['ph']
        
        # ۲. امتیاز EC
        if 'ec' in weights:
            ec_score = 50
            if ec <= crop_data['ec']['max']:
                ec_score = 100
            else:
                ec_score = max(0, (crop_data['ec']['max'] / ec) * 70)
            total_score += ec_score * weights['ec']
            total_weight += weights['ec']
        
        # ۳. امتیاز ماده آلی
        if 'organic_matter' in weights:
            om_score = 50
            if organic_matter >= crop_data['organic_matter']['min']:
                om_score = 100
            else:
                om_score = max(0, (organic_matter / crop_data['organic_matter']['min']) * 70)
            total_score += om_score * weights['organic_matter']
            total_weight += weights['organic_matter']
        
        # ۴. امتیاز بافت خاک
        if 'texture' in weights:
            texture_score = 100 if texture in crop_data['texture'] else 30
            total_score += texture_score * weights['texture']
            total_weight += weights['texture']
        
        # ۵. امتیاز نیتروژن
        if 'nitrogen' in weights and nitrogen is not None and nitrogen > 0:
            n_score = min(100, (nitrogen / 60) * 100)
            total_score += n_score * weights['nitrogen']
            total_weight += weights['nitrogen']
        
        # ۶. امتیاز فسفر
        if 'phosphorus' in weights and phosphorus is not None and phosphorus > 0:
            p_score = min(100, (phosphorus / 22) * 100)
            total_score += p_score * weights['phosphorus']
            total_weight += weights['phosphorus']
        
        # ۷. امتیاز پتاسیم
        if 'potassium' in weights and potassium is not None and potassium > 0:
            k_score = min(100, (potassium / 220) * 100)
            total_score += k_score * weights['potassium']
            total_weight += weights['potassium']
        
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 50
        
        return int(min(100, max(0, final_score)))
    
    # ==================== توابع اصلی تحلیل ====================
    
    @classmethod
    def calculate_health_index(cls, ph, ec, organic_matter, nitrogen=None, phosphorus=None, potassium=None,
                               iron=None, zinc=None, manganese=None, copper=None):
        """
        محاسبه شاخص سلامت خاک (DSHI)
        خروجی: عددی بین ۰ تا ۱۰۰
        """
        scores = []
        
        # ۱. امتیاز pH (وزن: ۲۵٪)
        if 6.0 <= ph <= 7.5:
            ph_score = 100
        elif 5.5 <= ph < 6.0 or 7.5 < ph <= 8.0:
            ph_score = 70
        elif 5.0 <= ph < 5.5 or 8.0 < ph <= 8.5:
            ph_score = 40
        else:
            ph_score = 20
        scores.append(ph_score * 0.25)
        
        # ۲. امتیاز EC (وزن: ۲۰٪)
        if ec <= 0.5:
            ec_score = 100
        elif 0.5 < ec <= 1.0:
            ec_score = 85
        elif 1.0 < ec <= 2.0:
            ec_score = 60
        elif 2.0 < ec <= 3.0:
            ec_score = 35
        else:
            ec_score = 15
        scores.append(ec_score * 0.20)
        
        # ۳. امتیاز ماده آلی (وزن: ۲۰٪)
        if organic_matter >= 3.0:
            om_score = 100
        elif 2.0 <= organic_matter < 3.0:
            om_score = 75
        elif 1.0 <= organic_matter < 2.0:
            om_score = 45
        else:
            om_score = 20
        scores.append(om_score * 0.20)
        
        # ۴. امتیاز عناصر اصلی NPK (وزن: ۳۰٪)
        npk_weight = 0.30
        if nitrogen is not None and phosphorus is not None and potassium is not None:
            n_score = min(100, (nitrogen / 60) * 100) if nitrogen > 0 else 0
            p_score = min(100, (phosphorus / 22) * 100) if phosphorus > 0 else 0
            k_score = min(100, (potassium / 220) * 100) if potassium > 0 else 0
            npk_score = (n_score + p_score + k_score) / 3
            scores.append(npk_score * npk_weight)
        else:
            remaining_weight = npk_weight / 3
            for i in range(3):
                if scores[i] > 0:
                    scores[i] = scores[i] * (1 + remaining_weight / scores[i])
        
        # ۵. عناصر ریزمغذی (وزن: هر کدوم ۵٪ = مجموعاً ۲۰٪)
        micronutrients = [
            ('iron', iron, 'آهن'),
            ('zinc', zinc, 'روی'),
            ('manganese', manganese, 'منگنز'),
            ('copper', copper, 'مس'),
        ]
        
        micronutrient_weight = 0.05
        micronutrient_count = 0
        
        for name, value, label in micronutrients:
            if value is not None and value > 0:
                optimal = cls.OPTIMAL_RANGES[name]
                if optimal['min'] <= value <= optimal['max']:
                    mn_score = 100
                elif value < optimal['min']:
                    mn_score = max(0, (value / optimal['min']) * 70)
                else:
                    mn_score = max(0, (optimal['max'] / value) * 70)
                scores.append(mn_score * micronutrient_weight)
                micronutrient_count += 1
        
        if micronutrient_count == 0:
            total_micronutrient_weight = micronutrient_weight * 4
            if len(scores) > 0:
                for i in range(len(scores)):
                    scores[i] = scores[i] * (1 + total_micronutrient_weight / len(scores))
        
        total_score = sum(scores)
        return min(100, max(0, total_score))
    
    @classmethod
    def get_health_level(cls, index):
        """دریافت سطح سلامت بر اساس شاخص"""
        if index >= 80:
            return 'EXCELLENT', 'عالی'
        elif index >= 60:
            return 'GOOD', 'خوب'
        elif index >= 40:
            return 'FAIR', 'متوسط'
        else:
            return 'POOR', 'ضعیف'
    
    @classmethod
    def get_crop_recommendations(cls, ph, ec, organic_matter, texture, nitrogen=None, phosphorus=None, potassium=None,
                                iron=None, zinc=None, manganese=None, copper=None):
        """
        دریافت توصیه‌های محصول بر اساس داده‌های خاک با وزن‌دهی اختصاصی
        """
        recommendations = []
        
        for crop_name, crop_data in cls.CROP_MATCHING.items():
            # بررسی اولیه (فیلتر کردن سریع)
            ph_ok = crop_data['ph']['min'] <= ph <= crop_data['ph']['max']
            if not ph_ok:
                continue
            
            ec_ok = ec <= crop_data['ec']['max']
            if not ec_ok:
                continue
            
            texture_ok = texture in crop_data['texture']
            if not texture_ok:
                continue
            
            om_ok = organic_matter >= crop_data['organic_matter']['min']
            if not om_ok:
                continue
            
            # محاسبه امتیاز با وزن‌های اختصاصی
            suitability_score = cls.calculate_crop_score(
                crop_name, ph, ec, organic_matter, texture,
                nitrogen, phosphorus, potassium
            )
            
            # امتیاز ریزمغذی‌ها
            micronutrient_score = 0
            crop_micro = crop_data.get('micronutrients', {})
            
            if crop_micro and iron is not None and zinc is not None and manganese is not None:
                if iron >= crop_micro.get('iron', 4.5):
                    micronutrient_score += 5
                if zinc >= crop_micro.get('zinc', 1.0):
                    micronutrient_score += 5
                if manganese >= crop_micro.get('manganese', 2.5):
                    micronutrient_score += 5
                if copper is not None and copper >= crop_micro.get('copper', 0.3):
                    micronutrient_score += 5
            
            suitability_score += micronutrient_score
            
            # محاسبه سود پیش‌بینی شده
            yield_factor = suitability_score / 100
            predicted_yield = crop_data['avg_yield'] * (0.7 + 0.3 * yield_factor)
            predicted_profit = crop_data['min_profit'] * (0.8 + 0.4 * yield_factor)
            
            # توصیه‌های کودی دقیق
            fertilizer_advice = cls.calculate_fertilizer_recommendations(crop_name, {
                'ph': ph,
                'ec': ec,
                'organic_matter': organic_matter,
                'nitrogen': nitrogen,
                'phosphorus': phosphorus,
                'potassium': potassium,
                'iron': iron,
                'zinc': zinc,
                'manganese': manganese,
                'copper': copper,
            })
            
            recommendations.append({
                'crop_name': crop_name,
                'crop_type': 'زراعی',
                'suitability_score': min(100, suitability_score),
                'predicted_yield': round(predicted_yield, 2),
                'predicted_profit': int(predicted_profit),
                'fertilizer_advice': fertilizer_advice,
                'irrigation_advice': cls._get_irrigation_advice(crop_name, texture),
                'planting_advice': cls._get_planting_advice(crop_name),
                'harvest_advice': cls._get_harvest_advice(crop_name),
            })
        
        recommendations.sort(key=lambda x: x['suitability_score'], reverse=True)
        return recommendations
    
    # ==================== توابع توصیه کودی دقیق ====================
    
    @classmethod
    def calculate_fertilizer_recommendations(cls, crop_name, soil_data):
        """
        محاسبه توصیه‌های کودی دقیق بر اساس محصول و وضعیت خاک
        """
        crop_needs = cls.CROP_FERTILIZER_NEEDS.get(crop_name)
        if not crop_needs:
            return []
        
        recommendations = []
        
        # ۱. نیتروژن (N)
        if 'nitrogen' in crop_needs:
            need = crop_needs['nitrogen']
            soil_n = soil_data.get('nitrogen', 0) or 0
            n_deficit = max(0, need['optimal'] - soil_n * 0.3)
            
            if n_deficit > 10:
                if n_deficit > 80:
                    fertilizer_key = 'UREA'
                    amount = n_deficit / 0.46
                else:
                    fertilizer_key = 'AMMONIUM_NITRATE'
                    amount = n_deficit / 0.34
                
                fert = cls.FERTILIZERS[fertilizer_key]
                recommendations.append({
                    'fertilizer_type': fertilizer_key,
                    'fertilizer_name': fert['name'],
                    'amount': round(amount, 1),
                    'unit': 'کیلوگرم در هکتار',
                    'timing': 'قبل از کاشت و مرحله رشد رویشی',
                    'method': 'مصرف سرک یا نواری',
                    'cost': round(amount * fert['price_per_kg']),
                    'description': f'تامین نیتروژن مورد نیاز ({round(n_deficit)} کیلوگرم N خالص)'
                })
        
        # ۲. فسفر (P)
        if 'phosphorus' in crop_needs:
            need = crop_needs['phosphorus']
            soil_p = soil_data.get('phosphorus', 0) or 0
            p_deficit = max(0, need['optimal'] - soil_p * 0.2)
            
            if p_deficit > 5:
                fert = cls.FERTILIZERS['SUPER_PHOSPHATE']
                amount = p_deficit / 0.20
                recommendations.append({
                    'fertilizer_type': 'SUPER_PHOSPHATE',
                    'fertilizer_name': fert['name'],
                    'amount': round(amount, 1),
                    'unit': 'کیلوگرم در هکتار',
                    'timing': 'قبل از کاشت',
                    'method': 'مصرف در عمق ۱۰-۱۵ سانتی‌متر',
                    'cost': round(amount * fert['price_per_kg']),
                    'description': f'تامین فسفر مورد نیاز ({round(p_deficit)} کیلوگرم P خالص)'
                })
        
        # ۳. پتاسیم (K)
        if 'potassium' in crop_needs:
            need = crop_needs['potassium']
            soil_k = soil_data.get('potassium', 0) or 0
            k_deficit = max(0, need['optimal'] - soil_k * 0.1)
            
            if k_deficit > 20:
                if soil_data.get('ec', 0) > 3.0:
                    fertilizer_key = 'POTASSIUM_SULFATE'
                else:
                    fertilizer_key = 'POTASSIUM_CHLORIDE'
                
                fert = cls.FERTILIZERS[fertilizer_key]
                amount = k_deficit / (fert['k_percent'] / 100)
                recommendations.append({
                    'fertilizer_type': fertilizer_key,
                    'fertilizer_name': fert['name'],
                    'amount': round(amount, 1),
                    'unit': 'کیلوگرم در هکتار',
                    'timing': 'قبل از کاشت و مرحله رشد رویشی',
                    'method': 'مصرف نواری',
                    'cost': round(amount * fert['price_per_kg']),
                    'description': f'تامین پتاسیم مورد نیاز ({round(k_deficit)} کیلوگرم K خالص)'
                })
        
        # ۴. کمپوست/کود آلی
        if soil_data.get('organic_matter', 0) < 2.0:
            compost_amount = (2.0 - soil_data['organic_matter']) * 5
            fert = cls.FERTILIZERS['COMPOST']
            recommendations.append({
                'fertilizer_type': 'COMPOST',
                'fertilizer_name': fert['name'],
                'amount': round(compost_amount, 1),
                'unit': 'تن در هکتار',
                'timing': 'قبل از کاشت',
                'method': 'مصرف سطحی و اختلاط با خاک',
                'cost': round(compost_amount * 1000 * fert['price_per_kg']),
                'description': f'افزایش ماده آلی خاک (فعلی: {soil_data["organic_matter"]}%)'
            })
        
        # ۵. ریزمغذی‌ها
        micronutrients = [
            ('iron', 'IRON_SULFATE', 'آهن', 4.5),
            ('zinc', 'ZINC_SULFATE', 'روی', 0.8),
            ('manganese', 'MANGANESE_SULFATE', 'منگنز', 2.0),
            ('copper', 'COPPER_SULFATE', 'مس', 0.2),
        ]
        
        for soil_key, fert_key, name, threshold in micronutrients:
            value = soil_data.get(soil_key, 0) or 0
            if value > 0 and value < threshold:
                deficit = threshold - value
                fert = cls.FERTILIZERS[fert_key]
                amount = deficit * 10
                recommendations.append({
                    'fertilizer_type': fert_key,
                    'fertilizer_name': fert['name'],
                    'amount': round(min(amount, 50), 1),
                    'unit': 'کیلوگرم در هکتار',
                    'timing': 'مرحله رشد رویشی',
                    'method': 'محلول‌پاشی یا مصرف خاکی',
                    'cost': round(amount * fert['price_per_kg']),
                    'description': f'رفع کمبود {name} (مقدار فعلی: {value} ppm)'
                })
        
        # مرتب‌سازی بر اساس اولویت
        priority_order = ['UREA', 'AMMONIUM_NITRATE', 'SUPER_PHOSPHATE', 
                          'POTASSIUM_SULFATE', 'POTASSIUM_CHLORIDE', 'COMPOST']
        recommendations.sort(key=lambda x: priority_order.index(x['fertilizer_type']) 
                             if x['fertilizer_type'] in priority_order else 999)
        
        return recommendations
    
    # ==================== توابع کمکی ====================
    
    @classmethod
    def _get_irrigation_advice(cls, crop, texture):
        """دریافت توصیه آبیاری بر اساس محصول و بافت خاک"""
        if texture in ['SANDY', 'LOAMY_SAND', 'SANDY_LOAM']:
            return 'آبیاری با فواصل کوتاه و حجم کم (خاک سبک)'
        elif texture in ['CLAY', 'SILTY_CLAY_LOAM']:
            return 'آبیاری با فواصل بلند و حجم زیاد (خاک سنگین)'
        else:
            return 'آبیاری متوسط و منظم'
    
    @classmethod
    def _get_planting_advice(cls, crop):
        """دریافت توصیه کاشت بر اساس محصول"""
        advice = {
            'گندم': 'کاشت در پاییز، عمق ۵-۷ سانتی‌متر، تراکم ۴۰۰-۴۵۰ بوته در متر مربع',
            'پسته': 'کاشت در اوایل بهار، فاصله ۶×۶ متر، نهال یکساله',
            'برنج': 'کاشت در اوایل بهار، نشاکاری با فاصله ۲۰×۲۰ سانتی‌متر',
            'ذرت': 'کاشت در بهار، عمق ۵-۸ سانتی‌متر، فاصله ۷۵×۱۵ سانتی‌متر',
            'چغندر قند': 'کاشت در بهار، عمق ۲-۳ سانتی‌متر، فاصله ۵۰×۲۰ سانتی‌متر',
            'پنبه': 'کاشت در بهار، عمق ۳-۵ سانتی‌متر، فاصله ۸۰×۲۰ سانتی‌متر',
            'زعفران': 'کاشت در تابستان، عمق ۱۵-۲۰ سانتی‌متر، تراکم ۱۰۰-۱۵۰ پیاز در متر مربع',
        }
        return advice.get(crop, 'مشاوره با کارشناس کشاورزی توصیه می‌شود')
    
    @classmethod
    def _get_harvest_advice(cls, crop):
        """دریافت توصیه برداشت بر اساس محصول"""
        advice = {
            'گندم': 'برداشت در اواخر بهار یا اوایل تابستان، زمانی که دانه‌ها سفت و زرد شوند',
            'پسته': 'برداشت در شهریور-مهر، زمانی که پوسته خارجی شروع به شکافتن کند',
            'برنج': 'برداشت در شهریور-مهر، زمانی که ۸۰٪ دانه‌ها قهوه‌ای شوند',
            'ذرت': 'برداشت در اواخر تابستان، زمانی که برگ‌های پایین خشک شوند',
            'چغندر قند': 'برداشت در پاییز، قبل از یخبندان',
            'پنبه': 'برداشت در شهریور-مهر، زمانی که ۶۰٪ غوزه‌ها باز شوند',
            'زعفران': 'برداشت در آبان-آذر، صبح زود و با دست',
        }
        return advice.get(crop, 'زمان برداشت با توجه به شرایط منطقه')
    
    # ==================== تابع اصلی تحلیل ====================
    
    @classmethod
    def analyze_soil(cls, data, province_name=None):
        """
        تحلیل کامل خاک با قابلیت دریافت استان برای داده‌های اقلیمی
        """
        # محاسبه شاخص سلامت
        health_index = cls.calculate_health_index(
            data['ph'], data['ec'], data['organic_matter'],
            data.get('nitrogen'), data.get('phosphorus'), data.get('potassium'),
            data.get('iron'), data.get('zinc'), data.get('manganese'), data.get('copper')
        )
        health_level_code, health_level_display = cls.get_health_level(health_index)
        
        # دریافت توصیه‌های محصول
        crop_recommendations = cls.get_crop_recommendations(
            data['ph'], data['ec'], data['organic_matter'], data['texture'],
            data.get('nitrogen'), data.get('phosphorus'), data.get('potassium'),
            data.get('iron'), data.get('zinc'), data.get('manganese'), data.get('copper')
        )
        
        # داده‌های اقلیمی
        climate_data = None
        if province_name:
            current_month = timezone.now().month
            climate_data = cls.get_climate_factors(province_name, current_month)
            
            if climate_data and crop_recommendations:
                for crop in crop_recommendations:
                    climate_score = cls.get_crop_suitability_with_climate(
                        crop['crop_name'],
                        data,
                        climate_data
                    )
                    crop['suitability_score'] = int((crop['suitability_score'] * 0.7 + climate_score * 0.3))
                    crop['climate_score'] = int(climate_score)
                
                crop_recommendations.sort(key=lambda x: x['suitability_score'], reverse=True)
        
        best_crop = crop_recommendations[0] if crop_recommendations else None
        
        return {
            'soil_health_index': round(health_index, 1),
            'soil_health_level': health_level_code,
            'soil_health_display': health_level_display,
            'recommended_crops': crop_recommendations,
            'best_crop': best_crop,
            'climate_data': climate_data,
            'summary': cls._generate_summary(data, health_index, best_crop),
        }
    
    @classmethod
    def _generate_summary(cls, data, health_index, best_crop):
        """تولید خلاصه تحلیل"""
        summary = []
        
        if health_index >= 80:
            summary.append('خاک شما در وضعیت عالی قرار دارد و برای کشت محصولات مختلف مناسب است.')
        elif health_index >= 60:
            summary.append('خاک شما وضعیت خوبی دارد، با مدیریت صحیح می‌توانید به حداکثر بهره‌وری برسید.')
        elif health_index >= 40:
            summary.append('خاک شما نیاز به بهبود دارد. با اجرای توصیه‌های مدیریتی می‌توانید سلامت خاک را افزایش دهید.')
        else:
            summary.append('خاک شما در وضعیت ضعیفی قرار دارد و نیاز به اصلاح اساسی دارد.')
        
        if best_crop:
            summary.append(
                f'بهترین محصول پیشنهادی برای خاک شما: {best_crop["crop_name"]} با '
                f'امتیاز تناسب {best_crop["suitability_score"]} و سود پیش‌بینی شده '
                f'{best_crop["predicted_profit"]:,} تومان در هکتار.'
            )
        else:
            summary.append('بر اساس داده‌های موجود، محصول مناسبی برای خاک شما یافت نشد.')
        
        # توصیه ریزمغذی‌ها (اگر در best_crop وجود داشت)
        if best_crop and best_crop.get('fertilizer_advice'):
            if isinstance(best_crop['fertilizer_advice'], list):
                micronutrient_advice = [adv for adv in best_crop['fertilizer_advice'] 
                                       if adv['fertilizer_type'] in ['IRON_SULFATE', 'ZINC_SULFATE', 
                                                                     'MANGANESE_SULFATE', 'COPPER_SULFATE']]
                if micronutrient_advice:
                    summary.append('توصیه ریزمغذی‌ها: ' + ' | '.join([adv['fertilizer_name'] + ': ' + str(adv['amount']) + ' ' + adv['unit'] 
                                                                      for adv in micronutrient_advice]))
        
        return ' '.join(summary)