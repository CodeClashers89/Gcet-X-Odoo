from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class SystemConfiguration(models.Model):
    """
    Global system settings and configuration.
    
    Business Use: Centralized configuration management for the entire ERP.
    Admins can modify business rules without code changes.
    Examples: Company details, default tax rates, rental periods, email settings
    """
    
    # Company Information
    company_name = models.CharField(
        max_length=255,
        default='Rental ERP',
        help_text="Company name displayed on invoices and website"
    )
    
    company_gstin = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Master GSTIN (if system is for single company)"
    )
    
    company_address = models.TextField(
        blank=True,
        null=True,
        help_text="Registered business address"
    )
    
    company_state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="State for GST calculations"
    )
    
    company_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Primary contact email"
    )
    
    company_phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Customer support phone number"
    )
    
    company_logo = models.ImageField(
        upload_to='company/',
        blank=True,
        null=True,
        help_text="Company logo for invoices and website header"
    )
    
    # Default Tax Rates
    default_cgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=9.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Default CGST rate % (typically 9% for 18% GST)"
    )
    
    default_sgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=9.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Default SGST rate % (typically 9% for 18% GST)"
    )
    
    default_igst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Default IGST rate % (typically 18%)"
    )
    
    # Rental Configuration
    min_rental_hours = models.PositiveIntegerField(
        default=1,
        help_text="Minimum rental duration in hours"
    )
    
    max_advance_booking_days = models.PositiveIntegerField(
        default=90,
        help_text="How far in advance customers can book (days)"
    )
    
    quotation_validity_days = models.PositiveIntegerField(
        default=7,
        help_text="Default quotation validity period (days)"
    )
    
    # Payment Settings
    require_deposit = models.BooleanField(
        default=True,
        help_text="Require security deposit for rentals"
    )
    
    default_deposit_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Default deposit % of rental amount"
    )
    
    invoice_payment_terms_days = models.PositiveIntegerField(
        default=0,
        help_text="Default invoice payment terms (0 = immediate)"
    )
    
    # Email/SMS Integration
    brevo_api_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Brevo (Sendinblue) SMTP API key for transactional emails"
    )
    
    brevo_smtp_server = models.CharField(
        max_length=255,
        default='smtp-relay.brevo.com',
        help_text="Brevo SMTP server address"
    )
    
    brevo_smtp_port = models.PositiveIntegerField(
        default=587,
        help_text="Brevo SMTP port"
    )
    
    brevo_sender_email = models.EmailField(
        blank=True,
        null=True,
        help_text="From email address for notifications"
    )
    
    brevo_sender_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="From name for email notifications"
    )
    
    # AppyFlow GSTIN Verification
    appyflow_api_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="AppyFlow API key for GSTIN verification"
    )
    
    enable_gstin_verification = models.BooleanField(
        default=False,
        help_text="Verify GSTIN via AppyFlow API during signup"
    )
    
    # Payment Gateway
    razorpay_key_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Razorpay Key ID"
    )
    
    razorpay_key_secret = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Razorpay Key Secret"
    )
    
    enable_razorpay = models.BooleanField(
        default=False,
        help_text="Enable Razorpay payment gateway"
    )
    
    # Website Settings
    site_title = models.CharField(
        max_length=100,
        default='Rental Management System',
        help_text="Website title (shown in browser tab)"
    )
    
    site_tagline = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Website tagline/slogan"
    )
    
    enable_customer_registration = models.BooleanField(
        default=True,
        help_text="Allow new customer signups"
    )
    
    enable_vendor_registration = models.BooleanField(
        default=False,
        help_text="Allow new vendor signups (usually admin-only)"
    )
    
    # Notification Settings
    send_quotation_emails = models.BooleanField(
        default=True,
        help_text="Email customer when quotation is created"
    )
    
    send_order_confirmation_emails = models.BooleanField(
        default=True,
        help_text="Email customer when order is confirmed"
    )
    
    send_pickup_reminders = models.BooleanField(
        default=True,
        help_text="Email reminder before pickup date"
    )
    
    send_return_reminders = models.BooleanField(
        default=True,
        help_text="Email reminder before return date"
    )
    
    return_reminder_hours_before = models.PositiveIntegerField(
        default=24,
        help_text="Send return reminder X hours before due date"
    )
    
    # Approval Workflow (Phase 8)
    enable_quotation_approvals = models.BooleanField(
        default=True,
        help_text="Require approval for high-value quotations"
    )
    
    quotation_approval_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=50000.00,
        validators=[MinValueValidator(0)],
        help_text="Quotations above this amount require approval"
    )
    
    enable_order_approvals = models.BooleanField(
        default=True,
        help_text="Require approval for high-value orders"
    )
    
    order_approval_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=100000.00,
        validators=[MinValueValidator(0)],
        help_text="Orders above this amount require approval"
    )
    
    # Singleton pattern (only one configuration record)
    class Meta:
        db_table = 'system_configuration'
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configuration'
    
    def __str__(self):
        return f"System Configuration - {self.company_name}"
    
    def save(self, *args, **kwargs):
        """Ensure only one configuration record exists"""
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of configuration"""
        pass
    
    @classmethod
    def get_config(cls):
        """Get or create singleton configuration"""
        config, created = cls.objects.get_or_create(pk=1)
        return config


class LateFeePolicy(models.Model):
    """
    Late return fee configuration.
    
    Business Use: Incentivize on-time returns and compensate vendor for lost rental opportunities.
    Example: 2-hour grace period, then ₹100/day penalty
    """
    
    name = models.CharField(
        max_length=100,
        help_text="Policy name (e.g., 'Standard Late Fee', 'Premium Equipment Late Fee')"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Policy description shown to customers"
    )
    
    # Grace period before penalties apply
    grace_period_hours = models.PositiveIntegerField(
        default=2,
        help_text="Free grace period in hours (e.g., 2 hours late = no charge)"
    )
    
    # Penalty calculation
    penalty_calculation_method = models.CharField(
        max_length=20,
        choices=[
            ('per_day', 'Per Day'),
            ('per_hour', 'Per Hour'),
            ('percentage', 'Percentage of Rental'),
        ],
        default='per_day',
        help_text="How late fees are calculated"
    )
    
    penalty_rate_per_day = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Fixed penalty per day (if method = per_day)"
    )
    
    penalty_rate_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Fixed penalty per hour (if method = per_hour)"
    )
    
    penalty_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Penalty as % of original rental amount (if method = percentage)"
    )
    
    # Limits
    max_penalty_cap = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Maximum late fee amount (prevents excessive charges)"
    )
    
    # Applicability
    applies_to_all_products = models.BooleanField(
        default=True,
        help_text="Apply this policy to all products"
    )
    
    product_categories = models.ManyToManyField(
        'catalog.ProductCategory',
        blank=True,
        related_name='late_fee_policies',
        help_text="Apply policy only to these categories (if not all products)"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Is this policy currently in effect"
    )
    
    effective_from = models.DateField(
        blank=True,
        null=True,
        help_text="Policy effective start date"
    )
    
    effective_until = models.DateField(
        blank=True,
        null=True,
        help_text="Policy expiration date (optional)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'late_fee_policies'
        verbose_name = 'Late Fee Policy'
        verbose_name_plural = 'Late Fee Policies'
        ordering = ['-is_active', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.penalty_calculation_method}"


class GSTConfiguration(models.Model):
    """
    GST rate configuration for different product categories.
    
    Business Use: Different products may have different GST rates.
    Example: 
    - Electronics: 18% GST
    - Medical equipment: 12% GST
    - Essential services: 5% GST
    """
    
    category = models.ForeignKey(
        'catalog.ProductCategory',
        on_delete=models.CASCADE,
        related_name='gst_configurations',
        help_text="Product category this GST rate applies to"
    )
    
    hsn_code = models.CharField(
        max_length=10,
        help_text="HSN code for this category (GST compliance)"
    )
    
    cgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="CGST rate % for this category"
    )
    
    sgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="SGST rate % for this category"
    )
    
    igst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="IGST rate % for this category"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Is this configuration active"
    )
    
    effective_from = models.DateField(
        help_text="When this GST rate becomes effective"
    )
    
    effective_until = models.DateField(
        blank=True,
        null=True,
        help_text="When this GST rate expires (for rate changes)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'gst_configurations'
        verbose_name = 'GST Configuration'
        verbose_name_plural = 'GST Configurations'
        ordering = ['category', '-effective_from']
        unique_together = ['category', 'effective_from']
    
    def __str__(self):
        return f"{self.category.name} - {self.cgst_rate + self.sgst_rate}% GST"


class EmailTemplate(models.Model):
    """
    Email templates for automated notifications.
    
    Business Use: Customizable email templates for different ERP events.
    Examples: Order confirmation, pickup reminder, late return alert
    """
    
    TEMPLATE_TYPE_CHOICES = [
        ('quotation_created', 'Quotation Created'),
        ('quotation_sent', 'Quotation Sent to Customer'),
        ('order_confirmed', 'Order Confirmed'),
        ('pickup_reminder', 'Pickup Reminder'),
        ('return_reminder', 'Return Reminder'),
        ('late_return_alert', 'Late Return Alert'),
        ('invoice_sent', 'Invoice Sent'),
        ('payment_received', 'Payment Received'),
        ('welcome_customer', 'Welcome Email (Customer)'),
        ('welcome_vendor', 'Welcome Email (Vendor)'),
        ('password_reset', 'Password Reset'),
    ]
    
    template_type = models.CharField(
        max_length=50,
        choices=TEMPLATE_TYPE_CHOICES,
        unique=True,
        help_text="Email trigger event"
    )
    
    subject = models.CharField(
        max_length=255,
        help_text="Email subject line (supports variables like {{order_number}})"
    )
    
    body_html = models.TextField(
        help_text="HTML email body (supports Django template syntax)"
    )
    
    body_text = models.TextField(
        help_text="Plain text fallback for email clients that don't support HTML"
    )
    
    # Available variables
    available_variables = models.JSONField(
        default=list,
        help_text="List of variables available for this template (e.g., ['customer_name', 'order_number'])"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Should this template be used"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_templates'
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
        ordering = ['template_type']
    
    def __str__(self):
        return f"{self.get_template_type_display()} - {self.subject}"
