"""
Two-Factor Authentication (2FA) Views
Handles TOTP setup, verification, backup codes, and 2FA management.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from rental_erp.mfa import mfa_manager
from audit.models import AuditLog

User = get_user_model()


@login_required
def setup_2fa(request):
    """
    Setup page for enabling 2FA.
    Shows QR code and backup codes.
    """
    user = request.user
    
    # If 2FA already enabled, redirect to manage page
    if user.totp_enabled:
        messages.info(request, '2FA is already enabled for your account.')
        return redirect('accounts:manage_2fa')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate':
            # Generate TOTP secret and QR code
            setup_data = mfa_manager.setup_totp(user)
            
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Setup data: secret={setup_data.get('secret')}, qr_code={'present' if setup_data.get('qr_code') else 'None'}, backup_codes={len(setup_data.get('backup_codes', []))}")
            
            # Store in session temporarily
            request.session['totp_secret'] = setup_data['secret']
            request.session['totp_backup_codes'] = setup_data['backup_codes']
            
            context = {
                'qr_code': setup_data['qr_code'],
                'secret': setup_data['secret'],
                'backup_codes': setup_data['backup_codes'],
                'step': 'verify',
            }
            
            return render(request, 'accounts/setup_2fa.html', context)
        
        elif action == 'verify':
            # Verify TOTP code and enable 2FA
            token = request.POST.get('token', '').strip()
            secret = request.session.get('totp_secret')
            backup_codes = request.session.get('totp_backup_codes')
            
            if not secret or not backup_codes:
                messages.error(request, 'Setup session expired. Please start again.')
                return redirect('accounts:setup_2fa')
            
            # Verify the token
            if mfa_manager.totp_manager.verify_token(secret, token):
                # Enable 2FA
                mfa_manager.enable_totp(user, secret, backup_codes)
                
                # Log the action
                AuditLog.objects.create(
                    user=user,
                    user_email=user.email,
                    user_role=user.role,
                    action_type='create',
                    model_name='User2FA',
                    object_id=str(user.id),
                    object_repr=str(user.email),
                    description='TOTP 2FA enabled',
                    ip_address=get_client_ip(request),
                )
                
                # Clear session
                del request.session['totp_secret']
                del request.session['totp_backup_codes']
                
                messages.success(request, '🔐 Two-Factor Authentication enabled successfully!')
                return redirect('accounts:manage_2fa')
            else:
                messages.error(request, 'Invalid verification code. Please try again.')
                # Regenerate page with same secret
                qr_code = mfa_manager.totp_manager.generate_qr_code(secret, user.email)
                context = {
                    'qr_code': qr_code,
                    'secret': secret,
                    'backup_codes': backup_codes,
                    'step': 'verify',
                }
                return render(request, 'accounts/setup_2fa.html', context)
    
    # GET request - show initial setup page
    context = {
        'step': 'start',
    }
    return render(request, 'accounts/setup_2fa.html', context)


@login_required
def manage_2fa(request):
    """
    Manage 2FA settings.
    View backup codes, regenerate, or disable 2FA.
    """
    user = request.user
    
    if not user.totp_enabled:
        messages.info(request, '2FA is not enabled. Set it up to secure your account.')
        return redirect('accounts:setup_2fa')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'disable':
            # Verify password before disabling
            password = request.POST.get('password')
            if user.check_password(password):
                mfa_manager.disable_mfa(user, method='totp')
                
                # Log the action
                AuditLog.objects.create(
                    user=user,
                    user_email=user.email,
                    user_role=user.role,
                    action_type='delete',
                    model_name='User2FA',
                    object_id=str(user.id),
                    object_repr=str(user.email),
                    description='TOTP 2FA disabled',
                    ip_address=get_client_ip(request),
                )
                
                messages.success(request, '2FA has been disabled.')
                return redirect('accounts:profile')
            else:
                messages.error(request, 'Incorrect password. 2FA not disabled.')
        
        elif action == 'regenerate_codes':
            # Generate new backup codes
            new_codes = mfa_manager.totp_manager.generate_backup_codes()
            from django.core.cache import cache
            cache.set(f'mfa_backup_codes_{user.id}', new_codes, 86400 * 365)
            
            # Log the action
            AuditLog.objects.create(
                user=user,
                user_email=user.email,
                user_role=user.role,
                action_type='update',
                model_name='User2FA',
                object_id=str(user.id),
                object_repr=str(user.email),
                description='Backup codes regenerated',
                ip_address=get_client_ip(request),
            )
            
            messages.success(request, 'New backup codes generated. Save them securely!')
            context = {
                'backup_codes': new_codes,
                'show_codes': True,
            }
            return render(request, 'accounts/manage_2fa.html', context)
    
    # GET request - show management page
    backup_codes = mfa_manager.get_backup_codes(user)
    context = {
        'backup_codes': backup_codes,
        'backup_codes_count': len(backup_codes),
    }
    return render(request, 'accounts/manage_2fa.html', context)


@login_required
@require_http_methods(['POST'])
def verify_2fa_api(request):
    """
    API endpoint to verify 2FA code (AJAX).
    Used during login flow.
    """
    user = request.user
    token = request.POST.get('token', '').strip()
    
    if not user.totp_enabled:
        return JsonResponse({
            'success': False,
            'error': '2FA is not enabled for this account'
        })
    
    # Verify token
    is_valid = mfa_manager.verify_mfa_method(user, 'totp', token)
    
    if is_valid:
        # Log successful verification
        AuditLog.objects.create(
            user=user,
            user_email=user.email,
            user_role=user.role,
            action_type='login',
            model_name='User',
            object_id=str(user.id),
            object_repr=str(user.email),
            description='2FA verification successful',
            ip_address=get_client_ip(request),
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Verification successful'
        })
    else:
        # Log failed verification
        AuditLog.objects.create(
            user=user,
            user_email=user.email,
            user_role=user.role,
            action_type='login',
            model_name='User',
            object_id=str(user.id),
            object_repr=str(user.email),
            description='2FA verification failed',
            ip_address=get_client_ip(request),
        )
        
        return JsonResponse({
            'success': False,
            'error': 'Invalid verification code'
        })


def get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
