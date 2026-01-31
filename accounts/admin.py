from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, CustomerProfile, VendorProfile
from .models import APIKey


class CustomerProfileInline(admin.StackedInline):
    """
    Inline admin for CustomerProfile.
    Allows editing customer details directly within User admin.
    """
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = 'Customer Profile'
    fk_name = 'user'
    fields = (
        'company_name', 'gstin', 'billing_address', 'shipping_address',
        'state', 'city', 'pincode', 'signup_coupon',
        'total_orders', 'total_spent'
    )
    readonly_fields = ('total_orders', 'total_spent')


class VendorProfileInline(admin.StackedInline):
    """
    Inline admin for VendorProfile.
    Allows editing vendor details directly within User admin.
    """
    model = VendorProfile
    can_delete = False
    verbose_name_plural = 'Vendor Profile'
    fk_name = 'user'
    fields = (
        'company_name', 'gstin', 'business_address',
        'state', 'city', 'pincode',
        ('bank_account_number', 'bank_ifsc_code', 'bank_name'),
        ('total_products', 'total_rentals', 'total_revenue', 'average_rating'),
        ('is_approved', 'approved_at')
    )
    readonly_fields = ('total_products', 'total_rentals', 'total_revenue', 'average_rating', 'approved_at')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin with role-based management.
    Extends Django's default UserAdmin to include custom fields and profile inlines.
    """
    
    list_display = (
        'email', 'get_full_name', 'role', 'is_verified',
        'is_active', 'is_staff', 'date_joined'
    )
    
    list_filter = (
        'role', 'is_verified', 'is_active', 'is_staff',
        'is_superuser', 'date_joined'
    )
    
    search_fields = ('email', 'first_name', 'last_name', 'username', 'phone')
    
    ordering = ('-date_joined',)
    
    # Fieldsets for add/change forms
    fieldsets = (
        ('Login Credentials', {
            'fields': ('email', 'username', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone')
        }),
        ('Role & Permissions', {
            'fields': ('role', 'is_verified', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Groups & Permissions', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'first_name', 'last_name',
                'role', 'password1', 'password2'
            ),
        }),
    )
    
    readonly_fields = ('date_joined', 'last_login')
    
    def get_inline_instances(self, request, obj=None):
        """
        Dynamically show profile inline based on user role.
        Business Logic: Only show relevant profile form for each user type.
        """
        if not obj:
            return []
        
        inlines = []
        if obj.is_customer():
            inlines.append(CustomerProfileInline(self.model, self.admin_site))
        elif obj.is_vendor():
            inlines.append(VendorProfileInline(self.model, self.admin_site))
        
        return inlines
    
    def get_queryset(self, request):
        """
        Filter users based on current admin's role.
        Business Logic: Vendors shouldn't see other vendors' data.
        """
        qs = super().get_queryset(request)
        
        # Superusers and admins see everything
        if request.user.is_superuser or request.user.is_admin_role():
            return qs
        
        # Vendors only see their own account
        if request.user.is_vendor():
            return qs.filter(pk=request.user.pk)
        
        return qs


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """
    Standalone admin for CustomerProfile (for bulk operations).
    """
    
    list_display = (
        'company_name', 'get_customer_name', 'gstin', 'state',
        'total_orders', 'total_spent', 'created_at'
    )
    
    list_filter = ('state', 'created_at')
    
    search_fields = (
        'company_name', 'gstin', 'user__email',
        'user__first_name', 'user__last_name'
    )
    
    readonly_fields = ('total_orders', 'total_spent', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'company_name', 'gstin')
        }),
        ('Address Details', {
            'fields': ('billing_address', 'shipping_address', 'state', 'city', 'pincode')
        }),
        ('Business Metrics', {
            'fields': ('total_orders', 'total_spent', 'signup_coupon'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_customer_name(self, obj):
        return obj.user.get_full_name()
    get_customer_name.short_description = 'Customer Name'


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    """
    Standalone admin for VendorProfile with approval workflow.
    """
    
    list_display = (
        'company_name', 'get_vendor_name', 'gstin', 'state',
        'is_approved', 'total_products', 'total_revenue', 'average_rating'
    )
    
    list_filter = ('is_approved', 'state', 'created_at')
    
    search_fields = (
        'company_name', 'gstin', 'user__email',
        'user__first_name', 'user__last_name'
    )
    
    readonly_fields = (
        'total_products', 'total_rentals', 'total_revenue',
        'average_rating', 'approved_at', 'created_at', 'updated_at'
    )
    
    actions = ['approve_vendors', 'disapprove_vendors']
    
    fieldsets = (
        ('Vendor Information', {
            'fields': ('user', 'company_name', 'gstin')
        }),
        ('Business Address', {
            'fields': ('business_address', 'state', 'city', 'pincode')
        }),
        ('Bank Details', {
            'fields': ('bank_account_number', 'bank_ifsc_code', 'bank_name'),
            'classes': ('collapse',)
        }),
        ('Performance Metrics', {
            'fields': (
                'total_products', 'total_rentals',
                'total_revenue', 'average_rating'
            ),
            'classes': ('collapse',)
        }),
        ('Approval Status', {
            'fields': ('is_approved', 'approved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_vendor_name(self, obj):
        return obj.user.get_full_name()
    get_vendor_name.short_description = 'Vendor Name'
    
    def approve_vendors(self, request, queryset):
        """Bulk approve vendors"""
        from django.utils import timezone
        updated = queryset.update(is_approved=True, approved_at=timezone.now())
        self.message_user(request, f'{updated} vendor(s) approved successfully.')
    approve_vendors.short_description = 'Approve selected vendors'
    
    def disapprove_vendors(self, request, queryset):
        """Bulk disapprove vendors"""
        updated = queryset.update(is_approved=False, approved_at=None)
        self.message_user(request, f'{updated} vendor(s) disapproved.')
    disapprove_vendors.short_description = 'Disapprove selected vendors'


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'name', 'prefix', 'last_four', 'created_at',
        'last_used_at', 'usage_count', 'expires_at', 'revoked_at'
    )
    list_filter = ('revoked_at', 'created_at', 'expires_at')
    search_fields = ('user__email', 'name', 'last_four')
    readonly_fields = (
        'key_hash', 'prefix', 'last_four', 'created_at',
        'last_used_at', 'last_used_ip', 'usage_count', 'revoked_at'
    )
    ordering = ('-created_at',)
