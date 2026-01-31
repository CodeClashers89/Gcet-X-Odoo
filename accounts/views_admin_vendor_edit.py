from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q, Sum
from .models import User, CustomerProfile, VendorProfile
from .forms import (
    CustomerRegistrationForm,
    VendorRegistrationForm,
    CustomerProfileForm,
    VendorProfileForm,
    AdminVendorEditForm,
)
from audit.models import AuditLog
from rental_erp.encryption import encryption_manager, mask_gstin, mask_bank_account, mask_upi
from rental_erp.security import rate_limit_view
from .decorators import role_required


def get_client_ip(request):
    """Utility to get real client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# ... (rest of the existing views remain the same) ...
# This is a placeholder - the actual file continues with all the existing view functions
