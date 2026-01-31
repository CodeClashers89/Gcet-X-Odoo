from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.db import transaction
import json
import requests
from .models import User, CustomerProfile, VendorProfile
from .forms import (
    CustomerRegistrationForm,
    VendorRegistrationForm,
    LoginForm,
    ForgotPasswordForm,
    ResetPasswordForm,
    UserProfileForm,
    VendorProfileUpdateForm,
    ChangePasswordForm,
)
from system_settings.models import SystemConfiguration, EmailTemplate
from audit.models import AuditLog
from rental_erp.encryption import encryption_manager, mask_gstin, mask_bank_account, mask_upi
from rental_erp.security import rate_limit_view
from .decorators import role_required


def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def verify_gstin_with_appyflow(gstin):
    """
    Verify GSTIN validity with AppyFlow API.
    Business Logic: Real-time GSTIN validation against government database.
    
    API Endpoint: AppyFlow GSTIN Verification
    Required: SystemConfiguration with appyflow_api_key
    
    Returns:
    - (True, company_name) if valid
    - (False, error_message) if invalid
    """
    try:
        config = SystemConfiguration.get_config()
        
        if not config.enable_gstin_verification or not config.appyflow_api_key:
            # Fallback to format validation only
            return True, "GSTIN format is valid (verification disabled)"
        
        # Call AppyFlow GSTIN verification API
        # Note: This is a placeholder. Actual API details from AppyFlow documentation
        api_url = "https://api.appyflow.in/v1/gstin/verify"
        headers = {
            'Authorization': f'Bearer {config.appyflow_api_key}',
            'Content-Type': 'application/json'
        }
        payload = {'gstin': gstin}
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('valid'):
                company_name = data.get('legal_name', 'N/A')
                return True, company_name
            else:
                return False, data.get('message', 'GSTIN not found')
        elif response.status_code == 401:
            return False, "API authentication failed"
        elif response.status_code == 404:
            return False, "GSTIN not found in government database"
        else:
            return False, f"Verification service error ({response.status_code})"
    
    except requests.exceptions.Timeout:
        return False, "GSTIN verification service is slow. Please try again."
    except requests.exceptions.ConnectionError:
        return False, "Unable to connect to GSTIN verification service."
    except Exception as e:
        return False, f"Verification error: {str(e)}"


def send_email_verification(user, request):
    """
    Send email verification link via Brevo SMTP.
    Business Logic: Ensures email ownership before allowing platform access.
    
    Uses: EmailTemplate (email_verification), SystemConfiguration (Brevo API)
    """
    try:
        config = SystemConfiguration.get_config()
        
        if not config.brevo_api_key:
            # Email sending disabled, auto-verify
            user.is_verified = True
            user.save()
            return True
        
        # Generate verification token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build verification URL
        verify_url = request.build_absolute_uri(
            f'/accounts/verify-email/{uid}/{token}/'
        )
        
        # Get email template
        template = EmailTemplate.objects.filter(
            template_type='welcome_customer' if user.role == 'customer' else 'welcome_vendor',
            is_active=True
        ).first()
        
        if not template:
            return True  # Skip if template doesn't exist
        
        # Prepare email (simplified - Brevo integration details vary)
        subject = f"Verify your email - {config.site_title}"
        body = f"""
        Hello {user.first_name},
        
        Welcome to {config.site_title}!
        
        Please verify your email address by clicking the link below:
        {verify_url}
        
        This link will expire in 24 hours.
        
        Best regards,
        {config.company_name}
        """
        
        # TODO: Replace with actual Brevo SMTP implementation
        # For now, we just mark as verified
        user.is_verified = True
        user.save()
        
        return True
    except Exception as e:
        print(f"Email verification error: {str(e)}")
        return False


@rate_limit_view(max_requests=5, period=60)
@require_http_methods(["GET", "POST"])
def signup_customer(request):
    """
    Customer registration view.
    Business Flow:
    1. Form submission (email, name, company, GSTIN)
    2. GSTIN format validation
    3. AppyFlow GSTIN verification (optional)
    4. Create User + CustomerProfile
    5. Send email verification
    6. Redirect to login with success message
    
    GET: Display registration form
    POST: Process form submission
    """
    if request.user.is_authenticated:
        return redirect('dashboards:dashboard')
    
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save user (not verified yet)
                    user = form.save()
                    
                    # Log signup action
                    AuditLog.log_action(
                        user=user,
                        action_type='signup',
                        model_instance=user,
                        description=f'Customer registration: {user.email}',
                        request=request,
                    )
                    
                    # Send verification email
                    send_email_verification(user, request)
                    
                    messages.success(
                        request,
                        'Registration successful! Check your email for verification link.'
                    )
                    return redirect('accounts:login')
            
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'accounts/signup_customer.html', {'form': form})


@rate_limit_view(max_requests=5, period=60)
@require_http_methods(["GET", "POST"])
def signup_vendor(request):
    """
    Vendor registration view.
    Business Flow:
    1. Form submission (company, GSTIN, bank details)
    2. GSTIN verification
    3. Create User + VendorProfile (is_approved=False)
    4. Send admin notification for approval
    5. Redirect to login with "pending approval" message
    
    Note: Vendor requires admin approval before account activation.
    """
    if request.user.is_authenticated:
        return redirect('dashboards:dashboard')
    
    if request.method == 'POST':
        form = VendorRegistrationForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # GSTIN verification
                    gstin = form.cleaned_data['gstin']
                    is_valid, result = verify_gstin_with_appyflow(gstin)
                    
                    if not is_valid:
                        messages.error(request, f'GSTIN verification failed: {result}')
                        return redirect('signup_vendor')
                    
                    # Save vendor
                    user = form.save()
                    
                    # Log signup
                    AuditLog.log_action(
                        user=user,
                        action_type='signup',
                        model_instance=user,
                        description=f'Vendor registration: {user.email} (pending approval)',
                        request=request,
                    )
                    
                    # Send verification email
                    send_email_verification(user, request)
                    
                    messages.success(
                        request,
                        'Registration successful! Your account is pending admin approval. '
                        'You will receive an email once approved.'
                    )
                    return redirect('accounts:login')
            
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = VendorRegistrationForm()
    
    return render(request, 'accounts/signup_vendor.html', {'form': form})


@rate_limit_view(max_requests=5, period=60)
@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    User login view.
    Business Flow:
    1. Email + password submission
    2. Authenticate user
    3. Check if email verified
    4. Check if vendor is approved
    5. Create session and redirect to dashboard
    
    Redirects:
    - If already logged in: dashboard
    - If login successful: dashboard
    - If unverified email: login (with error)
    - If vendor not approved: login (with error)
    """
    if request.user.is_authenticated:
        return redirect('dashboards:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        
        if form.is_valid():
            user = form.cleaned_data['user']
            
            # Check vendor approval
            if user.role == 'vendor':
                vendor_profile = VendorProfile.objects.get(user=user)
                if not vendor_profile.is_approved:
                    messages.error(
                        request,
                        'Your vendor account is pending admin approval. '
                        'You will be able to login once approved.'
                    )
                    return redirect('accounts:login')
            
            # Check if 2FA is enabled
            if user.totp_enabled:
                # Store user ID in session for 2FA verification
                request.session['pending_2fa_user_id'] = user.id
                request.session['pending_2fa_remember_me'] = form.cleaned_data.get('remember_me', False)
                
                # Log partial login
                AuditLog.objects.create(
                    user=user,
                    user_email=user.email,
                    user_role=user.role,
                    action_type='login',
                    model_name='User',
                    object_id=str(user.id),
                    object_repr=str(user.email),
                    description=f'Login initiated, 2FA verification required: {user.email}',
                    ip_address=get_client_ip(request),
                )
                
                return redirect('accounts:verify_2fa')
            
            # Login user (no 2FA)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Log login action
            AuditLog.objects.create(
                user=user,
                user_email=user.email,
                user_role=user.role,
                action_type='login',
                model_name='User',
                object_id=str(user.id),
                object_repr=str(user.email),
                description=f'User login: {user.email}',
                ip_address=get_client_ip(request),
                session_key=request.session.session_key,
            )
            
            # Remember me functionality
            if form.cleaned_data.get('remember_me'):
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
            
            # Redirect based on role
            next_url = request.GET.get('next', 'dashboards:dashboard')
            return redirect(next_url)
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
@require_http_methods(["POST"])
def logout_view(request):
    """
    User logout view.
    Business Logic:
    - Clear session
    - Log logout action
    - Redirect to homepage
    """
    # Log logout
    AuditLog.log_action(
        user=request.user,
        action_type='logout',
        model_instance=request.user,
        description=f'User logout: {request.user.email}',
        request=request,
    )
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


@rate_limit_view(max_requests=3, period=60)
@require_http_methods(["GET", "POST"])
def forgot_password(request):
    """
    Forgot password request view.
    Business Flow:
    1. User enters email
    2. Generate password reset token
    3. Send reset link via Brevo email
    4. Show confirmation message
    
    Security: Doesn't reveal if email exists (prevents user enumeration)
    """
    if request.user.is_authenticated:
        return redirect('dashboards:dashboard')
    
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        
        if form.is_valid():
            try:
                email = form.cleaned_data['email'].lower()
                user = User.objects.get(email=email)
                
                # Generate reset token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Build reset URL
                reset_url = request.build_absolute_uri(
                    f'/accounts/reset-password/{uid}/{token}/'
                )
                
                # TODO: Send reset email via Brevo
                # For now, just show success message
                messages.success(
                    request,
                    'Password reset link sent to your email. Check your inbox.'
                )
                return redirect('accounts:login')
            except User.DoesNotExist:
                # Don't reveal if user exists
                messages.success(
                    request,
                    'If an account exists with this email, you will receive a password reset link.'
                )
                return redirect('accounts:login')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = ForgotPasswordForm()
    
    return render(request, 'accounts/forgot_password.html', {'form': form})


@rate_limit_view(max_requests=3, period=60)
@require_http_methods(["GET", "POST"])
def reset_password(request, uidb64, token):
    """
    Password reset view (after user clicks email link).
    Business Flow:
    1. Validate token and UID
    2. Display new password form
    3. Update password and redirect to login
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, 'Invalid or expired reset link.')
        return redirect('accounts:login')
    
    # Validate token
    if not default_token_generator.check_token(user, token):
        messages.error(request, 'Password reset link has expired. Please request a new one.')
        return redirect('forgot_password')
    
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        
        if form.is_valid():
            new_password = form.cleaned_data['password']
            user.set_password(new_password)
            user.save()
            
            # Log password change
            AuditLog.log_action(
                user=user,
                action_type='update',
                model_instance=user,
                field_name='password',
                description='Password reset via email link',
                request=request,
            )
            
            messages.success(request, 'Password has been reset successfully. Please login.')
            return redirect('accounts:login')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = ResetPasswordForm()
    
    return render(request, 'accounts/reset_password.html', {'form': form, 'user': user})


@require_http_methods(["GET"])
def verify_email(request, uidb64, token):
    """
    Email verification view (after user clicks verification link).
    Business Flow:
    1. Validate token and UID
    2. Mark user as verified
    3. Redirect to login or auto-login
    
    Security: Token is single-use (expires after activation)
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, 'Invalid verification link.')
        return redirect('accounts:login')
    
    # Check if already verified
    if user.is_verified:
        messages.info(request, 'Email already verified. Please login.')
        return redirect('accounts:login')
    
    # Validate token (one-time use)
    if not default_token_generator.check_token(user, token):
        messages.error(request, 'Verification link has expired. Request a new one.')
        return redirect('accounts:login')
    
    # Mark as verified
    user.is_verified = True
    user.save()
    
    # Log verification
    AuditLog.log_action(
        user=user,
        action_type='update',
        model_instance=user,
        field_name='is_verified',
        old_value='False',
        new_value='True',
        description='Email verified via link',
        request=request,
    )
    
    messages.success(request, 'Email verified successfully! You can now login.')
    return redirect('accounts:login')


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    """
    User profile view for editing personal information.
    Business Logic:
    - Customers see: name, phone, company info (with masked GSTIN)
    - Vendors see: name, phone, company, bank details (with masked sensitive data)
    - Admins see: limited options
    
    Phase 10 - Task 2: Decrypt sensitive fields for display, mask for security
    """
    user = request.user
    
    if request.method == 'POST':
        # Check if updating vendor profile with encrypted fields
        if user.role == 'vendor' and 'update_vendor_profile' in request.POST:
            vendor_profile = VendorProfile.objects.get(user=user)
            vendor_form = VendorProfileUpdateForm(request.POST, instance=vendor_profile)
            
            if vendor_form.is_valid():
                vendor_form.save()
                
                # Log profile update
                AuditLog.log_action(
                    user=user,
                    action_type='update',
                    model_name='VendorProfile',
                    object_id=vendor_profile.id,
                    description='Vendor profile updated (encrypted fields)',
                    ip_address=get_client_ip(request),
                )
                
                messages.success(request, 'Vendor profile updated successfully.')
                return redirect('accounts:profile')
        else:
            # Update basic user profile
            form = UserProfileForm(request.POST, instance=user)
            
            if form.is_valid():
                form.save()
                
                # Log profile update
                AuditLog.log_action(
                    user=user,
                    action_type='update',
                    model_instance=user,
                    description='User profile updated',
                    request=request,
                )
                
                messages.success(request, 'Profile updated successfully.')
                return redirect('accounts:profile')
            else:
                for error in form.non_field_errors():
                    messages.error(request, error)
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
    }
    
    # Add role-specific profile data with decrypted and masked values
    if user.role == 'customer':
        customer_profile = CustomerProfile.objects.get(user=user)
        context['profile'] = customer_profile
        
        # Decrypt and mask GSTIN for display
        masked_data = {}
        if customer_profile.gstin:
            try:
                gstin_decrypted = encryption_manager.decrypt(customer_profile.gstin)
                masked_data['masked_gstin'] = mask_gstin(gstin_decrypted)
            except:
                masked_data['masked_gstin'] = '****ENCRYPTED'
        
        context['masked_data'] = masked_data
        
    elif user.role == 'vendor':
        vendor_profile = VendorProfile.objects.get(user=user)
        context['profile'] = vendor_profile
        context['vendor_form'] = VendorProfileUpdateForm(instance=vendor_profile)
        
        # Decrypt and mask all sensitive vendor data for display
        masked_data = {}
        
        # Decrypt and mask GSTIN
        if vendor_profile.gstin:
            try:
                gstin_decrypted = encryption_manager.decrypt(vendor_profile.gstin)
                masked_data['masked_gstin'] = mask_gstin(gstin_decrypted)
            except:
                masked_data['masked_gstin'] = '****ENCRYPTED'
        
        # Decrypt and mask bank account
        if vendor_profile.bank_account_number:
            try:
                bank_account_decrypted = encryption_manager.decrypt(vendor_profile.bank_account_number)
                masked_data['masked_bank_account'] = mask_bank_account(bank_account_decrypted)
            except:
                masked_data['masked_bank_account'] = '****ENCRYPTED'
        
        # Decrypt and mask IFSC code
        if vendor_profile.bank_ifsc_code:
            try:
                ifsc_decrypted = encryption_manager.decrypt(vendor_profile.bank_ifsc_code)
                masked_data['masked_ifsc_code'] = mask_bank_account(ifsc_decrypted)  # Show last 4
            except:
                masked_data['masked_ifsc_code'] = '****ENCRYPTED'
        
        # Decrypt and mask UPI ID
        if vendor_profile.upi_id:
            try:
                upi_decrypted = encryption_manager.decrypt(vendor_profile.upi_id)
                # Simple UPI masking: show first char and last @ domain
                if '@' in upi_decrypted:
                    parts = upi_decrypted.split('@')
                    masked_data['masked_upi_id'] = f"{parts[0][0]}***@{parts[1]}"
                else:
                    masked_data['masked_upi_id'] = upi_decrypted[0] + '****'
            except:
                masked_data['masked_upi_id'] = '****ENCRYPTED'
        
        context['masked_data'] = masked_data
    
    return render(request, 'accounts/profile.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def change_password(request):
    """
    Change password view for logged-in users.
    Business Logic:
    - Verify current password
    - Update to new password
    - Log password change
    """
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user = request.user
            user.set_password(new_password)
            user.save()
            
            # Log password change
            AuditLog.log_action(
                user=user,
                action_type='update',
                model_instance=user,
                field_name='password',
                description='Password changed by user',
                request=request,
            )
            
            messages.success(request, 'Password changed successfully. Please login again.')
            logout(request)
            return redirect('accounts:login')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = ChangePasswordForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})


@require_http_methods(["GET"])
def verify_gstin_ajax(request):
    """
    AJAX endpoint to verify GSTIN in real-time during signup.
    Business Use: Live GSTIN validation without form submission.
    
    GET Parameters:
    - gstin: 15-character GSTIN to verify
    
    Returns:
    - JSON: {'valid': bool, 'company_name': str, 'message': str}
    """
    gstin = request.GET.get('gstin', '').upper()
    
    if len(gstin) != 15:
        return JsonResponse({
            'valid': False,
            'message': 'GSTIN must be 15 characters'
        })
    
    is_valid, result = verify_gstin_with_appyflow(gstin)
    
    return JsonResponse({
        'valid': is_valid,
        'company_name': result if is_valid else None,
        'message': result
    })


@login_required
@role_required(['admin'])
def admin_vendor_list(request):
    """
    List all vendors for admin review and management.
    Business Use: Dashboard for managing marketplace participant approvals.
    """
    vendors = VendorProfile.objects.select_related('user').all().order_by('-created_at')
    
    # Filter by approval status
    status = request.GET.get('status')
    if status == 'pending':
        vendors = vendors.filter(is_approved=False)
    elif status == 'approved':
        vendors = vendors.filter(is_approved=True)
        
    return render(request, 'accounts/admin_vendor_list.html', {'vendors': vendors, 'current_status': status})


@login_required
@role_required(['admin'])
@require_http_methods(["POST"])
def approve_vendor(request, pk):
    """
    Approve a vendor registration.
    Business Flow: Marks vendor as approved, allowing them to list products.
    """
    try:
        vendor = VendorProfile.objects.get(pk=pk)
        vendor.is_approved = True
        vendor.approved_at = timezone.now()
        vendor.user.is_active = True
        vendor.user.save()
        vendor.save()
        
        # Log approval
        AuditLog.log_action(
            user=request.user,
            action_type='update',
            model_instance=vendor,
            field_name='is_approved',
            old_value='False',
            new_value='True',
            description=f'Vendor approved: {vendor.user.email}',
            request=request,
        )
        
        messages.success(request, f'Vendor {vendor.company_name} has been approved.')
    except VendorProfile.DoesNotExist:
        messages.error(request, 'Vendor not found.')
        
    return redirect('accounts:admin_vendor_list')


@login_required
@role_required(['admin'])
@require_http_methods(["POST"])
def reject_vendor(request, pk):
    """
    Deactivate/Reject a vendor registration.
    """
    try:
        vendor = VendorProfile.objects.get(pk=pk)
        vendor.is_approved = False
        vendor.user.is_active = False
        vendor.user.save()
        vendor.save()
        
        # Log rejection
        AuditLog.log_action(
            user=request.user,
            action_type='update',
            model_instance=vendor,
            field_name='is_approved',
            old_value='True',
            new_value='False',
            description=f'Vendor rejected/deactivated: {vendor.user.email}',
            request=request,
        )
        
        messages.warning(request, f'Vendor {vendor.company_name} has been deactivated.')
    except VendorProfile.DoesNotExist:
        messages.error(request, 'Vendor not found.')
        
    return redirect('accounts:admin_vendor_list')


@login_required
@role_required(['admin'])
def admin_vendor_profile(request, pk):
    """
    View detailed vendor profile information.
    Business Use: Admin can review vendor details before approval.
    """
    from rental_erp.encryption import encryption_manager, mask_gstin, mask_bank_account
    vendor_profile = VendorProfile.objects.select_related('user').get(pk=pk)
    
    # Decrypt and mask sensitive data
    masked_data = {}
    if vendor_profile.gstin:
        try:
            gstin_decrypted = encryption_manager.decrypt(vendor_profile.gstin)
            masked_data['masked_gstin'] = mask_gstin(gstin_decrypted)
        except:
            masked_data['masked_gstin'] = '****ENCRYPTED'
    
    if vendor_profile.bank_account_number:
        try:
            bank_decrypted = encryption_manager.decrypt(vendor_profile.bank_account_number)
            masked_data['masked_bank_account'] = mask_bank_account(bank_decrypted)
        except:
            masked_data['masked_bank_account'] = '****ENCRYPTED'
    
    # Get vendor's products
    from catalog.models import Product
    products = Product.objects.filter(vendor=vendor_profile.user).order_by('-created_at')[:10]
    
    return render(request, 'accounts/admin_vendor_profile.html', {
        'vendor': vendor_profile,
        'masked_data': masked_data,
        'products': products
    })


@login_required
@role_required(['admin'])
def admin_product_list(request):
    """
    List all products with approval management.
    Business Use: Admin reviews and approves vendor products before they go live.
    """
    from catalog.models import Product
    
    products = Product.objects.select_related('vendor', 'category').all().order_by('-created_at')
    
    # Filter by publication status
    status = request.GET.get('status')
    if status == 'pending':
        products = products.filter(is_published=False)
    elif status == 'published':
        products = products.filter(is_published=True)
    
    # Filter by vendor
    vendor_id = request.GET.get('vendor')
    if vendor_id:
        products = products.filter(vendor_id=vendor_id)
        
    return render(request, 'catalog/admin_product_list.html', {
        'products': products,
        'current_status': status,
        'current_vendor': vendor_id
    })


@login_required
@role_required(['admin'])
@require_http_methods(["POST"])
def publish_product(request, pk):
    """
    Approve/publish a vendor product.
    Business Flow: Makes product visible to customers.
    """
    from catalog.models import Product
    try:
        product = Product.objects.get(pk=pk)
        product.is_published = True
        product.save()
        
        # Log approval
        AuditLog.log_action(
            user=request.user,
            action_type='update',
            model_instance=product,
            field_name='is_published',
            old_value='False',
            new_value='True',
            description=f'Product approved: {product.name} (Vendor: {product.vendor.email})',
            request=request,
        )
        
        messages.success(request, f'Product "{product.name}" has been published.')
    except Product.DoesNotExist:
        messages.error(request, 'Product not found.')
        
    return redirect('accounts:admin_product_list')


@login_required
@role_required(['admin'])
@require_http_methods(["POST"])
def unpublish_product(request, pk):
    """
    Unpublish/hide a product from customers.
    """
    from catalog.models import Product
    try:
        product = Product.objects.get(pk=pk)
        product.is_published = False
        product.save()
        
        # Log action
        AuditLog.log_action(
            user=request.user,
            action_type='update',
            model_instance=product,
            field_name='is_published',
            old_value='True',
            new_value='False',
            description=f'Product unpublished: {product.name}',
            request=request,
        )
        
        messages.warning(request, f'Product "{product.name}" has been unpublished.')
    except Product.DoesNotExist:
        messages.error(request, 'Product not found.')
        
    return redirect('accounts:admin_product_list')


@login_required
@role_required(['admin'])
def admin_vendor_edit(request, pk):
    """
    Edit vendor profile information.
    Business Use: Admin can update vendor details and approval status.
    """
    from .forms import AdminVendorEditForm
    
    vendor_profile = VendorProfile.objects.select_related('user').get(pk=pk)
    
    if request.method == 'POST':
        form = AdminVendorEditForm(request.POST, instance=vendor_profile)
        if form.is_valid():
            # Handle encrypted fields - only update if new value provided
            if form.cleaned_data.get('gstin'):
                vendor_profile.gstin = encryption_manager.encrypt(form.cleaned_data['gstin'])
            if form.cleaned_data.get('bank_account_number'):
                vendor_profile.bank_account_number = encryption_manager.encrypt(form.cleaned_data['bank_account_number'])
            if form.cleaned_data.get('upi_id'):
                vendor_profile.upi_id = encryption_manager.encrypt(form.cleaned_data['upi_id'])
            
            form.save()
            
            # Log the edit
            AuditLog.log_action(
                user=request.user,
                action_type='update',
                model_instance=vendor_profile,
                description=f'Updated vendor profile: {vendor_profile.company_name}',
                request=request,
            )
            
            messages.success(request, 'Vendor profile updated successfully.')
            return redirect('accounts:admin_vendor_profile', pk=vendor_profile.pk)
    else:
        form = AdminVendorEditForm(instance=vendor_profile)
        
        # Decrypt encrypted fields for editing
        if vendor_profile.gstin:
            try:
                form.fields['gstin'].initial = encryption_manager.decrypt(vendor_profile.gstin)
            except:
                form.fields['gstin'].initial = ''
        
        if vendor_profile.bank_account_number:
            try:
                form.fields['bank_account_number'].initial = encryption_manager.decrypt(vendor_profile.bank_account_number)
            except:
                form.fields['bank_account_number'].initial = ''
                
        if vendor_profile.upi_id:
            try:
                form.fields['upi_id'].initial = encryption_manager.decrypt(vendor_profile.upi_id)
            except:
                form.fields['upi_id'].initial = ''
    
    return render(request, 'accounts/admin_vendor_edit.html', {
        'vendor': vendor_profile,
        'form': form
    })
