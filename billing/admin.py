from django.contrib import admin
from django.utils.html import format_html
from .models import Invoice, InvoiceLine, Payment


class InvoiceLineInline(admin.TabularInline):
    """
    Inline admin for invoice line items.
    Business Use: Add/edit invoice items directly within invoice form.
    """
    model = InvoiceLine
    extra = 1
    fields = (
        'description', 'rental_order_line', 'quantity',
        'unit_price', 'line_total', 'is_taxable', 'hsn_code'
    )
    readonly_fields = ('line_total',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """
    Admin for invoices with GST compliance.
    Business Use: Generate and manage customer billing documents.
    """
    
    list_display = (
        'invoice_number', 'billing_name', 'vendor',
        'invoice_date', 'due_date', 'total', 'paid_amount',
        'balance_due', 'get_status_badge'
    )
    
    list_filter = (
        'status', 'payment_terms', 'is_intrastate',
        'invoice_date', 'due_date', 'vendor'
    )
    
    search_fields = (
        'invoice_number', 'billing_name', 'billing_gstin',
        'customer__email', 'rental_order__order_number'
    )
    
    readonly_fields = (
        'invoice_number', 'rental_order', 'customer',
        'subtotal', 'cgst_amount', 'sgst_amount', 'igst_amount',
        'tax_amount', 'total', 'paid_amount', 'balance_due',
        'created_at', 'updated_at', 'sent_at', 'paid_at'
    )
    
    inlines = [InvoiceLineInline]
    
    fieldsets = (
        ('Invoice Information', {
            'fields': (
                'invoice_number', 'rental_order', 'customer', 'vendor', 'status'
            )
        }),
        ('Dates & Terms', {
            'fields': ('invoice_date', 'due_date', 'payment_terms')
        }),
        ('Billing Details', {
            'fields': (
                'billing_name', 'billing_gstin', 'billing_address', 'billing_state'
            )
        }),
        ('Vendor Details', {
            'fields': (
                'vendor_name', 'vendor_gstin', 'vendor_address', 'vendor_state'
            ),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': (
                'subtotal', 'discount_amount', 'late_fee',
                'damage_charges', 'other_charges'
            )
        }),
        ('GST Calculation', {
            'fields': (
                'is_intrastate', 'cgst_rate', 'sgst_rate', 'igst_rate',
                'cgst_amount', 'sgst_amount', 'igst_amount', 'tax_amount'
            )
        }),
        ('Totals', {
            'fields': ('total', 'paid_amount', 'balance_due')
        }),
        ('Deposit', {
            'fields': ('deposit_collected', 'deposit_refunded'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes', 'customer_notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'sent_at', 'paid_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['send_invoices', 'mark_as_paid', 'calculate_gst']
    
    def get_status_badge(self, obj):
        """Display color-coded status badge"""
        colors = {
            'draft': 'gray',
            'sent': 'blue',
            'partially_paid': 'orange',
            'paid': 'green',
            'overdue': 'red',
            'cancelled': 'black'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="padding: 3px 10px; background-color: {}; color: white; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def send_invoices(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='draft').update(status='sent', sent_at=timezone.now())
        self.message_user(request, f'{updated} invoice(s) sent to customers.')
    send_invoices.short_description = 'Send invoices to customers'
    
    def mark_as_paid(self, request, queryset):
        for invoice in queryset:
            invoice.mark_as_paid()
        self.message_user(request, f'{queryset.count()} invoice(s) marked as paid.')
    mark_as_paid.short_description = 'Mark as paid'
    
    def calculate_gst(self, request, queryset):
        for invoice in queryset:
            invoice.calculate_totals()
        self.message_user(request, f'GST recalculated for {queryset.count()} invoice(s).')
    calculate_gst.short_description = 'Recalculate GST & totals'
    
    def get_queryset(self, request):
        """Filter invoices based on user role"""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser or request.user.is_admin_role():
            return qs
        
        if request.user.is_vendor():
            return qs.filter(vendor=request.user)
        
        if request.user.is_customer():
            return qs.filter(customer=request.user)
        
        return qs.none()


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    """Standalone admin for invoice lines"""
    
    list_display = (
        'get_invoice_number', 'description', 'quantity',
        'unit_price', 'line_total', 'is_taxable', 'hsn_code'
    )
    
    list_filter = ('is_taxable', 'created_at')
    
    search_fields = ('description', 'invoice__invoice_number', 'hsn_code')
    
    readonly_fields = ('line_total', 'created_at')
    
    def get_invoice_number(self, obj):
        return obj.invoice.invoice_number
    get_invoice_number.short_description = 'Invoice'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Admin for payment transactions.
    Business Use: Track customer payments and reconcile with invoices.
    """
    
    list_display = (
        'payment_number', 'get_invoice_number', 'customer',
        'amount', 'payment_method', 'get_status_badge',
        'payment_date', 'is_refund'
    )
    
    list_filter = (
        'payment_status', 'payment_method', 'is_refund',
        'payment_date', 'created_at'
    )
    
    search_fields = (
        'payment_number', 'invoice__invoice_number',
        'customer__email', 'transaction_id', 'cheque_number'
    )
    
    readonly_fields = (
        'payment_number', 'invoice', 'customer',
        'processed_at', 'created_at', 'updated_at'
    )
    
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'payment_number', 'invoice', 'customer',
                'amount', 'payment_method', 'payment_status', 'payment_date'
            )
        }),
        ('Gateway Details', {
            'fields': ('transaction_id', 'gateway_response'),
            'classes': ('collapse',)
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'cheque_number'),
            'classes': ('collapse',)
        }),
        ('Refund', {
            'fields': ('is_refund', 'refund_reason', 'original_payment'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['process_successful_payments', 'mark_as_failed']
    
    def get_invoice_number(self, obj):
        return obj.invoice.invoice_number
    get_invoice_number.short_description = 'Invoice'
    
    def get_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'success': 'green',
            'failed': 'red',
            'refunded': 'purple'
        }
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="padding: 3px 10px; background-color: {}; color: white; border-radius: 3px;">{}</span>',
            color, obj.get_payment_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def process_successful_payments(self, request, queryset):
        count = 0
        for payment in queryset.filter(payment_status='pending'):
            payment.payment_status = 'success'
            payment.save()
            payment.process_payment()
            count += 1
        self.message_user(request, f'{count} payment(s) processed successfully.')
    process_successful_payments.short_description = 'Process as successful'
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.filter(payment_status='pending').update(payment_status='failed')
        self.message_user(request, f'{updated} payment(s) marked as failed.')
    mark_as_failed.short_description = 'Mark as failed'
