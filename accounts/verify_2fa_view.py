from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from rental_erp.mfa import mfa_manager
from audit.models import AuditLog
from .models import User


def get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def verify_2fa(request):
    """
    2FA verification during login.
    User has already entered username/password, now needs to provide TOTP code.
    """
    # Check if there's a pending 2FA user
    user_id = request.session.get('pending_2fa_user_id')
    if not user_id:
        messages.error(request, 'No pending authentication. Please login again.')
        return redirect('accounts:login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Invalid session. Please login again.')
        return redirect('login')
    
    if request.method == 'POST':
        token = request.POST.get('token', '').strip()
        
        # Verify the token
        is_valid = mfa_manager.verify_mfa_method(user, 'totp', token)
        
        if is_valid:
            # Clear pending session data
            remember_me = request.session.get('pending_2fa_remember_me', False)
            del request.session['pending_2fa_user_id']
            if 'pending_2fa_remember_me' in request.session:
                del request.session['pending_2fa_remember_me']
            
            # Login the user
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Log successful login with 2FA
            AuditLog.objects.create(
                user=user,
                user_email=user.email,
                user_role=user.role,
                action_type='login',
                model_name='User',
                object_id=str(user.id),
                object_repr=str(user.email),
                description=f'User login with 2FA: {user.email}',
                ip_address=get_client_ip(request),
                session_key=request.session.session_key,
            )
            
            # Remember me functionality
            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
            
            messages.success(request, '🔐 Login successful with 2FA!')
            next_url = request.GET.get('next', 'dashboards:dashboard')
            return redirect(next_url)
        else:
            # Log failed 2FA attempt
            AuditLog.objects.create(
                user=user,
                user_email=user.email,
                user_role=user.role,
                action_type='login',
                model_name='User',
                object_id=str(user.id),
                object_repr=str(user.email),
                description=f'Failed 2FA verification: {user.email}',
                ip_address=get_client_ip(request),
            )
            
            messages.error(request, 'Invalid verification code. Please try again.')
    
    context = {
        'email': user.email,
    }
    return render(request, 'accounts/verify_2fa.html', context)
