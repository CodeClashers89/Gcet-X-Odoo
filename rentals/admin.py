from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Quotation, QuotationLine, RentalOrder, RentalOrderLine,
    Reservation, Pickup, Return, ApprovalRequest
)


class QuotationLineInline(admin.TabularInline):
    """
    Inline admin for quotation line items.
    Business Use: Add/edit products in quotation directly from quotation form.
    """
    model = QuotationLine
    extra = 1
    fields = (
        'product', 'product_variant', 'quantity',
        'rental_start_date', 'rental_end_date',
        'unit_price', 'line_total'
    )
    readonly_fields = ('line_total',)


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    """
    Admin for rental quotations.
    Business Use: Manage price proposals before order confirmation.
    """
    
    list_display = (
        'quotation_number', 'customer', 'get_status_badge',
        'subtotal', 'total', 'valid_until', 'created_at'
    )
    
    list_filter = ('status', 'created_at', 'valid_until')
    
    search_fields = (
        'quotation_number', 'customer__email',
        'customer__first_name', 'customer__last_name'
    )
    
    readonly_fields = (
        'quotation_number', 'subtotal', 'tax_amount', 'total',
        'created_at', 'updated_at', 'confirmed_at'
    )
    
    inlines = [QuotationLineInline]
    
    fieldsets = (
        ('Quotation Details', {
            'fields': ('quotation_number', 'customer', 'status', 'valid_until')
        }),
        ('Pricing Summary', {
            'fields': ('subtotal', 'discount_amount', 'tax_amount', 'total')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'confirmed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_sent', 'mark_as_confirmed', 'cancel_quotations']
    
    def get_status_badge(self, obj):
        """Display color-coded status badge"""
        colors = {
            'draft': 'gray',
            'sent': 'blue',
            'confirmed': 'green',
            'cancelled': 'red',
            'expired': 'orange'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="padding: 3px 10px; background-color: {}; color: white; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def mark_as_sent(self, request, queryset):
        updated = queryset.filter(status='draft').update(status='sent')
        self.message_user(request, f'{updated} quotation(s) marked as sent.')
    mark_as_sent.short_description = 'Mark as sent'
    
    def mark_as_confirmed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='sent').update(status='confirmed', confirmed_at=timezone.now())
        self.message_user(request, f'{updated} quotation(s) confirmed.')
    mark_as_confirmed.short_description = 'Confirm quotations'
    
    def cancel_quotations(self, request, queryset):
        updated = queryset.exclude(status__in=['confirmed', 'cancelled']).update(status='cancelled')
        self.message_user(request, f'{updated} quotation(s) cancelled.')
    cancel_quotations.short_description = 'Cancel quotations'


class RentalOrderLineInline(admin.TabularInline):
    """
    Inline admin for rental order line items.
    Business Use: Manage rented items within order.
    """
    model = RentalOrderLine
    extra = 0
    fields = (
        'product', 'product_variant', 'quantity',
        'rental_start_date', 'rental_end_date',
        'actual_pickup_date', 'actual_return_date',
        'unit_price', 'line_total', 'late_fee_charged'
    )
    readonly_fields = ('line_total', 'late_fee_charged')


@admin.register(RentalOrder)
class RentalOrderAdmin(admin.ModelAdmin):
    """
    Admin for rental orders (confirmed rentals).
    Business Use: Core rental transaction management.
    """
    
    list_display = (
        'order_number', 'customer', 'vendor', 'get_status_badge',
        'total', 'paid_amount', 'get_payment_status', 'created_at'
    )
    
    list_filter = ('status', 'vendor', 'created_at', 'confirmed_at')
    
    search_fields = (
        'order_number', 'customer__email', 'vendor__email',
        'customer__first_name', 'customer__last_name'
    )
    
    readonly_fields = (
        'order_number', 'quotation', 'subtotal', 'tax_amount',
        'late_fee', 'total', 'created_at', 'updated_at',
        'confirmed_at', 'completed_at'
    )
    
    inlines = [RentalOrderLineInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'quotation', 'customer', 'vendor', 'status')
        }),
        ('Addresses', {
            'fields': ('delivery_address', 'billing_address')
        }),
        ('Pricing', {
            'fields': (
                'subtotal', 'discount_amount', 'tax_amount',
                'late_fee', 'total'
            )
        }),
        ('Payment Tracking', {
            'fields': ('deposit_amount', 'paid_amount')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['confirm_orders', 'mark_in_progress', 'mark_completed']
    
    def get_status_badge(self, obj):
        """Display color-coded status badge"""
        colors = {
            'draft': 'gray',
            'confirmed': 'blue',
            'in_progress': 'orange',
            'completed': 'green',
            'cancelled': 'red',
            'invoiced': 'purple'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="padding: 3px 10px; background-color: {}; color: white; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def get_payment_status(self, obj):
        """Display payment completion status"""
        if obj.is_payment_complete():
            return format_html('<span style="color: green;">✓ Paid</span>')
        elif obj.paid_amount > 0:
            return format_html('<span style="color: orange;">Partial</span>')
        else:
            return format_html('<span style="color: red;">Unpaid</span>')
    get_payment_status.short_description = 'Payment'
    
    def confirm_orders(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='draft').update(status='confirmed', confirmed_at=timezone.now())
        self.message_user(request, f'{updated} order(s) confirmed.')
    confirm_orders.short_description = 'Confirm orders'
    
    def mark_in_progress(self, request, queryset):
        updated = queryset.filter(status='confirmed').update(status='in_progress')
        self.message_user(request, f'{updated} order(s) marked as in progress.')
    mark_in_progress.short_description = 'Mark as in progress'
    
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='in_progress').update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'{updated} order(s) completed.')
    mark_completed.short_description = 'Mark as completed'
    
    def get_queryset(self, request):
        """
        Filter orders based on user role.
        Business Logic: Vendors only see their own orders.
        """
        qs = super().get_queryset(request)
        
        if request.user.is_superuser or request.user.is_admin_role():
            return qs
        
        if request.user.is_vendor():
            return qs.filter(vendor=request.user)
        
        if request.user.is_customer():
            return qs.filter(customer=request.user)
        
        return qs.none()


@admin.register(RentalOrderLine)
class RentalOrderLineAdmin(admin.ModelAdmin):
    """
    Standalone admin for order line items.
    Business Use: Detailed view of individual rented items.
    """
    
    list_display = (
        'get_order_number', 'product', 'quantity',
        'rental_start_date', 'rental_end_date',
        'actual_return_date', 'is_late_return', 'late_fee_charged'
    )
    
    list_filter = ('is_late_return', 'rental_start_date', 'rental_end_date')
    
    search_fields = (
        'rental_order__order_number', 'product__name',
        'rental_order__customer__email'
    )
    
    readonly_fields = ('line_total', 'late_fee_charged', 'created_at', 'updated_at')
    
    def get_order_number(self, obj):
        return obj.rental_order.order_number
    get_order_number.short_description = 'Order'


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """
    Admin for inventory reservations.
    Business Use: CRITICAL - prevents double-booking by blocking inventory.
    """
    
    list_display = (
        'get_order_number', 'product', 'product_variant',
        'quantity', 'rental_start_date', 'rental_end_date',
        'get_status_badge', 'created_at'
    )
    
    list_filter = ('status', 'rental_start_date', 'rental_end_date', 'created_at')
    
    search_fields = (
        'rental_order_line__rental_order__order_number',
        'product__name', 'product_variant__variant_name'
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Reservation Details', {
            'fields': ('rental_order_line', 'product', 'product_variant', 'quantity', 'status')
        }),
        ('Reservation Period', {
            'fields': ('rental_start_date', 'rental_end_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_order_number(self, obj):
        return obj.rental_order_line.rental_order.order_number
    get_order_number.short_description = 'Order'
    
    def get_status_badge(self, obj):
        colors = {
            'confirmed': 'blue',
            'active': 'orange',
            'completed': 'green',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="padding: 3px 10px; background-color: {}; color: white; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'


@admin.register(Pickup)
class PickupAdmin(admin.ModelAdmin):
    """
    Admin for pickup documents.
    Business Use: Track item handover to customers.
    """
    
    list_display = (
        'pickup_number', 'get_order_number', 'get_customer',
        'scheduled_pickup_date', 'actual_pickup_date',
        'get_status_badge', 'items_checked'
    )
    
    list_filter = ('status', 'scheduled_pickup_date', 'items_checked', 'customer_id_verified')
    
    search_fields = (
        'pickup_number', 'rental_order__order_number',
        'rental_order__customer__email'
    )
    
    readonly_fields = ('pickup_number', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Pickup Information', {
            'fields': ('pickup_number', 'rental_order', 'status')
        }),
        ('Schedule', {
            'fields': ('scheduled_pickup_date', 'actual_pickup_date')
        }),
        ('Verification', {
            'fields': (
                'handed_over_by', 'items_checked',
                'customer_id_verified', 'pickup_notes'
            )
        }),
        ('Digital Signature', {
            'fields': ('customer_signature',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_completed']
    
    def get_order_number(self, obj):
        return obj.rental_order.order_number
    get_order_number.short_description = 'Order'
    
    def get_customer(self, obj):
        return obj.rental_order.customer.get_full_name()
    get_customer.short_description = 'Customer'
    
    def get_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'in_progress': 'blue',
            'completed': 'green',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="padding: 3px 10px; background-color: {}; color: white; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for pickup in queryset:
            if pickup.status != 'completed':
                pickup.status = 'completed'
                pickup.actual_pickup_date = timezone.now()
                pickup.save()
                updated += 1
        self.message_user(request, f'{updated} pickup(s) marked as completed.')
    mark_completed.short_description = 'Mark pickups as completed'


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    """
    Admin for return documents.
    Business Use: Track item returns and calculate late fees.
    """
    
    list_display = (
        'return_number', 'get_order_number', 'get_customer',
        'scheduled_return_date', 'actual_return_date',
        'is_late_return', 'late_fee_charged', 'get_status_badge'
    )
    
    list_filter = (
        'status', 'is_late_return', 'items_damaged',
        'all_items_returned', 'scheduled_return_date'
    )
    
    search_fields = (
        'return_number', 'rental_order__order_number',
        'rental_order__customer__email'
    )
    
    readonly_fields = (
        'return_number', 'late_fee_charged',
        'created_at', 'updated_at'
    )
    
    fieldsets = (
        ('Return Information', {
            'fields': ('return_number', 'rental_order', 'status')
        }),
        ('Schedule', {
            'fields': ('scheduled_return_date', 'actual_return_date')
        }),
        ('Inspection', {
            'fields': (
                'received_by', 'all_items_returned',
                'items_damaged', 'damage_description', 'damage_cost'
            )
        }),
        ('Late Return', {
            'fields': ('is_late_return', 'late_days', 'late_fee_charged')
        }),
        ('Notes & Signature', {
            'fields': ('return_notes', 'customer_signature'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['process_returns']
    
    def get_order_number(self, obj):
        return obj.rental_order.order_number
    get_order_number.short_description = 'Order'
    
    def get_customer(self, obj):
        return obj.rental_order.customer.get_full_name()
    get_customer.short_description = 'Customer'
    
    def get_status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'in_progress': 'blue',
            'completed': 'green',
            'partial': 'yellow',
            'damaged': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="padding: 3px 10px; background-color: {}; color: white; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    
    def process_returns(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for return_doc in queryset:
            if return_doc.status not in ['completed', 'damaged']:
                return_doc.actual_return_date = timezone.now()
                return_doc.calculate_late_fee()
                return_doc.status = 'completed'
                return_doc.save()
                updated += 1
        self.message_user(request, f'{updated} return(s) processed.')
    process_returns.short_description = 'Process returns'


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    """
    Admin for approval requests (Phase 8).
    Business Use: Track quotations and orders requiring approval.
    """
    
    list_display = (
        'request_number', 'request_type', 'get_document',
        'approval_amount', 'status_badge', 'requested_by',
        'approved_by', 'created_at'
    )
    
    list_filter = ('request_type', 'status', 'created_at')
    
    search_fields = (
        'request_number', 'quotation__quotation_number',
        'rental_order__order_number', 'requested_by__email'
    )
    
    readonly_fields = (
        'request_number', 'created_at', 'updated_at', 'approved_at',
        'quotation', 'rental_order'
    )
    
    fieldsets = (
        ('Request Information', {
            'fields': ('request_number', 'request_type', 'status')
        }),
        ('Document Reference', {
            'fields': ('quotation', 'rental_order', 'approval_amount')
        }),
        ('Approval Details', {
            'fields': ('requested_by', 'approved_by', 'approval_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'approved_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_requests', 'reject_requests']
    
    def get_document(self, obj):
        if obj.quotation:
            return f"QT-{obj.quotation.quotation_number}"
        elif obj.rental_order:
            return f"RO-{obj.rental_order.order_number}"
        return "-"
    get_document.short_description = 'Document'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'FFA500',
            'approved': '28A745',
            'rejected': 'DC3545'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="padding: 3px 10px; background-color: #{}; color: white; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def approve_requests(self, request, queryset):
        updated = 0
        for approval in queryset.filter(status='pending'):
            approval.approve(request.user, "Approved via admin panel")
            updated += 1
        self.message_user(request, f'{updated} approval(s) approved.')
    approve_requests.short_description = 'Approve selected requests'
    
    def reject_requests(self, request, queryset):
        updated = 0
        for approval in queryset.filter(status='pending'):
            approval.reject(request.user, "Rejected via admin panel")
            updated += 1
        self.message_user(request, f'{updated} approval(s) rejected.')
    reject_requests.short_description = 'Reject selected requests'
