from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProvinceViewSet, CountyViewSet, FarmViewSet, SoilAnalysisViewSet, SoilSampleViewSet

router = DefaultRouter()
router.register(r'provinces', ProvinceViewSet)
router.register(r'counties', CountyViewSet, basename='county')  
router.register(r'farms', FarmViewSet)
router.register(r'soil-samples', SoilSampleViewSet)
router.register(r'analyses', SoilAnalysisViewSet, basename='analysis')


urlpatterns = [
    path('api/', include(router.urls)),
]