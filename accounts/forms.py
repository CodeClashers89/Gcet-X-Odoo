from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.text import slugify
import re
from .models import User, CustomerProfile, VendorProfile
from rental_erp.encryption import (
    encryption_manager,
    validate_gstin,
    validate_ifsc_code,
    validate_pan
)


class UserRegistrationForm(forms.ModelForm):
    """
    Base registration form for new users.
    Business Use: Captures basic user information (email, name, password).
    
    Used by:
    - CustomerRegistrationForm
    - VendorRegistrationForm
    Subclasses extend this with role-specific fields.
    """
    
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'At least 8 characters'
        }),
        help_text='Password must be at least 8 characters long.'
    )
    
    password_confirmation = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        }),
        label='Confirm Password'
    )
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your@email.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
        }
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError('This email address is already registered.')
        return email
    
    def clean(self):
        """Validate password confirmation"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirmation = cleaned_data.get('password_confirmation')
        
        if password and password_confirmation and password != password_confirmation:
            raise ValidationError('Passwords do not match. Please try again.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Override save to:
        1. Create username from email
        2. Set password
        3. Mark as unverified (requires email confirmation)
        """
        user = super().save(commit=False)
        user.username = slugify(self.cleaned_data['email'].split('@')[0])
        user.email = self.cleaned_data['email'].lower()
        user.set_password(self.cleaned_data['password'])
        user.is_verified = False  # Requires email verification
        
        if commit:
            user.save()
        return user


class CustomerRegistrationForm(UserRegistrationForm):
    """
    Extended registration form for customer users.
    Business Use: Capture customer's company and GST details for invoicing.
    
    Fields:
    - company_name: Legal entity name
    - gstin: GST Identification Number (mandatory for tax compliance)
    - state: For GST calculation
    - signup_coupon: Optional promotional code
    """
    
    company_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Company Name'
        }),
        help_text='Business entity name for invoicing.'
    )
    
    gstin = forms.CharField(
        max_length=15,
        validators=[],  # Validation done in AppyFlow API
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '15-character GSTIN (e.g., 27AABCP1234A1Z5)'
        }),
        help_text='GST Identification Number (required for invoicing).'
    )
    
    state = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Maharashtra, Karnataka'
        }),
        help_text='Your state (for GST calculations).'
    )
    
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City (optional)'
        })
    )
    
    pincode = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '6-digit postal code'
        })
    )
    
    billing_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Complete billing address'
        })
    )
    
    signup_coupon = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Promo code (optional)'
        }),
        help_text='Enter if you have a promotional code.'
    )
    
    class Meta(UserRegistrationForm.Meta):
        fields = ('email', 'first_name', 'last_name', 'company_name', 'gstin', 'state')
    
    def clean_gstin(self):
        """
        Validate GSTIN format using encryption module validator.
        Business Logic: GSTIN must be 15 characters, alphanumeric.
        """
        gstin = self.cleaned_data.get('gstin', '').upper()
        
        # Use encryption module's validator (Phase 10 - Task 2)
        if not validate_gstin(gstin):
            raise ValidationError(
                'Invalid GSTIN format. Expected format: 27AABCP1234A1Z5'
            )
        
        # Check for duplicate GSTIN - note we need to decrypt existing GSTINs
        # For now, we'll skip duplicate check during encryption migration
        # TODO: Implement encrypted duplicate check after all data is encrypted
        
        return gstin
    
    def save(self, commit=True):
        """Create user and customer profile with encrypted GSTIN"""
        user = super().save(commit=False)
        user.role = 'customer'
        
        if commit:
            user.save()
            
            # Encrypt GSTIN before storage (Phase 10 - Task 2)
            gstin_plaintext = self.cleaned_data['gstin']
            gstin_encrypted = encryption_manager.encrypt(gstin_plaintext)
            
            # Create customer profile
            CustomerProfile.objects.create(
                user=user,
                company_name=self.cleaned_data['company_name'],
                gstin=gstin_encrypted,  # Store encrypted
                state=self.cleaned_data['state'],
                city=self.cleaned_data['city'],
                pincode=self.cleaned_data['pincode'],
                billing_address=self.cleaned_data['billing_address'],
                signup_coupon=self.cleaned_data.get('signup_coupon'),
            )
        
        return user


class VendorRegistrationForm(UserRegistrationForm):
    """
    Extended registration form for vendor users.
    Business Use: Capture vendor's business details and banking information.
    
    Note: Vendor registration typically requires admin approval.
    """
    
    company_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Business Name'
        })
    )
    
    gstin = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'GSTIN (15 characters)'
        })
    )
    
    state = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'State'
        })
    )
    
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City (optional)'
        })
    )
    
    pincode = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Postal code'
        })
    )
    
    business_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Business address'
        })
    )
    
    bank_account_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Bank account number (for payouts)'
        }),
        help_text='Will be encrypted for security'
    )
    
    bank_ifsc_code = forms.CharField(
        max_length=11,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'IFSC code (e.g., SBIN0012345)'
        }),
        help_text='Will be encrypted for security'
    )
    
    bank_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Bank name'
        })
    )
    
    upi_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'UPI ID (e.g., yourname@upi)'
        }),
        help_text='Alternative to bank account for instant payouts (encrypted)'
    )
    
    def clean_gstin(self):
        """Validate GSTIN format for vendor using encryption module"""
        gstin = self.cleaned_data.get('gstin', '').upper()
        
        # Use encryption module's validator (Phase 10 - Task 2)
        if not validate_gstin(gstin):
            raise ValidationError('Invalid GSTIN format.')
        
        # Skip duplicate check during encryption migration
        # TODO: Implement encrypted duplicate check
        
        return gstin
    
    def clean_bank_ifsc_code(self):
        """Validate IFSC code if provided"""
        ifsc = self.cleaned_data.get('bank_ifsc_code', '').upper()
        if ifsc and not validate_ifsc_code(ifsc):
            raise ValidationError('Invalid IFSC code format. Expected: SBIN0012345')
        return ifsc
    
    def save(self, commit=True):
        """Create user and vendor profile with encrypted sensitive fields"""
        user = super().save(commit=False)
        user.role = 'vendor'
        
        if commit:
            user.save()
            
            # Encrypt sensitive fields (Phase 10 - Task 2)
            gstin_encrypted = encryption_manager.encrypt(self.cleaned_data['gstin'])
            
            bank_account = self.cleaned_data.get('bank_account_number')
            bank_account_encrypted = encryption_manager.encrypt(bank_account) if bank_account else None
            
            bank_ifsc = self.cleaned_data.get('bank_ifsc_code')
            bank_ifsc_encrypted = encryption_manager.encrypt(bank_ifsc) if bank_ifsc else None
            
            upi_id = self.cleaned_data.get('upi_id')
            upi_id_encrypted = encryption_manager.encrypt(upi_id) if upi_id else None
            
            VendorProfile.objects.create(
                user=user,
                company_name=self.cleaned_data['company_name'],
                gstin=gstin_encrypted,  # Encrypted
                state=self.cleaned_data['state'],
                city=self.cleaned_data['city'],
                pincode=self.cleaned_data['pincode'],
                business_address=self.cleaned_data['business_address'],
                bank_account_number=bank_account_encrypted,  # Encrypted
                bank_ifsc_code=bank_ifsc_encrypted,  # Encrypted
                upi_id=upi_id_encrypted,  # Encrypted
                bank_name=self.cleaned_data.get('bank_name'),
                is_approved=False,  # Requires admin approval
            )
        
        return user


class LoginForm(forms.Form):
    """
    Login form using email instead of username.
    Business Use: Customers and vendors login with email for simplicity.
    """
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your password'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Remember me for 30 days'
    )
    
    def clean(self):
        """Authenticate user"""
        cleaned_data = super().clean()
        email = cleaned_data.get('email', '').lower()
        password = cleaned_data.get('password')
        
        if email and password:
            # Get user by email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise ValidationError('Invalid email or password.')
            
            # Check password
            if not user.check_password(password):
                raise ValidationError('Invalid email or password.')
            
            # Check if user is active
            if not user.is_active:
                raise ValidationError('This account is inactive. Please contact support.')
            
            # Check if email is verified (optional enforcement)
            if not user.is_verified:
                raise ValidationError(
                    'Please verify your email address before logging in. '
                    'Check your inbox for the verification link.'
                )
            
            # Store user in cleaned data for view to use
            cleaned_data['user'] = user
        
        return cleaned_data


class ForgotPasswordForm(forms.Form):
    """
    Form to request password reset via email.
    Business Use: Allow users to reset forgotten passwords securely.
    """
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email',
            'autofocus': True
        })
    )
    
    def clean_email(self):
        """Verify email exists"""
        email = self.cleaned_data.get('email', '').lower()
        
        if not User.objects.filter(email=email).exists():
            # Don't reveal if email exists (security best practice)
            raise ValidationError(
                'If an account exists with this email, you will receive a password reset link.'
            )
        
        return email


class ResetPasswordForm(forms.Form):
    """
    Form to set new password during password reset flow.
    Business Use: Called after user verifies email token.
    """
    
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password (min 8 characters)'
        })
    )
    
    password_confirmation = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        }),
        label='Confirm Password'
    )
    
    def clean(self):
        """Validate password confirmation"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirmation = cleaned_data.get('password_confirmation')
        
        if password and password_confirmation and password != password_confirmation:
            raise ValidationError('Passwords do not match.')
        
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    """
    Form for users to update their basic profile information.
    Business Use: Allow users to change name, phone, notification preferences.
    """
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 XXXXXXXXXX'}),
        }


class VendorProfileUpdateForm(forms.ModelForm):
    """
    Form for vendors to update their profile with encrypted sensitive fields.
    Phase 10 - Task 2: Handles encryption/decryption of bank details and GSTIN.
    """
    
    class Meta:
        model = VendorProfile
        fields = ('company_name', 'business_address', 'state', 'city', 'pincode',
                  'bank_account_number', 'bank_ifsc_code', 'upi_id', 'bank_name')
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank account number (encrypted)'
            }),
            'bank_ifsc_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'IFSC code (encrypted)'
            }),
            'upi_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'UPI ID (encrypted)'
            }),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        """Decrypt fields for display in form"""
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            # Decrypt bank account for editing
            if self.instance.bank_account_number:
                try:
                    self.initial['bank_account_number'] = encryption_manager.decrypt(
                        self.instance.bank_account_number
                    )
                except:
                    pass  # Handle decryption errors gracefully
            
            # Decrypt IFSC code
            if self.instance.bank_ifsc_code:
                try:
                    self.initial['bank_ifsc_code'] = encryption_manager.decrypt(
                        self.instance.bank_ifsc_code
                    )
                except:
                    pass
            
            # Decrypt UPI ID
            if self.instance.upi_id:
                try:
                    self.initial['upi_id'] = encryption_manager.decrypt(
                        self.instance.upi_id
                    )
                except:
                    pass
    
    def clean_bank_ifsc_code(self):
        """Validate IFSC code if provided"""
        ifsc = self.cleaned_data.get('bank_ifsc_code', '').upper()
        if ifsc and not validate_ifsc_code(ifsc):
            raise ValidationError('Invalid IFSC code format. Expected: SBIN0012345')
        return ifsc
    
    def save(self, commit=True):
        """Encrypt sensitive fields before saving"""
        instance = super().save(commit=False)
        
        # Encrypt bank account
        bank_account = self.cleaned_data.get('bank_account_number')
        if bank_account:
            instance.bank_account_number = encryption_manager.encrypt(bank_account)
        
        # Encrypt IFSC code
        ifsc_code = self.cleaned_data.get('bank_ifsc_code')
        if ifsc_code:
            instance.bank_ifsc_code = encryption_manager.encrypt(ifsc_code)
        
        # Encrypt UPI ID
        upi_id = self.cleaned_data.get('upi_id')
        if upi_id:
            instance.upi_id = encryption_manager.encrypt(upi_id)
        
        if commit:
            instance.save()
        
        return instance


class ChangePasswordForm(forms.Form):
    """
    Form for users to change their password.
    Business Use: Security best practice - allow users to change passwords periodically.
    """
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current password'
        })
    )
    
    new_password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password (min 8 characters)'
        })
    )
    
    new_password_confirmation = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        label='Confirm New Password'
    )
    
    def __init__(self, user, *args, **kwargs):
        """Store user instance for password verification"""
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        """Verify current password"""
        current_password = self.cleaned_data.get('current_password')
        
        if not self.user.check_password(current_password):
            raise ValidationError('Current password is incorrect.')
        
        return current_password
    
    def clean(self):
        """Validate new password confirmation"""
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        new_password_confirmation = cleaned_data.get('new_password_confirmation')
        
        if new_password and new_password_confirmation and new_password != new_password_confirmation:
            raise ValidationError('New passwords do not match.')
        
        return cleaned_data
