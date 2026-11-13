from rest_framework.permissions import BasePermission


def _profile(request):
    if not request.user.is_authenticated:
        return None
    return getattr(request.user, 'profile', None)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        profile = _profile(request)
        return bool(request.user.is_authenticated and (request.user.is_superuser or (profile and profile.role == 'ADMIN')))


class IsExpert(BasePermission):
    def has_permission(self, request, view):
        profile = _profile(request)
        return bool(request.user.is_authenticated and (request.user.is_superuser or (profile and profile.role == 'EXPERT')))


class IsLab(BasePermission):
    def has_permission(self, request, view):
        profile = _profile(request)
        return bool(request.user.is_authenticated and profile and profile.role == 'LAB' and profile.is_verified)


class IsFarmer(BasePermission):
    def has_permission(self, request, view):
        profile = _profile(request)
        return bool(request.user.is_authenticated and profile and profile.role == 'FARMER')


class IsAdminOrExpert(BasePermission):
    def has_permission(self, request, view):
        profile = _profile(request)
        return bool(request.user.is_authenticated and (request.user.is_superuser or (profile and profile.role in ['ADMIN', 'EXPERT'])))


class IsLabOrExpert(BasePermission):
    def has_permission(self, request, view):
        profile = _profile(request)
        if request.user.is_superuser:
            return True
        return bool(profile and (profile.role == 'EXPERT' or (profile.role == 'LAB' and profile.is_verified)))


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        if hasattr(obj, 'farmer') and hasattr(obj.farmer, 'user'):
            return obj.farmer.user_id == request.user.id
        if hasattr(obj, 'user'):
            return obj.user_id == request.user.id
        return False


class IsVerifiedLabSample(BasePermission):
    def has_permission(self, request, view):
        profile = _profile(request)
        if request.user.is_superuser:
            return True
        return bool(profile and (
            profile.role in ['ADMIN', 'EXPERT']
            or (profile.role == 'LAB' and profile.is_verified)
        ))
