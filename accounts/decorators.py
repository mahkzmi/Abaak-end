from django.core.exceptions import PermissionDenied
from functools import wraps


def role_required(*roles):
    """
    دکوراتور برای محدود کردن دسترسی به viewها بر اساس نقش
    استفاده: @role_required('ADMIN', 'EXPERT')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied('لطفاً وارد شوید')
            if not hasattr(request.user, 'profile'):
                raise PermissionDenied('پروفایل کاربر یافت نشد')
            if request.user.profile.role not in roles:
                raise PermissionDenied('شما دسترسی لازم را ندارید')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator