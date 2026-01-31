from django.contrib import admin
from .models import (
    SystemConfiguration, LateFeePolicy,
    GSTConfiguration, EmailTemplate
)


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    """
    Admin for global system settings (singleton).
    Business Use: Centralized configuration for the entire ERP.
    """
    
    fieldsets = (
        ('Company Information', {
            'fields': (
                'company_name', 'company_gstin', 'company_address',
                'company_state', 'company_email', 'company_phone', 'company_logo'
            )
        }),
        ('Default Tax Rates', {
            'fields': ('default_cgst_rate', 'default_sgst_rate', 'default_igst_rate')
        }),
        ('Rental Configuration', {
            'fields': (
                'min_rental_hours', 'max_advance_booking_days',
                'quotation_validity_days'
            )
        }),
        ('Payment Settings', {
            'fields': (
                'require_deposit', 'default_deposit_percentage',
                'invoice_payment_terms_days'
            )
        }),
        ('Brevo SMTP Integration', {
            'fields': (
                'brevo_api_key', 'brevo_smtp_server', 'brevo_smtp_port',
                'brevo_sender_email', 'brevo_sender_name'
            ),
            'classes': ('collapse',)
        }),
        ('AppyFlow GSTIN Verification', {
            'fields': ('appyflow_api_key', 'enable_gstin_verification'),
            'classes': ('collapse',)
        }),
        ('Razorpay Payment Gateway', {
            'fields': ('razorpay_key_id', 'razorpay_key_secret', 'enable_razorpay'),
            'classes': ('collapse',)
        }),
        ('Website Settings', {
            'fields': (
                'site_title', 'site_tagline',
                'enable_customer_registration', 'enable_vendor_registration'
            )
        }),
        ('Notification Settings', {
            'fields': (
                'send_quotation_emails', 'send_order_confirmation_emails',
                'send_pickup_reminders', 'send_return_reminders',
                'return_reminder_hours_before'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent creating multiple configuration records"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of configuration"""
        return False


@admin.register(LateFeePolicy)
class LateFeePolicyAdmin(admin.ModelAdmin):
    """
    Admin for late return fee policies.
    Business Use: Configure penalties for late returns.
    """
    
    list_display = (
        'name', 'penalty_calculation_method', 'grace_period_hours',
        'get_penalty_rate', 'applies_to_all_products', 'is_active'
    )
    
    list_filter = (
        'is_active', 'penalty_calculation_method',
        'applies_to_all_products', 'effective_from'
    )
    
    search_fields = ('name', 'description')
    
    filter_horizontal = ('product_categories',)
    
    fieldsets = (
        ('Policy Information', {
            'fields': ('name', 'description')
        }),
        ('Grace Period', {
            'fields': ('grace_period_hours',)
        }),
        ('Penalty Configuration', {
            'fields': (
                'penalty_calculation_method',
                'penalty_rate_per_day', 'penalty_rate_per_hour',
                'penalty_percentage', 'max_penalty_cap'
            )
        }),
        ('Applicability', {
            'fields': ('applies_to_all_products', 'product_categories')
        }),
        ('Status & Validity', {
            'fields': ('is_active', 'effective_from', 'effective_until')
        }),
    )
    
    def get_penalty_rate(self, obj):
        if obj.penalty_calculation_method == 'per_day':
            return f"₹{obj.penalty_rate_per_day}/day"
        elif obj.penalty_calculation_method == 'per_hour':
            return f"₹{obj.penalty_rate_per_hour}/hour"
        else:
            return f"{obj.penalty_percentage}% of rental"
    get_penalty_rate.short_description = 'Penalty Rate'


@admin.register(GSTConfiguration)
class GSTConfigurationAdmin(admin.ModelAdmin):
    """
    Admin for category-wise GST rates.
    Business Use: Different products have different GST rates.
    """
    
    list_display = (
        'category', 'hsn_code', 'get_total_gst_rate',
        'is_active', 'effective_from', 'effective_until'
    )
    
    list_filter = ('is_active', 'effective_from', 'category')
    
    search_fields = ('category__name', 'hsn_code')
    
    fieldsets = (
        ('Category', {
            'fields': ('category', 'hsn_code')
        }),
        ('GST Rates', {
            'fields': ('cgst_rate', 'sgst_rate', 'igst_rate')
        }),
        ('Validity', {
            'fields': ('is_active', 'effective_from', 'effective_until')
        }),
    )
    
    def get_total_gst_rate(self, obj):
        return f"{obj.cgst_rate + obj.sgst_rate}% (CGST+SGST) / {obj.igst_rate}% (IGST)"
    get_total_gst_rate.short_description = 'Total GST'


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """
    Admin for email templates.
    Business Use: Customize automated notification emails.
    """
    
    list_display = (
        'get_template_type_display', 'subject', 'is_active', 'updated_at'
    )
    
    list_filter = ('is_active', 'template_type', 'updated_at')
    
    search_fields = ('template_type', 'subject', 'body_html', 'body_text')
    
    fieldsets = (
        ('Template Type', {
            'fields': ('template_type', 'is_active')
        }),
        ('Email Content', {
            'fields': ('subject', 'body_html', 'body_text')
        }),
        ('Available Variables', {
            'fields': ('available_variables',),
            'description': 'JSON list of variables that can be used in this template (e.g., customer_name, order_number)'
        }),
    )
