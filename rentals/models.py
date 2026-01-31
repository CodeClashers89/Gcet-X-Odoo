from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class Quotation(models.Model):
    """
    Price proposal for rental request (pre-order stage).
    
    Business Use: Customer adds items to cart → Quotation is created (Draft).
    Customer can review, modify quantities/dates before confirming.
    Once confirmed, Quotation becomes a RentalOrder.
    
    ERP Flow: Draft → Sent → Confirmed (→ converts to RentalOrder)
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),           # Being edited by customer
        ('sent', 'Sent'),             # Shared with customer for review
        ('confirmed', 'Confirmed'),   # Customer accepted, ready to become order
        ('cancelled', 'Cancelled'),   # Customer abandoned
        ('expired', 'Expired'),       # Validity period passed
    ]
    
    # Document identification
    quotation_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated unique quotation ID (e.g., QT-2026-0001)"
    )
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quotations',
        limit_choices_to={'role': 'customer'},
        help_text="Customer requesting the rental quote"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Current quotation stage"
    )
    
    # Validity period
    valid_until = models.DateField(
        help_text="Quotation expires after this date (typical: 7-30 days)"
    )
    
    # Pricing summary (calculated from QuotationLines)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Sum of all line items before tax/discount"
    )
    
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total discount applied"
    )
    
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="GST calculated (CGST+SGST or IGST)"
    )
    
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Final quotation amount (subtotal - discount + tax)"
    )
    
    # Advance Payment Terms
    advance_payment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Required advance payment % for this quotation"
    )
    
    advance_payment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Calculated advance amount to be paid"
    )
    
    # Notes and terms
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Special instructions or terms"
    )
    
    # Approval workflow
    requires_approval = models.BooleanField(
        default=False,
        help_text="Whether this quotation needs approval (for high-value orders)"
    )
    
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('not_required', 'Not Required'),
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='not_required',
        help_text="Current approval status"
    )
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approved_quotations',
        help_text="Admin or vendor who approved this quotation"
    )
    
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When this quotation was approved"
    )
    
    # State tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When customer confirmed this quotation"
    )
    
    class Meta:
        db_table = 'quotations'
        verbose_name = 'Quotation'
        verbose_name_plural = 'Quotations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['quotation_number']),
        ]
    
    def __str__(self):
        return f"{self.quotation_number} - {self.customer.get_full_name()} - ₹{self.total}"
    
    def calculate_totals(self):
        """Recalculate quotation totals from line items"""
        from decimal import Decimal
        
        lines = self.quotation_lines.all()
        # Use Decimal for sum to avoid float conversion
        self.subtotal = sum((line.line_total for line in lines), Decimal('0.00'))
        
        # Ensure discount_amount is Decimal
        if self.discount_amount is None:
            self.discount_amount = Decimal('0.00')
        
        # GST calculation (simplified - actual GST logic will be more complex)
        tax_rate = Decimal('0.18')  # 18% GST (will be configurable)
        self.tax_amount = (self.subtotal - self.discount_amount) * tax_rate
        self.total = self.subtotal - self.discount_amount + self.tax_amount
        
        # Calculate advance amount
        self.advance_payment_amount = (self.total * self.advance_payment_percentage) / Decimal('100.00')
        
        self.save()

    @property
    def total_amount(self):
        """Property alias for backward compatibility with notifications/templates"""
        return self.total


class QuotationLine(models.Model):
    """
    Individual line items in a quotation (products + rental periods).
    
    Business Use: Each product in the cart becomes a quotation line.
    Stores: What to rent, How many, Start date, End date, Price
    """
    
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name='quotation_lines',
        help_text="Parent quotation document"
    )
    
    # Product reference
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='quotation_lines',
        help_text="Product being quoted"
    )
    
    product_variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='quotation_lines',
        help_text="Specific variant if applicable"
    )
    
    # Rental period
    rental_start_date = models.DateTimeField(
        help_text="When customer wants to pick up the item"
    )
    
    rental_end_date = models.DateTimeField(
        help_text="When customer will return the item"
    )
    
    # Quantity
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of units to rent"
    )
    
    # Pricing
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Rental price per unit for the specified duration"
    )
    
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="quantity × unit_price"
    )
    
    # Pricing breakdown (for transparency)
    duration_days = models.PositiveIntegerField(
        default=1,
        help_text="Calculated rental duration in days"
    )
    
    duration_hours = models.PositiveIntegerField(
        default=0,
        help_text="Additional hours beyond full days"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'quotation_lines'
        verbose_name = 'Quotation Line'
        verbose_name_plural = 'Quotation Lines'
        ordering = ['quotation', 'id']
    
    def __str__(self):
        return f"{self.quotation.quotation_number} - {self.product.name} × {self.quantity}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate line total before saving"""
        from decimal import Decimal
        
        # Ensure unit_price is not None and is Decimal
        if self.unit_price is None:
            self.unit_price = Decimal('0.00')
        elif not isinstance(self.unit_price, Decimal):
            self.unit_price = Decimal(str(self.unit_price))
        
        # Ensure quantity is not None
        if self.quantity is None:
            self.quantity = 1
        
        # Calculate line total with proper Decimal arithmetic
        self.line_total = Decimal(str(self.quantity)) * self.unit_price
        super().save(*args, **kwargs)


class RentalOrder(models.Model):
    """
    Confirmed rental agreement (converted from Quotation).
    
    Business Use: When customer confirms quotation, it becomes a RentalOrder.
    This triggers:
    - Stock reservation
    - Pickup document generation
    - Invoice creation (draft)
    - Payment collection
    
    ERP Flow: Draft → Confirmed → In Progress → Completed → Invoiced
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),               # Initial state
        ('confirmed', 'Confirmed'),       # Customer committed, stock reserved
        ('in_progress', 'In Progress'),   # Customer has picked up items
        ('completed', 'Completed'),       # Items returned successfully
        ('cancelled', 'Cancelled'),       # Order cancelled before completion
        ('invoiced', 'Invoiced'),         # Invoice generated and sent
    ]
    
    # Document identification
    order_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated unique order ID (e.g., RO-2026-0001)"
    )
    
    # Link to original quotation
    quotation = models.OneToOneField(
        Quotation,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='rental_order',
        help_text="Source quotation that was converted to this order"
    )
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rental_orders',
        limit_choices_to={'role': 'customer'},
        help_text="Customer placing the rental order"
    )
    
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_rental_orders',
        limit_choices_to={'role': 'vendor'},
        help_text="Vendor fulfilling the rental order"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Current order stage in the rental lifecycle"
    )
    
    # Delivery details
    delivery_address = models.TextField(
        help_text="Where items will be delivered/picked up"
    )
    
    billing_address = models.TextField(
        help_text="Address for invoice (may differ from delivery)"
    )
    
    # Pricing (copied from quotation, but can be adjusted)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Sum of all order lines"
    )
    
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Discount applied"
    )
    
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="GST amount"
    )
    
    late_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Late return penalties (added if items returned late)"
    )
    
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Final order total including all fees"
    )
    
    # Advance Payment Tracking
    advance_payment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Required advance payment % for this order"
    )
    
    advance_payment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Calculated advance amount expected"
    )
    
    # Payment tracking
    deposit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Security deposit collected upfront"
    )
    
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount paid so far (partial or full)"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Special instructions or customer requests"
    )
    
    # Approval workflow
    requires_approval = models.BooleanField(
        default=False,
        help_text="Whether this order needs approval (for high-value orders)"
    )
    
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('not_required', 'Not Required'),
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='not_required',
        help_text="Current approval status"
    )
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approved_rental_orders',
        help_text="Admin who approved this order"
    )
    
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When this order was approved"
    )
    
    # State tracking timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When order was confirmed"
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When all items were returned"
    )
    
    class Meta:
        db_table = 'rental_orders'
        verbose_name = 'Rental Order'
        verbose_name_plural = 'Rental Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.customer.get_full_name()} - ₹{self.total}"
    
    @property
    def rental_start_date(self):
        """Property to get start date from first line item"""
        first_line = self.order_lines.first()
        return first_line.rental_start_date if first_line else None

    @property
    def rental_end_date(self):
        """Property to get end date from first line item"""
        first_line = self.order_lines.first()
        return first_line.rental_end_date if first_line else None

    @property
    def total_amount(self):
        """Property alias for backward compatibility with notifications/templates"""
        return self.total

    @property
    def pickup_location(self):
        """Property alias for delivery_address used in notifications"""
        return self.delivery_address

    @property
    def balance(self):
        """Calculate remaining balance"""
        return self.total - self.paid_amount

    def is_payment_complete(self):
        """Check if order is fully paid"""
        return self.paid_amount >= self.total

    def calculate_totals(self):
        """Recalculate order totals from line items"""
        from decimal import Decimal

        lines = self.order_lines.all()
        self.subtotal = sum((line.line_total for line in lines), Decimal('0.00'))

        if self.discount_amount is None:
            self.discount_amount = Decimal('0.00')
        if self.tax_amount is None:
            self.tax_amount = Decimal('0.00')
        if self.late_fee is None:
            self.late_fee = Decimal('0.00')

        self.total = self.subtotal - self.discount_amount + self.tax_amount + self.late_fee
        
        # Calculate advance amount
        self.advance_payment_amount = (self.total * self.advance_payment_percentage) / Decimal('100.00')
        
        if self.paid_amount is None:
            self.paid_amount = Decimal('0.00')

        self.save()
    
        return max(Decimal('0.00'), self.total - self.paid_amount)

    @property
    def total_amount(self):
        """Property alias for backward compatibility with notifications/templates"""
        return self.total


class RentalOrderLine(models.Model):
    """
    Individual items in a rental order with specific rental periods.
    
    Business Use: Tracks exactly what was rented, when, and for how long.
    Critical for reservation system to prevent double-booking.
    """
    
    rental_order = models.ForeignKey(
        RentalOrder,
        on_delete=models.CASCADE,
        related_name='order_lines',
        help_text="Parent rental order"
    )
    
    # Product reference
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='rental_order_lines',
        help_text="Product being rented"
    )
    
    product_variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='rental_order_lines',
        help_text="Specific variant being rented"
    )
    
    # Rental period (CRITICAL for reservation logic)
    rental_start_date = models.DateTimeField(
        help_text="Scheduled pickup date/time"
    )
    
    rental_end_date = models.DateTimeField(
        help_text="Scheduled return date/time"
    )
    
    # Actual pickup/return (updated during operations)
    actual_pickup_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When customer actually picked up the item"
    )
    
    actual_return_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When customer actually returned the item"
    )
    
    # Quantity
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of units rented"
    )
    
    # Pricing
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Rental price per unit"
    )
    
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="quantity × unit_price"
    )
    
    # Duration tracking
    duration_days = models.PositiveIntegerField(
        default=1,
        help_text="Rental duration in days"
    )
    
    duration_hours = models.PositiveIntegerField(
        default=0,
        help_text="Additional hours beyond full days"
    )
    
    # Late return tracking
    is_late_return = models.BooleanField(
        default=False,
        help_text="Item returned after scheduled end date"
    )
    
    late_days = models.PositiveIntegerField(
        default=0,
        help_text="Number of days late (0 if on time)"
    )
    
    late_fee_charged = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Late return penalty amount"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rental_order_lines'
        verbose_name = 'Rental Order Line'
        verbose_name_plural = 'Rental Order Lines'
        ordering = ['rental_order', 'id']
    
    def __str__(self):
        return f"{self.rental_order.order_number} - {self.product.name} × {self.quantity}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate line total"""
        from decimal import Decimal
        
        # Ensure unit_price is not None and is Decimal
        if self.unit_price is None:
            self.unit_price = Decimal('0.00')
        elif not isinstance(self.unit_price, Decimal):
            self.unit_price = Decimal(str(self.unit_price))
        
        # Ensure quantity is not None
        if self.quantity is None:
            self.quantity = 1
        
        # Calculate line total with proper Decimal arithmetic
        self.line_total = Decimal(str(self.quantity)) * self.unit_price
        super().save(*args, **kwargs)
    
    def calculate_late_fee(self):
        """
        Calculate late return fee based on system configuration.
        Business Logic: Grace period + per-day penalty rate
        """
        if not self.actual_return_date or not self.rental_end_date:
            return Decimal('0.00')
        
        if self.actual_return_date <= self.rental_end_date:
            return Decimal('0.00')  # Returned on time
        
        # Calculate late days
        late_duration = self.actual_return_date - self.rental_end_date
        self.late_days = late_duration.days
        
        # Get late fee policy from settings (simplified)
        from system_settings.models import LateFeePolicy
        try:
            policy = LateFeePolicy.objects.filter(is_active=True).first()
            if policy and self.late_days > policy.grace_period_hours / 24:
                billable_days = max(0, self.late_days - (policy.grace_period_hours // 24))
                self.late_fee_charged = billable_days * policy.penalty_rate_per_day * self.quantity
                self.is_late_return = True
        except:
            pass  # Default: no late fee if policy not configured
        
        return self.late_fee_charged


class Reservation(models.Model):
    """
    Inventory blocking mechanism to prevent double-booking.
    
    Business Use: CRITICAL for rental businesses.
    When an order is confirmed, reservations are created for each line item.
    This ensures the same product cannot be rented to two customers for overlapping dates.
    
    Example: Camera #1234 reserved from Jan 15-20 → Cannot be rented Jan 17-22 by another customer.
    """
    
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),   # Stock is blocked
        ('active', 'Active'),         # Customer has picked up (rental in progress)
        ('completed', 'Completed'),   # Item returned, stock released
        ('cancelled', 'Cancelled'),   # Reservation cancelled, stock released
    ]
    
    # Link to order line
    rental_order_line = models.ForeignKey(
        RentalOrderLine,
        on_delete=models.CASCADE,
        related_name='reservations',
        help_text="Which order line created this reservation"
    )
    
    # Product being reserved
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='reservations',
        help_text="Product whose inventory is blocked"
    )
    
    product_variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='reservations',
        help_text="Specific variant being reserved"
    )
    
    # Reservation period (copied from order line)
    rental_start_date = models.DateTimeField(
        help_text="Reservation start (blocks inventory from this date)"
    )
    
    rental_end_date = models.DateTimeField(
        help_text="Reservation end (inventory released after this date)"
    )
    
    # Quantity reserved
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="How many units are blocked"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='confirmed',
        help_text="Reservation lifecycle stage"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reservations'
        verbose_name = 'Reservation'
        verbose_name_plural = 'Reservations'
        ordering = ['rental_start_date']
        indexes = [
            models.Index(fields=['product', 'status', 'rental_start_date', 'rental_end_date']),
            models.Index(fields=['product_variant', 'status', 'rental_start_date', 'rental_end_date']),
        ]
    
    def __str__(self):
        item = self.product_variant if self.product_variant else self.product
        return f"Reserve {item.name} × {self.quantity} ({self.rental_start_date.date()} to {self.rental_end_date.date()})"


class Pickup(models.Model):
    """
    Pickup document tracking item handover to customer.
    
    Business Use: Generated when customer arrives to pick up rented items.
    Vendor verifies items, checks customer ID, records pickup time.
    Stock status changes from "Reserved" to "With Customer".
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),       # Scheduled, customer hasn't arrived
        ('in_progress', 'In Progress'), # Customer at location, checking items
        ('completed', 'Completed'),   # Items handed over successfully
        ('cancelled', 'Cancelled'),   # Customer didn't show up
    ]
    
    # Document identification
    pickup_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated pickup document ID (e.g., PU-2026-0001)"
    )
    
    rental_order = models.OneToOneField(
        RentalOrder,
        on_delete=models.CASCADE,
        related_name='pickup',
        help_text="Associated rental order"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Pickup process stage"
    )
    
    # Scheduling
    scheduled_pickup_date = models.DateTimeField(
        help_text="When customer plans to pick up items"
    )
    
    actual_pickup_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When items were actually handed over"
    )
    
    # Personnel
    handed_over_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='pickups_processed',
        help_text="Vendor staff who processed this pickup"
    )
    
    # Quality checks
    items_checked = models.BooleanField(
        default=False,
        help_text="Vendor verified all items before handover"
    )
    
    customer_id_verified = models.BooleanField(
        default=False,
        help_text="Customer identity verified"
    )
    
    pickup_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Condition notes, missing accessories, damages observed at pickup"
    )
    
    # Digital signature / proof
    customer_signature = models.TextField(
        blank=True,
        null=True,
        help_text="Digital signature data (base64) or acknowledgment"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pickups'
        verbose_name = 'Pickup'
        verbose_name_plural = 'Pickups'
        ordering = ['-scheduled_pickup_date']
    
    def __str__(self):
        return f"{self.pickup_number} - {self.rental_order.order_number}"


class Return(models.Model):
    """
    Return document tracking item return from customer.
    
    Business Use: Generated when customer returns rented items.
    Vendor inspects for damage, checks all items present, calculates late fees.
    Stock status changes from "With Customer" back to "Available".
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),         # Expected return, not yet arrived
        ('in_progress', 'In Progress'), # Customer returning, inspection underway
        ('completed', 'Completed'),     # All items returned and verified
        ('partial', 'Partial Return'),  # Some items returned, others pending
        ('damaged', 'Returned with Damage'), # Items returned but damaged
    ]
    
    # Document identification
    return_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated return document ID (e.g., RT-2026-0001)"
    )
    
    rental_order = models.OneToOneField(
        RentalOrder,
        on_delete=models.CASCADE,
        related_name='return_doc',
        help_text="Associated rental order"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Return process stage"
    )
    
    # Scheduling
    scheduled_return_date = models.DateTimeField(
        help_text="When customer should return items (from order)"
    )
    
    actual_return_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When items were actually returned"
    )
    
    # Personnel
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='returns_processed',
        help_text="Vendor staff who processed this return"
    )
    
    # Quality inspection
    all_items_returned = models.BooleanField(
        default=False,
        help_text="All rented items accounted for"
    )
    
    items_damaged = models.BooleanField(
        default=False,
        help_text="Any items returned with damage"
    )
    
    damage_description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed damage assessment (for security deposit deduction)"
    )
    
    damage_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Repair/replacement cost (deducted from deposit)"
    )
    
    # Late return
    is_late_return = models.BooleanField(
        default=False,
        help_text="Returned after scheduled date"
    )
    
    late_days = models.PositiveIntegerField(
        default=0,
        help_text="Number of days late"
    )
    
    late_fee_charged = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Late return penalty"
    )
    
    # Notes
    return_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Inspection notes, customer feedback, issues"
    )
    
    # Digital acknowledgment
    customer_signature = models.TextField(
        blank=True,
        null=True,
        help_text="Customer acknowledgment of return condition"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'returns'
        verbose_name = 'Return'
        verbose_name_plural = 'Returns'
        ordering = ['-scheduled_return_date']
    
    def __str__(self):
        return f"{self.return_number} - {self.rental_order.order_number}"
    
    def calculate_late_fee(self):
        """Calculate and apply late return fees"""
        if not self.actual_return_date or not self.scheduled_return_date:
            return
        
        if self.actual_return_date > self.scheduled_return_date:
            self.is_late_return = True
            late_duration = self.actual_return_date - self.scheduled_return_date
            self.late_days = late_duration.days
            
            # Apply late fees to order lines
            for line in self.rental_order.order_lines.all():
                line.actual_return_date = self.actual_return_date
                line.calculate_late_fee()
                line.save()
                self.late_fee_charged += line.late_fee_charged
            
            self.save()


class ApprovalRequest(models.Model):
    """
    Tracks approval requests for high-value quotations or orders.
    
    Business Use: Orders above approval threshold require admin approval.
    Tracks: Who requested approval, who approved, when, and reasons.
    
    Workflow:
    - Quotation/Order created with high value
    - ApprovalRequest created automatically (pending)
    - Admin reviews and approves or rejects
    - Status updated, audit logged
    """
    
    REQUEST_TYPE_CHOICES = [
        ('quotation', 'Quotation Approval'),
        ('order', 'Order Approval'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    # Document identification
    request_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated unique approval request ID (e.g., APR-2026-0001)"
    )
    
    request_type = models.CharField(
        max_length=20,
        choices=REQUEST_TYPE_CHOICES,
        help_text="Type of approval being requested"
    )
    
    # Links to source documents
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='approval_requests',
        help_text="Quotation requiring approval (if applicable)"
    )
    
    rental_order = models.ForeignKey(
        RentalOrder,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='approval_requests',
        help_text="Rental order requiring approval (if applicable)"
    )
    
    # Approval details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current approval status"
    )
    
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approval_requests_created',
        help_text="User who triggered the approval request"
    )
    
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='approval_requests_approved',
        help_text="Admin who approved/rejected the request"
    )
    
    approval_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for approval or rejection"
    )
    
    # Amount requiring approval
    approval_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total amount requiring approval"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When approval decision was made"
    )
    
    class Meta:
        db_table = 'approval_requests'
        verbose_name = 'Approval Request'
        verbose_name_plural = 'Approval Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['request_type', 'status']),
            models.Index(fields=['requested_by', 'status']),
            models.Index(fields=['approved_by', 'status']),
        ]
    
    def __str__(self):
        doc_name = f"QT-{self.quotation.quotation_number}" if self.quotation else f"RO-{self.rental_order.order_number}"
        return f"{self.request_number} - {doc_name} - {self.status.title()}"
    
    def approve(self, approver, notes=""):
        """Approve this request"""
        self.status = 'approved'
        self.approved_by = approver
        self.approval_notes = notes
        self.approved_at = timezone.now()
        self.save()
        
        # Update linked document's approval status
        if self.quotation:
            self.quotation.approval_status = 'approved'
            self.quotation.approved_by = approver
            self.quotation.approved_at = timezone.now()
            self.quotation.save()
        elif self.rental_order:
            self.rental_order.approval_status = 'approved'
            self.rental_order.approved_by = approver
            self.rental_order.approved_at = timezone.now()
            self.rental_order.save()
    
    def reject(self, approver, notes=""):
        """Reject this request"""
        self.status = 'rejected'
        self.approved_by = approver
        self.approval_notes = notes
        self.approved_at = timezone.now()
        self.save()
        
        # Update linked document's approval status
        if self.quotation:
            self.quotation.approval_status = 'rejected'
            self.quotation.approved_by = approver
            self.quotation.approved_at = timezone.now()
            self.quotation.save()
        elif self.rental_order:
            self.rental_order.approval_status = 'rejected'
            self.rental_order.approved_by = approver
            self.rental_order.approved_at = timezone.now()
            self.rental_order.save()


class RentalInquiry(models.Model):
    """
    Initial rental inquiry/query from customer.
    
    Business Use: Customer sends initial request for products and quantity.
    Vendor reviews and decides to create quotation or reject.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),                    # Awaiting vendor response
        ('sent_to_vendor', 'Sent to Vendor'),     # Sent to vendor
        ('accepted', 'Accepted'),                  # Vendor accepted, quotation in progress
        ('rejected', 'Rejected'),                  # Vendor rejected
        ('expired', 'Expired'),                    # Inquiry validity expired
    ]
    
    inquiry_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated inquiry ID"
    )
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rental_inquiries',
        limit_choices_to={'role': 'customer'}
    )
    
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_inquiries',
        limit_choices_to={'role': 'vendor'}
    )
    
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE
    )
    
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    quantity = models.PositiveIntegerField()
    
    rental_start_date = models.DateField()
    rental_end_date = models.DateField()
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rental_inquiries'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Inquiry {self.inquiry_number} - {self.product.name}"


