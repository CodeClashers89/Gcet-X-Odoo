"""
API Key Management Views
Create, list, and revoke API keys for users.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta

from .models import APIKey
from rental_erp.api_security import APIKeyManager
from audit.models import AuditLog


@login_required
@require_http_methods(["GET", "POST"])
def api_keys(request):
    """List and create API keys for the logged-in user."""
    user = request.user

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        expires_in_days = request.POST.get('expires_in_days', '').strip()

        if not name:
            messages.error(request, 'API key name is required.')
            return redirect('accounts:api_keys')

        # Generate API key
        raw_key = APIKeyManager.generate_api_key()
        key_hash = APIKeyManager.hash_api_key(raw_key)

        expires_at = None
        if expires_in_days.isdigit():
            expires_at = timezone.now() + timedelta(days=int(expires_in_days))

        api_key = APIKey.objects.create(
            user=user,
            name=name,
            key_hash=key_hash,
            prefix=raw_key[:3],
            last_four=raw_key[-4:],
            expires_at=expires_at,
        )

        AuditLog.objects.create(
            user=user,
            user_email=user.email,
            user_role=user.role,
            action_type='create',
            model_name='APIKey',
            object_id=str(api_key.id),
            object_repr=f"{api_key.prefix}****{api_key.last_four}",
            description=f"API key created: {name}",
            ip_address=get_client_ip(request),
        )

        # Store raw key in session for one-time display
        request.session['created_api_key'] = raw_key
        messages.success(request, 'API key created. Copy it now; it will not be shown again.')
        return redirect('accounts:api_keys')

    created_key = request.session.pop('created_api_key', None)
    keys = APIKey.objects.filter(user=user).order_by('-created_at')

    return render(request, 'accounts/api_keys.html', {
        'api_keys': keys,
        'created_key': created_key,
    })


@login_required
@require_http_methods(["POST"])
def revoke_api_key(request, key_id):
    """Revoke an API key."""
    api_key = get_object_or_404(APIKey, id=key_id, user=request.user)

    if api_key.revoked_at:
        messages.info(request, 'API key is already revoked.')
        return redirect('accounts:api_keys')

    api_key.revoke()

    AuditLog.objects.create(
        user=request.user,
        user_email=request.user.email,
        user_role=request.user.role,
        action_type='delete',
        model_name='APIKey',
        object_id=str(api_key.id),
        object_repr=f"{api_key.prefix}****{api_key.last_four}",
        description=f"API key revoked: {api_key.name}",
        ip_address=get_client_ip(request),
    )

    messages.success(request, 'API key revoked successfully.')
    return redirect('accounts:api_keys')


def get_client_ip(request):
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
