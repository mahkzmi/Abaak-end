from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """فقط کاربران با نقش ADMIN"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'


class IsExpert(BasePermission):
    """فقط کاربران با نقش EXPERT"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'EXPERT'


class IsLab(BasePermission):
    """فقط کاربران با نقش LAB"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'LAB'


class IsFarmer(BasePermission):
    """فقط کاربران با نقش FARMER"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'FARMER'


class IsAdminOrExpert(BasePermission):
    """کاربران با نقش ADMIN یا EXPERT"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
            return False
        return request.user.profile.role in ['ADMIN', 'EXPERT']


class IsLabOrExpert(BasePermission):
    """کاربران با نقش LAB یا EXPERT"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
            return False
        return request.user.profile.role in ['LAB', 'EXPERT']


class IsOwnerOrReadOnly(BasePermission):
    """فقط مالک می‌تواند تغییر دهد، بقیه فقط می‌توانند بخوانند"""
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        # بررسی اینکه کاربر مالک است
        if hasattr(obj, 'farmer') and hasattr(obj.farmer, 'user'):
            return obj.farmer.user == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsVerifiedLabSample(BasePermission):
    """فقط کاربران با نقش LAB می‌توانند نمونه ثبت کنند"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not hasattr(request.user, 'profile'):
            return False
        return request.user.profile.role in ['LAB', 'ADMIN', 'EXPERT']