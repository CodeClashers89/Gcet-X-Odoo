from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from decimal import Decimal


class Invoice(models.Model):
    """
    Legal financial document requesting payment from customer.
    
    Business Use: Generated after rental order confirmation or completion.
    Must be GST-compliant for Indian businesses (CGST+SGST or IGST).
    Tracks payment status: Draft → Sent → Paid
    
    Critical for: Revenue recognition, Tax compliance, Customer billing
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),           # Being prepared, not sent to customer
        ('sent', 'Sent'),             # Sent to customer, awaiting payment
        ('partially_paid', 'Partially Paid'),  # Some payment received
        ('paid', 'Paid'),             # Fully paid
        ('overdue', 'Overdue'),       # Payment deadline passed
        ('cancelled', 'Cancelled'),   # Invoice voided
    ]
    
    PAYMENT_TERM_CHOICES = [
        ('immediate', 'Immediate'),       # Pay before pickup
        ('on_delivery', 'On Delivery'),   # Pay at pickup
        ('net_7', 'Net 7 Days'),          # Pay within 7 days
        ('net_15', 'Net 15 Days'),
        ('net_30', 'Net 30 Days'),
        ('on_return', 'On Return'),       # Pay after return
    ]
    
    # Document identification
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated invoice ID (e.g., INV-2026-0001)"
    )
    
    # Link to rental order
    rental_order = models.ForeignKey(
        'rentals.RentalOrder',
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text="Rental order being invoiced"
    )
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invoices',
        limit_choices_to={'role': 'customer'},
        help_text="Customer being billed"
    )
    
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_invoices',
        limit_choices_to={'role': 'vendor'},
        help_text="Vendor issuing the invoice"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Invoice lifecycle stage"
    )
    
    # Dates
    invoice_date = models.DateField(
        help_text="Invoice issue date"
    )
    
    due_date = models.DateField(
        help_text="Payment deadline"
    )
    
    payment_terms = models.CharField(
        max_length=20,
        choices=PAYMENT_TERM_CHOICES,
        default='immediate',
        help_text="When payment is expected"
    )
    
    # Billing details (copied from customer profile at invoice time)
    billing_name = models.CharField(
        max_length=255,
        help_text="Customer's company name for invoice"
    )
    
    billing_gstin = models.CharField(
        max_length=15,
        help_text="Customer's GSTIN for GST compliance"
    )
    
    billing_address = models.TextField(
        help_text="Customer's billing address"
    )
    
    billing_state = models.CharField(
        max_length=100,
        help_text="State for GST calculation (intra-state vs inter-state)"
    )
    
    # Vendor details (for invoice header)
    vendor_name = models.CharField(
        max_length=255,
        help_text="Vendor's company name"
    )
    
    vendor_gstin = models.CharField(
        max_length=15,
        help_text="Vendor's GSTIN"
    )
    
    vendor_address = models.TextField(
        help_text="Vendor's business address"
    )
    
    vendor_state = models.CharField(
        max_length=100,
        help_text="Vendor's state (for GST type determination)"
    )
    
    # Pricing breakdown
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Sum of all invoice lines before tax/discount"
    )
    
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Discount applied"
    )
    
    # GST calculation
    is_intrastate = models.BooleanField(
        default=True,
        help_text="Same state transaction (CGST+SGST) or inter-state (IGST)"
    )
    
    cgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=9.00,
        help_text="Central GST rate % (typically 9% for 18% total GST)"
    )
    
    sgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=9.00,
        help_text="State GST rate % (typically 9% for 18% total GST)"
    )
    
    igst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        help_text="Integrated GST rate % (for inter-state)"
    )
    
    cgst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Central GST amount (intra-state only)"
    )
    
    sgst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="State GST amount (intra-state only)"
    )
    
    igst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Integrated GST amount (inter-state only)"
    )
    
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total tax (CGST+SGST or IGST)"
    )
    
    # Additional charges
    late_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Late return penalties"
    )
    
    damage_charges = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Equipment damage costs"
    )
    
    other_charges = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Miscellaneous charges (delivery, packaging, etc.)"
    )
    
    # Totals
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Final invoice total (subtotal - discount + tax + fees)"
    )

    @property
    def total_amount(self):
        """Property alias for backward compatibility with notifications/templates"""
        return self.total
    
    # Payment tracking
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount paid so far"
    )
    
    balance_due = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Remaining amount to be paid"
    )
    
    # Deposit handling
    deposit_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Security deposit collected upfront"
    )
    
    deposit_refunded = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Deposit returned after successful return"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes or special instructions"
    )
    
    customer_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes visible to customer on invoice"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When invoice was sent to customer"
    )
    paid_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When invoice was fully paid"
    )
    
    class Meta:
        db_table = 'invoices'
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-invoice_date', '-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['due_date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number} - {self.billing_name} - ₹{self.total}"
    
    def calculate_gst(self):
        """
        Calculate GST based on customer and vendor states.
        Business Rule: Same state = CGST+SGST, Different state = IGST
        """
        taxable_amount = self.subtotal - self.discount_amount + self.late_fee + self.damage_charges + self.other_charges
        
        if self.billing_state == self.vendor_state:
            # Intra-state: CGST + SGST
            self.is_intrastate = True
            self.cgst_amount = (taxable_amount * self.cgst_rate) / 100
            self.sgst_amount = (taxable_amount * self.sgst_rate) / 100
            self.igst_amount = Decimal('0.00')
            self.tax_amount = self.cgst_amount + self.sgst_amount
        else:
            # Inter-state: IGST
            self.is_intrastate = False
            self.cgst_amount = Decimal('0.00')
            self.sgst_amount = Decimal('0.00')
            self.igst_amount = (taxable_amount * self.igst_rate) / 100
            self.tax_amount = self.igst_amount
    
    def calculate_totals(self):
        """Recalculate all invoice totals"""
        from decimal import Decimal
        
        # Sum invoice lines with proper Decimal handling
        lines = self.invoice_lines.all()
        self.subtotal = sum((line.line_total for line in lines), Decimal('0.00'))
        
        # Calculate GST
        self.calculate_gst()
        
        # Ensure all amounts are Decimal
        if self.discount_amount is None:
            self.discount_amount = Decimal('0.00')
        if self.late_fee is None:
            self.late_fee = Decimal('0.00')
        if self.damage_charges is None:
            self.damage_charges = Decimal('0.00')
        if self.other_charges is None:
            self.other_charges = Decimal('0.00')
        if self.tax_amount is None:
            self.tax_amount = Decimal('0.00')
        
        # Calculate final total
        self.total = (
            self.subtotal 
            - self.discount_amount 
            + self.tax_amount 
            + self.late_fee 
            + self.damage_charges 
            + self.other_charges
        )
        
        # Update balance
        if self.paid_amount is None:
            self.paid_amount = Decimal('0.00')
        self.balance_due = self.total - self.paid_amount
        
        self.save()
    
    def mark_as_paid(self):
        """Mark invoice as fully paid"""
        from django.utils import timezone
        self.status = 'paid'
        self.paid_amount = self.total
        self.balance_due = Decimal('0.00')
        self.paid_at = timezone.now()
        self.save()


class InvoiceLine(models.Model):
    """
    Individual line items on an invoice.
    
    Business Use: Itemized billing for transparency.
    Shows: Product name, rental period, quantity, rate, total
    """
    
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='invoice_lines',
        help_text="Parent invoice document"
    )
    
    # Product/service description
    description = models.CharField(
        max_length=500,
        help_text="Line item description (e.g., 'Canon EOS R5 Rental (Jan 15-20, 2026)')"
    )
    
    # Optional: Link to original order line
    rental_order_line = models.ForeignKey(
        'rentals.RentalOrderLine',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='invoice_lines',
        help_text="Source order line (if applicable)"
    )
    
    # Quantity and pricing
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0)],
        help_text="Quantity (units or days)"
    )
    
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per unit"
    )
    
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="quantity × unit_price"
    )
    
    # Tax applicability
    is_taxable = models.BooleanField(
        default=True,
        help_text="Should GST be applied to this line"
    )
    
    # HSN/SAC code for GST compliance
    hsn_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="HSN code for goods / SAC for services (GST requirement)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'invoice_lines'
        verbose_name = 'Invoice Line'
        verbose_name_plural = 'Invoice Lines'
        ordering = ['invoice', 'id']
    
    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.description}"
    
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


class Payment(models.Model):
    """
    Payment transaction record linking payments to invoices.
    
    Business Use: Tracks money received from customers.
    Supports partial payments, multiple payment methods, and reconciliation.
    Updates invoice paid_amount and status automatically.
    """
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Net Banking'),
        ('cheque', 'Cheque'),
        ('razorpay', 'Razorpay'),
        ('stripe', 'Stripe'),
        ('other', 'Other'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),           # Payment initiated, awaiting confirmation
        ('processing', 'Processing'),     # Payment gateway processing
        ('success', 'Success'),           # Payment confirmed
        ('failed', 'Failed'),             # Payment failed
        ('refunded', 'Refunded'),         # Payment reversed
    ]
    
    # Document identification
    payment_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Auto-generated payment ID (e.g., PAY-2026-0001)"
    )
    
    # Link to invoice
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Invoice being paid"
    )
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments_made',
        limit_choices_to={'role': 'customer'},
        help_text="Customer making the payment"
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Payment amount"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        help_text="How customer paid"
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        help_text="Payment confirmation status"
    )
    
    payment_date = models.DateTimeField(
        help_text="When payment was made"
    )
    
    # Payment gateway details
    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Payment gateway transaction reference (Encrypted)"
    )
    
    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw payment gateway response (for debugging/reconciliation)"
    )
    
    # Bank details (for cheque/bank transfer)
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bank name for cheque/transfer payments"
    )
    
    cheque_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Cheque number if payment method is cheque (Encrypted)"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Payment notes or reference information"
    )
    
    # Refund tracking
    is_refund = models.BooleanField(
        default=False,
        help_text="Is this a refund transaction?"
    )
    
    refund_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for refund"
    )
    
    original_payment = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='refunds',
        help_text="Original payment being refunded"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When payment was confirmed/failed"
    )
    
    class Meta:
        db_table = 'payments'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['invoice', 'payment_status']),
            models.Index(fields=['customer', 'payment_status']),
            models.Index(fields=['payment_number']),
            models.Index(fields=['transaction_id']),
        ]
    
    def __str__(self):
        return f"{self.payment_number} - ₹{self.amount} - {self.payment_method}"
    
    def process_payment(self):
        """
        Process successful payment and update invoice.
        Business Logic: Update invoice paid_amount, recalculate balance, update status
        """
        from django.utils import timezone
        
        if self.payment_status == 'success' and not self.processed_at:
            # Update invoice
            invoice = self.invoice
            invoice.paid_amount += self.amount
            invoice.balance_due = invoice.total - invoice.paid_amount
            
            # Update invoice status
            if invoice.balance_due <= Decimal('0.00'):
                invoice.status = 'paid'
                invoice.paid_at = timezone.now()
            elif invoice.paid_amount > Decimal('0.00'):
                invoice.status = 'partially_paid'
            
            invoice.save()
            
            # Mark payment as processed
            self.processed_at = timezone.now()
            self.save()
