from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Supports role-based access control for Customer, Vendor, and Admin users.
    
    Business Use: Every rental business needs different user types with different permissions.
    - Customers: browse products, create quotations, place orders
    - Vendors: manage products, process orders, view earnings
    - Admins: full system access, analytics, configuration
    """
    
    # Role choices for RBAC (Role-Based Access Control)
    ROLE_CHOICES = [
        ('customer', 'Customer'),  # End-user who rents products
        ('vendor', 'Vendor'),      # Business user who owns rental products
        ('admin', 'Admin'),        # System administrator with full access
    ]
    
    # Core fields
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text="Used for login and notifications"
    )
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='customer',
        help_text="Determines user's permissions and accessible features"
    )
    
    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ],
        help_text="Contact number for order notifications and support"
    )
    
    is_verified = models.BooleanField(
        default=False,
        help_text="Email verification status for security"
    )
    
    # 2FA/MFA fields (Phase 10 - Task 5)
    totp_secret = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text="TOTP secret key for 2FA (encrypted)"
    )
    
    totp_enabled = models.BooleanField(
        default=False,
        help_text="Whether TOTP 2FA is enabled for this user"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Override username to use email as login credential
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def is_customer(self):
        """Check if user has customer role"""
        return self.role == 'customer'
    
    def is_vendor(self):
        """Check if user has vendor role"""
        return self.role == 'vendor'
    
    def is_admin_role(self):
        """Check if user has admin role"""
        return self.role == 'admin'


class CustomerProfile(models.Model):
    """
    Extended profile for Customer users.
    Stores business-specific information required for invoicing and legal compliance.
    
    Business Use: Real rental companies need customer's company details and GSTIN
    for generating GST-compliant invoices. This data is legally required in India.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile',
        limit_choices_to={'role': 'customer'},
        help_text="Links to the User account"
    )
    
    company_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Registered business name for invoicing (optional for individuals)"
    )
    
    # Encrypted fields (Phase 10 - Task 2)
    gstin = models.CharField(
        max_length=255,  # Increased for encrypted data
        blank=True,
        null=True,
        unique=True,
        help_text="GST Identification Number - mandatory for tax invoices (encrypted, optional for individuals)"
    )
    
    billing_address = models.TextField(
        help_text="Default address for invoice generation"
    )
    
    shipping_address = models.TextField(
        blank=True,
        null=True,
        help_text="Delivery address for rented equipment (can differ from billing)"
    )
    
    # Business location for GST calculation (intra-state vs inter-state)
    state = models.CharField(
        max_length=100,
        help_text="State for GST calculation (CGST+SGST vs IGST)"
    )
    
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    
    pincode = models.CharField(
        max_length=6,
        validators=[
            RegexValidator(regex=r'^\d{6}$', message="Enter a valid 6-digit pincode")
        ],
        help_text="Postal code for delivery logistics"
    )
    
    # Signup incentive tracking
    signup_coupon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Coupon code used during registration (for discounts/tracking)"
    )
    
    # Customer lifetime value tracking
    total_orders = models.PositiveIntegerField(
        default=0,
        help_text="Total number of rental orders placed"
    )
    
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Lifetime revenue from this customer"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customer_profiles'
        verbose_name = 'Customer Profile'
        verbose_name_plural = 'Customer Profiles'
    
    def __str__(self):
        return f"{self.company_name} - {self.gstin}"


class VendorProfile(models.Model):
    """
    Extended profile for Vendor users.
    Tracks vendor business details and performance metrics.
    
    Business Use: Vendors need to track their earnings, products, and performance.
    Admins need vendor-wise analytics for strategic decisions.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='vendorprofile',
        limit_choices_to={'role': 'vendor'},
        help_text="Links to the Vendor User account"
    )
    
    company_name = models.CharField(
        max_length=255,
        help_text="Vendor's registered business name"
    )
    
    # Encrypted fields (Phase 10 - Task 2)
    gstin = models.CharField(
        max_length=255,  # Increased for encrypted data
        unique=True,
        help_text="Vendor's GST number for tax compliance (encrypted)"
    )
    
    business_address = models.TextField(
        help_text="Vendor's business location"
    )
    
    state = models.CharField(
        max_length=100,
        help_text="State for GST calculations"
    )
    
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    
    pincode = models.CharField(
        max_length=6,
        validators=[
            RegexValidator(regex=r'^\d{6}$', message="Enter a valid 6-digit pincode")
        ]
    )
    
    # Bank details for payment settlements (Phase 10 - Task 2: Encrypted)
    bank_account_number = models.CharField(
        max_length=255,  # Increased for encrypted data
        blank=True,
        null=True,
        help_text="For revenue payouts (encrypted)"
    )
    
    bank_ifsc_code = models.CharField(
        max_length=255,  # Increased for encrypted data
        blank=True,
        null=True,
        help_text="Bank branch code (encrypted)"
    )
    
    vendor_logo = models.ImageField(
        upload_to='vendors/logos/',
        blank=True,
        null=True,
        help_text="Vendor's business logo for documents"
    )
    
    # Financial Terms
    ADVANCE_PAYMENT_CHOICES = [
        ('none', 'No Advance Required'),
        ('half', '50% Advance Required'),
        ('full', '100% Advance Required'),
        ('custom', 'Custom Percentage Advance'),
    ]
    
    advance_payment_type = models.CharField(
        max_length=20,
        choices=ADVANCE_PAYMENT_CHOICES,
        default='none',
        help_text="Standard advance payment policy for this vendor"
    )
    
    advance_payment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Percentage of total to be paid as advance (for 'custom' type)"
    )
    
    upi_id = models.CharField(
        max_length=255,  # Encrypted UPI ID for alternative payment
        blank=True,
        null=True,
        help_text="UPI ID for instant payouts (encrypted)"
    )
    
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    
    # Performance metrics
    total_products = models.PositiveIntegerField(
        default=0,
        help_text="Number of products listed by this vendor"
    )
    
    total_rentals = models.PositiveIntegerField(
        default=0,
        help_text="Total rental orders fulfilled"
    )
    
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Lifetime earnings from rentals"
    )
    
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Customer satisfaction score (0-5)"
    )
    
    # Vendor onboarding status
    is_approved = models.BooleanField(
        default=False,
        help_text="Admin approval required before vendor can list products"
    )
    
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When admin approved this vendor"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vendor_profiles'
        verbose_name = 'Vendor Profile'
        verbose_name_plural = 'Vendor Profiles'
    
    def __str__(self):
        return f"{self.company_name} - {self.user.get_full_name()}"


class UserConsent(models.Model):
    """
    Track user consent for GDPR compliance.
    GDPR Article 7 - Conditions for consent.
    """
    CONSENT_TYPES = [
        ('terms_of_service', 'Terms of Service'),
        ('privacy_policy', 'Privacy Policy'),
        ('data_processing', 'Data Processing'),
        ('marketing', 'Marketing Communications'),
        ('cookies', 'Cookie Usage'),
        ('third_party_sharing', 'Third-Party Data Sharing'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='consents',
        help_text="User who gave consent"
    )
    
    consent_type = models.CharField(
        max_length=50,
        choices=CONSENT_TYPES,
        help_text="Type of consent given"
    )
    
    granted = models.BooleanField(
        default=False,
        help_text="Whether consent was granted or withdrawn"
    )
    
    granted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When consent was given or withdrawn"
    )
    
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP address when consent was given"
    )
    
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="Browser user agent when consent was given"
    )
    
    # Version tracking for policy updates
    policy_version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Version of the policy user consented to"
    )
    
    # Withdrawal tracking
    withdrawn_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When consent was withdrawn (if applicable)"
    )
    
    class Meta:
        db_table = 'user_consents'
        verbose_name = 'User Consent'
        verbose_name_plural = 'User Consents'
        ordering = ['-granted_at']
        indexes = [
            models.Index(fields=['user', 'consent_type']),
            models.Index(fields=['granted_at']),
        ]
    
    def __str__(self):
        status = 'Granted' if self.granted else 'Withdrawn'
        return f"{self.user.email} - {self.consent_type} ({status})"
    
    def withdraw(self):
        """Withdraw consent."""
        from django.utils import timezone
        self.granted = False
        self.withdrawn_at = timezone.now()
        self.save()


class DataDeletionRequest(models.Model):
    """
    Track GDPR Article 17 - Right to Erasure requests.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='deletion_requests',
        help_text="User requesting data deletion"
    )
    
    request_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When deletion was requested"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of deletion request"
    )
    
    reason = models.TextField(
        blank=True,
        null=True,
        help_text="User's reason for requesting deletion"
    )
    
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When data deletion was completed"
    )
    
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='completed_deletions',
        help_text="Admin who completed the deletion"
    )
    
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for rejecting deletion request (e.g., legal hold)"
    )
    
    # Audit trail
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP address when request was made"
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes about the deletion process"
    )
    
    class Meta:
        db_table = 'data_deletion_requests'
        verbose_name = 'Data Deletion Request'
        verbose_name_plural = 'Data Deletion Requests'
        ordering = ['-request_date']
    
    def __str__(self):
        return f"{self.user.email} - {self.status} - {self.request_date}"


class APIKey(models.Model):
    """
    API keys for secure external API access.
    Stores only hashed keys for security.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys',
        help_text="Owner of the API key"
    )

    name = models.CharField(
        max_length=100,
        help_text="Friendly name for the API key (e.g., 'Mobile App')"
    )

    key_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="SHA256 hash of the API key"
    )

    prefix = models.CharField(
        max_length=10,
        default='sk_',
        help_text="API key prefix"
    )

    last_four = models.CharField(
        max_length=4,
        help_text="Last four characters of the API key for display"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the API key was created"
    )

    last_used_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last time the API key was used"
    )

    last_used_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="IP address from last API key use"
    )

    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of times the API key was used"
    )

    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Expiration date for the API key"
    )

    revoked_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the API key was revoked"
    )

    class Meta:
        db_table = 'api_keys'
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['key_hash']),
            models.Index(fields=['last_used_at']),
        ]

    @property
    def is_active(self):
        if self.revoked_at:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=['revoked_at'])

    def __str__(self):
        return f"{self.user.email} - {self.name} ({self.prefix}****{self.last_four})"
