from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from .models import User, VendorProfile, CustomerProfile


class CustomerRegistrationForm(UserCreationForm):
    """Form for customer registration"""
    first_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    state = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    city = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    pincode = forms.CharField(max_length=6, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    billing_address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=True)
    signup_coupon = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm Password'
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'customer'
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
            # Create customer profile
            CustomerProfile.objects.create(
                user=user,
                billing_address=self.cleaned_data['billing_address'],
                state=self.cleaned_data['state'],
                city=self.cleaned_data.get('city', ''),
                pincode=self.cleaned_data['pincode'],
                signup_coupon=self.cleaned_data.get('signup_coupon', '')
            )
        return user


class VendorRegistrationForm(UserCreationForm):
    """Form for vendor registration"""
    first_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    company_name = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    gstin = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    state = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    city = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    pincode = forms.CharField(max_length=6, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    business_address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=True)
    bank_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    bank_account_number = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    bank_ifsc_code = forms.CharField(max_length=11, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm Password'
    
    def save(self, commit=True):
        from rental_erp.encryption import encryption_manager
        user = super().save(commit=False)
        user.role = 'vendor'
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
            # Create vendor profile with encrypted fields
            VendorProfile.objects.create(
                user=user,
                company_name=self.cleaned_data['company_name'],
                gstin=encryption_manager.encrypt(self.cleaned_data['gstin']),
                business_address=self.cleaned_data['business_address'],
                state=self.cleaned_data['state'],
                city=self.cleaned_data.get('city', ''),
                pincode=self.cleaned_data['pincode'],
                bank_name=self.cleaned_data.get('bank_name', ''),
                bank_account_number=encryption_manager.encrypt(self.cleaned_data.get('bank_account_number', '')) if self.cleaned_data.get('bank_account_number') else '',
                bank_ifsc_code=encryption_manager.encrypt(self.cleaned_data.get('bank_ifsc_code', '')) if self.cleaned_data.get('bank_ifsc_code') else '',
                is_approved=False
            )
        return user


class LoginForm(forms.Form):
    """Login form with email and password"""
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    remember_me = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if user is None:
                raise forms.ValidationError('Invalid email or password')
            if not user.is_verified:
                raise forms.ValidationError('Please verify your email before logging in')
            cleaned_data['user'] = user
        
        return cleaned_data


class ForgotPasswordForm(forms.Form):
    """Password reset request form"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'})
    )


class ResetPasswordForm(forms.Form):
    """New password form for password reset"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'}),
        label='New Password'
    )
    password_confirmation = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'}),
        label='Confirm New Password'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirmation = cleaned_data.get('password_confirmation')
        
        if password and password_confirmation:
            if password != password_confirmation:
                raise forms.ValidationError('Passwords do not match')
        
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class VendorProfileUpdateForm(forms.ModelForm):
    """Form for vendors to update their profile"""
    class Meta:
        model = VendorProfile
        fields = (
            'company_name', 'business_address', 'state', 'city', 'pincode', 
            'bank_name', 'vendor_logo', 'advance_payment_type', 'advance_payment_percentage'
        )
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'vendor_logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'advance_payment_type': forms.Select(attrs={'class': 'form-select'}),
            'advance_payment_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class ChangePasswordForm(forms.Form):
    """Form for changing user password"""
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Current Password'
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='New Password'
    )
    new_password_confirmation = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Confirm New Password'
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise forms.ValidationError('Current password is incorrect')
        return current_password
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        new_password_confirmation = cleaned_data.get('new_password_confirmation')
        
        if new_password and new_password_confirmation:
            if new_password != new_password_confirmation:
                raise forms.ValidationError('New passwords do not match')
        
        return cleaned_data


class AdminVendorEditForm(forms.ModelForm):
    """
    Form for admin to edit vendor profile information.
    """
    # User fields
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False)
    
    class Meta:
        model = VendorProfile
        fields = [
            'company_name',
            'gstin',
            'bank_account_number',
            'bank_name',
            'upi_id',
            'business_address',
            'vendor_logo',
            'advance_payment_type',
            'advance_payment_percentage',
            'is_approved',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gstin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter new GSTIN or leave blank to keep current'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter new account number or leave blank'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'upi_id': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'vendor_logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'advance_payment_type': forms.Select(attrs={'class': 'form-select'}),
            'advance_payment_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate user fields from the related user object
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            self.fields['phone_number'].initial = self.instance.user.phone
        
        # Make encrypted fields not required since we'll preserve them if blank
        self.fields['gstin'].required = False
        self.fields['bank_account_number'].required = False
    
    def save(self, commit=True):
        vendor_profile = super().save(commit=False)
        
        # Update user fields
        user = vendor_profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone_number', '')
        
        if commit:
            user.save()
            vendor_profile.save()
        
        return vendor_profile
