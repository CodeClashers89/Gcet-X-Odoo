"""
GDPR Compliance Views
Support for data subject rights: access, rectification, erasure, portability.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from django.core import serializers
import json

from .models import User, CustomerProfile, VendorProfile, UserConsent, DataDeletionRequest
from rentals.models import Quotation, RentalOrder
from billing.models import Invoice, Payment
from audit.models import AuditLog


@login_required
@require_http_methods(["GET"])
def my_data(request):
    """
    GDPR Article 15 - Right of Access.
    Display all personal data the system holds about the user.
    """
    user = request.user
    
    # Gather all user data
    user_data = {
        'basic_info': {
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone,
            'role': user.role,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
        },
        'profile': None,
        'quotations_count': 0,
        'orders_count': 0,
        'invoices_count': 0,
        'payments_count': 0,
        'audit_logs_count': 0,
        'consents': [],
    }
    
    # Profile data
    if user.role == 'customer':
        try:
            profile = CustomerProfile.objects.get(user=user)
            user_data['profile'] = {
                'company_name': profile.company_name,
                'gstin': '****ENCRYPTED',  # Don't show sensitive data
                'billing_address': profile.billing_address,
                'city': profile.city,
                'state': profile.state,
            }
        except CustomerProfile.DoesNotExist:
            pass
    elif user.role == 'vendor':
        try:
            profile = VendorProfile.objects.get(user=user)
            user_data['profile'] = {
                'company_name': profile.company_name,
                'is_approved': profile.is_approved,
                'total_products': profile.total_products,
                'total_rentals': profile.total_rentals,
            }
        except VendorProfile.DoesNotExist:
            pass
    
    # Activity counts
    if user.role == 'customer':
        user_data['quotations_count'] = Quotation.objects.filter(customer=user).count()
        user_data['orders_count'] = RentalOrder.objects.filter(customer=user).count()
        user_data['invoices_count'] = Invoice.objects.filter(customer=user).count()
        user_data['payments_count'] = Payment.objects.filter(customer=user).count()
    elif user.role == 'vendor':
        user_data['quotations_count'] = Quotation.objects.filter(vendor=user).count()
        user_data['orders_count'] = RentalOrder.objects.filter(vendor=user).count()
        user_data['invoices_count'] = Invoice.objects.filter(vendor=user).count()
    
    # Audit logs
    user_data['audit_logs_count'] = AuditLog.objects.filter(user=user).count()
    
    # Consents
    consents = UserConsent.objects.filter(user=user, granted=True)
    user_data['consents'] = [
        {
            'type': consent.consent_type,
            'granted_at': consent.granted_at,
            'policy_version': consent.policy_version,
        }
        for consent in consents
    ]
    
    return render(request, 'accounts/my_data.html', {'user_data': user_data})


@login_required
@require_http_methods(["GET"])
def export_my_data(request):
    """
    GDPR Article 20 - Right to Data Portability.
    Export user's personal data in JSON format.
    """
    user = request.user
    
    # Gather all data
    export_data = {
        'export_date': timezone.now().isoformat(),
        'user': {
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone,
            'role': user.role,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        },
        'profile': {},
        'quotations': [],
        'orders': [],
        'invoices': [],
        'payments': [],
        'audit_logs': [],
        'consents': [],
    }
    
    # Profile
    if user.role == 'customer':
        try:
            profile = CustomerProfile.objects.get(user=user)
            export_data['profile'] = {
                'company_name': profile.company_name,
                'billing_address': profile.billing_address,
                'city': profile.city,
                'state': profile.state,
                'pincode': profile.pincode,
                'total_orders': profile.total_orders,
                'total_spent': str(profile.total_spent),
            }
        except CustomerProfile.DoesNotExist:
            pass
    elif user.role == 'vendor':
        try:
            profile = VendorProfile.objects.get(user=user)
            export_data['profile'] = {
                'company_name': profile.company_name,
                'business_address': profile.business_address,
                'is_approved': profile.is_approved,
                'total_products': profile.total_products,
                'total_rentals': profile.total_rentals,
                'total_revenue': str(profile.total_revenue),
            }
        except VendorProfile.DoesNotExist:
            pass
    
    # Quotations
    if user.role == 'customer':
        quotations = Quotation.objects.filter(customer=user)
    else:
        quotations = Quotation.objects.filter(vendor=user)
    
    for quot in quotations:
        export_data['quotations'].append({
            'quotation_number': quot.quotation_number,
            'status': quot.status,
            'total_amount': str(quot.total_amount),
            'created_at': quot.created_at.isoformat(),
        })
    
    # Orders
    if user.role == 'customer':
        orders = RentalOrder.objects.filter(customer=user)
    else:
        orders = RentalOrder.objects.filter(vendor=user)
    
    for order in orders:
        export_data['orders'].append({
            'order_number': order.order_number,
            'status': order.status,
            'total_amount': str(order.total_amount),
            'created_at': order.created_at.isoformat(),
        })
    
    # Consents
    consents = UserConsent.objects.filter(user=user)
    for consent in consents:
        export_data['consents'].append({
            'consent_type': consent.consent_type,
            'granted': consent.granted,
            'granted_at': consent.granted_at.isoformat(),
            'policy_version': consent.policy_version,
            'withdrawn_at': consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
        })
    
    # Log data export
    AuditLog.log_action(
        user=user,
        action_type='export',
        model_name='UserData',
        description='GDPR data export',
        ip_address=get_client_ip(request),
    )
    
    # Return as JSON download
    response = HttpResponse(
        json.dumps(export_data, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="my_data_{user.id}_{timezone.now().strftime("%Y%m%d")}.json"'
    
    return response


@login_required
@require_http_methods(["GET", "POST"])
def request_data_deletion(request):
    """
    GDPR Article 17 - Right to Erasure ('Right to be Forgotten').
    Submit a request to delete all personal data.
    """
    user = request.user
    
    # Check if there's already a pending request
    existing_request = DataDeletionRequest.objects.filter(
        user=user,
        status__in=['pending', 'in_progress']
    ).first()
    
    if request.method == 'POST':
        if existing_request:
            messages.warning(request, 'You already have a pending deletion request.')
            return redirect('accounts:request_data_deletion')
        
        reason = request.POST.get('reason', '')
        
        # Create deletion request
        deletion_request = DataDeletionRequest.objects.create(
            user=user,
            reason=reason,
            status='pending',
            ip_address=get_client_ip(request),
        )
        
        # Log the request
        AuditLog.log_action(
            user=user,
            action_type='delete',
            model_name='DataDeletionRequest',
            object_id=deletion_request.id,
            description=f'GDPR deletion request submitted',
            ip_address=get_client_ip(request),
        )
        
        messages.success(
            request,
            'Your data deletion request has been submitted. '
            'An administrator will review it within 30 days as required by GDPR.'
        )
        return redirect('accounts:my_data')
    
    return render(request, 'accounts/request_data_deletion.html', {
        'existing_request': existing_request,
    })


@login_required
@require_http_methods(["POST"])
def withdraw_consent(request, consent_id):
    """
    GDPR Article 7(3) - Right to withdraw consent.
    Allow users to withdraw previously given consent.
    """
    try:
        consent = UserConsent.objects.get(id=consent_id, user=request.user)
        consent.withdraw()
        
        # Log withdrawal
        AuditLog.log_action(
            user=request.user,
            action_type='update',
            model_name='UserConsent',
            object_id=consent.id,
            description=f'Consent withdrawn: {consent.consent_type}',
            ip_address=get_client_ip(request),
        )
        
        messages.success(request, f'Consent for {consent.get_consent_type_display()} has been withdrawn.')
    except UserConsent.DoesNotExist:
        messages.error(request, 'Consent not found.')
    
    return redirect('accounts:my_data')


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
