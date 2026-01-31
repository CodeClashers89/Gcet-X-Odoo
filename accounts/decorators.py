from django.shortcuts import redirect
from django.http import HttpResponseForbidden

def role_required(allowed_roles):
    """
    Decorator to restrict view access by user role.
    Business Use: RBAC enforcement (customer-only views, vendor-only views, etc.)
    
    Usage:
    @role_required(['customer'])
    def view_func(request):
        ...
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            if request.user.role not in allowed_roles:
                return HttpResponseForbidden('You do not have access to this page.')
            
            return view_func(request, *args, **kwargs)
        
        wrapper.__name__ = view_func.__name__
        return wrapper
    
    return decorator
