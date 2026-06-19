from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, ProfileView, LogoutView,
    ProfileDetailView, ProfileUpdateView, UserFarmsView, UserAnalysesView,
    SubscriptionListView, UserSubscriptionView, PurchaseSubscriptionView ,     DashboardStatsView

)

urlpatterns = [
    # ============ احراز هویت ============
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    
    # ============ پروفایل ============
    path('api/profile/', ProfileView.as_view(), name='profile'),
    path('api/profile/detail/', ProfileDetailView.as_view(), name='profile_detail'),
    path('api/profile/update/', ProfileUpdateView.as_view(), name='profile_update'),
    path('api/profile/farms/', UserFarmsView.as_view(), name='user_farms'),
    path('api/profile/analyses/', UserAnalysesView.as_view(), name='user_analyses'),
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard_stats'),

    
    # ============ اشتراک ============
    path('api/subscriptions/plans/', SubscriptionListView.as_view(), name='subscription_plans'),  
    path('api/subscriptions/my/', UserSubscriptionView.as_view(), name='my_subscription'),
    path('api/subscriptions/purchase/', PurchaseSubscriptionView.as_view(), name='purchase_subscription'),
]