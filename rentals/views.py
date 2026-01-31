from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone

from accounts.models import User, VendorProfile
from catalog.models import Product, RentalPricing
from rentals.models import Quotation, QuotationLine, RentalOrder, RentalOrderLine, Pickup, Return, Reservation
from billing.models import Invoice
from system_settings.models import SystemConfiguration, LateFeePolicy
from audit.models import AuditLog

from .forms import (
    CreateQuotationForm,
    QuotationLineFormSet,
    SendQuotationForm,
    ConfirmQuotationForm,
    RentalOrderStatusForm,
    PickupScheduleForm,
    PickupCompletionForm,
    ReturnScheduleForm,
    ReturnCompletionForm,
)


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
@require_http_methods(["GET", "POST"])
def create_quotation(request):
    """
    Create new query with line items (customer request).
    Business Flow:
    1. Customer selects products, rental dates, quantities
    2. Form calculates pricing based on RentalPricing
    3. Save query (quotation) in draft status
    4. Vendor reviews and sends quotation to customer
    
    Only customers can create quotations.
    """
    if request.user.role != 'customer':
        return HttpResponseForbidden('Only customers can create queries.')
    
    if request.method == 'POST':
        form = CreateQuotationForm(request.POST)
        formset = QuotationLineFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Create quotation
                    quotation = form.save(commit=False)
                    quotation.customer = request.user
                    quotation.status = 'draft'
                    quotation.quotation_number = f"QT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    quotation.valid_until = timezone.now() + timedelta(
                        days=SystemConfiguration.get_config().quotation_validity_days
                    )
                    quotation.save()
                    
                    # Save line items
                    formset.instance = quotation
                    formset.save()
                    
                    # Calculate totals
                    quotation.calculate_totals()
                    
                    # Log creation
                    AuditLog.log_action(
                        user=request.user,
                        action_type='create',
                        model_instance=quotation,
                        description=f'Quotation created: {quotation.quotation_number}',
                        request=request,
                    )
                    
                    messages.success(
                        request,
                        f'Query {quotation.quotation_number} created successfully!'
                    )
                    return redirect('rentals:quotation_detail', pk=quotation.id)
            
            except Exception as e:
                messages.error(request, f'Failed to create query: {str(e)}')
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
            for formset_error in formset.non_form_errors():
                messages.error(request, formset_error)
    else:
        form = CreateQuotationForm()
        formset = QuotationLineFormSet()
    
    return render(request, 'rentals/create_quotation.html', {
        'form': form,
        'formset': formset,
    })


@login_required
@require_http_methods(["GET"])
def quotation_list(request):
    """
    List quotations for logged-in user.
    Business Logic:
    - Customers: See quotations they created
    - Vendors: Not applicable (vendors see orders, not quotations)
    - Admins: See all quotations
    """
    if request.user.role == 'customer':
        quotations = Quotation.objects.filter(customer=request.user).order_by('-created_at')
    elif request.user.is_staff:
        quotations = Quotation.objects.all().order_by('-created_at')
    else:
        return HttpResponseForbidden('You do not have access to queries.')
    
    # Status filtering
    status = request.GET.get('status')
    if status:
        quotations = quotations.filter(status=status)
    
    return render(request, 'rentals/quotation_list.html', {
        'quotations': quotations,
        'status': status,
    })


@login_required
@require_http_methods(["GET"])
def vendor_query_list(request):
    """
    List customer queries (draft quotations) for vendors.
    Vendors can review and send quotations to customers.
    """
    if request.user.role != 'vendor':
        return HttpResponseForbidden('Only vendors can view queries.')

    quotations = Quotation.objects.filter(
        quotation_lines__product__vendor=request.user
    ).distinct().order_by('-created_at')

    status = request.GET.get('status')
    if status:
        quotations = quotations.filter(status=status)

    return render(request, 'rentals/vendor_query_list.html', {
        'quotations': quotations,
        'status': status,
    })


@login_required
@require_http_methods(["GET", "POST"])
def quotation_detail(request, pk):
    """
    View quotation details and confirm/send.
    Business Flow:
    - Customer views quotation and confirms (converts to order)
    - Vendor sends quotation to customer for review
    - Admin views all quotation details
    """
    quotation = get_object_or_404(Quotation, pk=pk)
    
    # Permission check
    if request.user.role == 'customer' and quotation.customer != request.user:
        return HttpResponseForbidden('You do not have access to this query.')
    elif request.user.role == 'vendor':
        vendor_has_line = quotation.quotation_lines.filter(
            product__vendor=request.user
        ).exists()
        if not vendor_has_line:
            return HttpResponseForbidden('You do not have access to this query.')
    elif not request.user.is_staff and request.user != quotation.customer:
        return HttpResponseForbidden('You do not have access to this query.')
    
    # Get vendor info if exists
    vendor = None
    if quotation.quotation_lines.exists():
        first_line = quotation.quotation_lines.first()
        if first_line.product.vendor:
            vendor = first_line.product.vendor
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm' and request.user.role == 'customer':
            # Customer confirms quotation → creates RentalOrder
            if quotation.status != 'sent':
                messages.error(request, 'This query is not ready for approval yet.')
                return redirect('rentals:quotation_detail', pk=quotation.id)

            if quotation.approval_status == 'pending':
                messages.error(request, 'This query is pending approval and cannot be confirmed yet.')
                return redirect('rentals:quotation_detail', pk=quotation.id)

            form = ConfirmQuotationForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        # Create rental order from quotation
                        rental_order = RentalOrder.objects.create(
                            quotation=quotation,
                            customer=quotation.customer,
                            vendor=vendor,
                            order_number=f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            status='confirmed',
                            delivery_address=form.cleaned_data['delivery_address'],
                            billing_address=form.cleaned_data['billing_address'],
                            deposit_amount=form.cleaned_data.get('deposit_amount') or 0,
                        )
                        
                        # Copy quotation lines to order lines
                        for qt_line in quotation.quotation_lines.all():
                            RentalOrderLine.objects.create(
                                rental_order=rental_order,
                                product=qt_line.product,
                                product_variant=qt_line.product_variant,
                                rental_start_date=qt_line.rental_start_date,
                                rental_end_date=qt_line.rental_end_date,
                                quantity=qt_line.quantity,
                                unit_price=qt_line.unit_price,
                                line_total=qt_line.line_total,
                            )
                        
                        # Create reservations to block inventory
                        for order_line in rental_order.order_lines.all():
                            for _ in range(order_line.quantity):
                                Reservation.objects.create(
                                    rental_order_line=order_line,
                                    product=order_line.product,
                                    product_variant=order_line.product_variant,
                                    rental_start_date=order_line.rental_start_date,
                                    rental_end_date=order_line.rental_end_date,
                                    status='confirmed',
                                )
                        
                        # Calculate totals
                        rental_order.calculate_totals()
                        
                        # Update quotation status
                        quotation.status = 'confirmed'
                        quotation.confirmed_at = timezone.now()
                        quotation.save()
                        
                        # Log order creation
                        AuditLog.log_action(
                            user=request.user,
                            action_type='state_change',
                            model_instance=rental_order,
                            field_name='status',
                            old_value='NONE',
                            new_value='confirmed',
                            description=f'Query approved, sale order created: {rental_order.order_number}',
                            request=request,
                        )
                        
                        messages.success(
                            request,
                            f'Order {rental_order.order_number} created successfully!'
                        )
                        return redirect('rentals:order_detail', pk=rental_order.id)
                
                except Exception as e:
                    messages.error(request, f'Failed to confirm quotation: {str(e)}')
        
        elif action == 'send' and (request.user.is_staff or request.user.role == 'vendor'):
            # Admin/vendor sends quotation to customer
            form = SendQuotationForm(request.POST)
            if form.is_valid():
                # TODO: Send email via Brevo
                messages.success(request, 'Quotation sent to customer')
                
                # Log sending
                AuditLog.log_action(
                    user=request.user,
                    action_type='state_change',
                    model_instance=quotation,
                    field_name='status',
                    old_value='draft',
                    new_value='sent',
                    description=f'Quotation sent to customer: {quotation.quotation_number}',
                    request=request,
                )
                quotation.status = 'sent'
                
                # Check if approval is required (>= approval threshold from system settings)
                from rentals.models import ApprovalRequest
                
                try:
                    sys_config = SystemConfiguration.objects.first()
                    approval_threshold = sys_config.quotation_approval_threshold if sys_config else 50000
                    
                    if quotation.total >= approval_threshold:
                        # Create approval request
                        quotation.requires_approval = True
                        quotation.approval_status = 'pending'
                        
                        approval_request = ApprovalRequest.objects.create(
                            request_number=f"APR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            request_type='quotation',
                            quotation=quotation,
                            requested_by=request.user,
                            approval_amount=quotation.total,
                        )
                        
                        messages.info(request, f'Quotation exceeds approval threshold (₹{approval_threshold}). Approval required.')
                        AuditLog.log_action(
                            user=request.user,
                            action_type='create',
                            model_instance=approval_request,
                            description=f'Approval request created for quotation {quotation.quotation_number}',
                            request=request,
                        )
                except Exception as e:
                    # If settings don't exist, continue without approval
                    pass
                
                quotation.save()

        elif action == 'decline' and request.user.role == 'customer':
            if quotation.status in ['sent', 'draft']:
                old_status = quotation.status
                quotation.status = 'cancelled'
                quotation.save()

                AuditLog.log_action(
                    user=request.user,
                    action_type='state_change',
                    model_instance=quotation,
                    field_name='status',
                    old_value=old_status,
                    new_value='cancelled',
                    description=f'Query declined: {quotation.quotation_number}',
                    request=request,
                )

                messages.info(request, 'Query declined successfully.')
                return redirect('rentals:quotation_list')

    
    # Prepare forms
    confirm_form = ConfirmQuotationForm() if request.user.role == 'customer' else None
    send_form = SendQuotationForm() if (request.user.is_staff or request.user.role == 'vendor') else None
    
    return render(request, 'rentals/quotation_detail.html', {
        'quotation': quotation,
        'confirm_form': confirm_form,
        'send_form': send_form,
        'vendor': vendor,
    })


@login_required
@require_http_methods(["GET"])
def order_list(request):
    """
    List rental orders for logged-in user.
    Business Logic:
    - Customers: See their orders
    - Vendors: See orders for their products
    - Admins: See all orders
    """
    if request.user.role == 'customer':
        orders = RentalOrder.objects.filter(customer=request.user).order_by('-created_at')
    elif request.user.role == 'vendor':
        # Get vendor's products and find orders
        orders = RentalOrder.objects.filter(
            vendor=request.user
        ).order_by('-created_at')
    elif request.user.is_staff:
        orders = RentalOrder.objects.all().order_by('-created_at')
    else:
        return HttpResponseForbidden('You do not have access to orders.')
    
    # Status filtering
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    return render(request, 'rentals/order_list.html', {
        'orders': orders,
        'status': status,
    })


@login_required
@require_http_methods(["GET", "POST"])
def order_detail(request, pk):
    """
    View rental order details and manage status.
    Business Flow:
    1. Customer views order and payment details
    2. Vendor confirms order, schedules pickup/return
    3. Admin views all order details
    """
    order = get_object_or_404(RentalOrder, pk=pk)
    
    # Permission check
    if request.user.role == 'customer' and order.customer != request.user:
        return HttpResponseForbidden('You do not have access to this order.')
    elif request.user.role == 'vendor' and order.vendor != request.user:
        return HttpResponseForbidden('You do not have access to this order.')
    elif not request.user.is_staff and request.user not in [order.customer, order.vendor]:
        return HttpResponseForbidden('You do not have access to this order.')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'confirm' and request.user == order.vendor:
            # Vendor confirms order
            order.status = 'confirmed'
            order.save()
            messages.success(request, 'Order confirmed')
            AuditLog.log_action(
                user=request.user,
                action_type='state_change',
                model_instance=order,
                field_name='status',
                old_value='draft',
                new_value='confirmed',
                description=f'Order confirmed by vendor',
                request=request,
            )
        
        elif action == 'start' and request.user == order.vendor:
            # Vendor marks order as in progress
            order.status = 'in_progress'
            order.save()
            messages.success(request, 'Order started')
            AuditLog.log_action(
                user=request.user,
                action_type='state_change',
                model_instance=order,
                field_name='status',
                old_value='confirmed',
                new_value='in_progress',
                description=f'Order status changed to in progress',
                request=request,
            )
        
        elif action == 'complete' and request.user == order.vendor:
            # Vendor marks order as completed
            order.status = 'completed'
            order.save()
            messages.success(request, 'Order completed')
            AuditLog.log_action(
                user=request.user,
                action_type='state_change',
                model_instance=order,
                field_name='status',
                old_value='in_progress',
                new_value='completed',
                description=f'Order marked as completed',
                request=request,
            )
    
    # Get related pickup/return
    pickup = order.pickup if hasattr(order, 'pickup') else None
    return_record = order.return_doc if hasattr(order, 'return_doc') else None
    
    # Get invoice if exists
    invoice = order.invoices.first()
    
    return render(request, 'rentals/order_detail.html', {
        'order': order,
        'pickup': pickup,
        'return_record': return_record,
        'invoice': invoice,
    })


@login_required
@require_http_methods(["GET", "POST"])
def schedule_pickup(request, order_id):
    """
    Schedule pickup of rental items.
    Business Use: Vendor coordinates when items will be picked up.
    """
    order = get_object_or_404(RentalOrder, pk=order_id)
    
    # Permission check - only vendor can schedule
    if request.user != order.vendor:
        return HttpResponseForbidden('Only vendor can schedule pickups.')
    
    if request.method == 'POST':
        form = PickupScheduleForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create pickup record
                    pickup = Pickup.objects.create(
                        rental_order=order,
                        pickup_number=f"PU-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        scheduled_pickup_date=form.cleaned_data['scheduled_pickup_date'],
                        pickup_notes=form.cleaned_data.get('pickup_notes', ''),
                    )
                    
                    AuditLog.log_action(
                        user=request.user,
                        action_type='create',
                        model_instance=pickup,
                        description=f'Pickup scheduled: {pickup.pickup_number}',
                        request=request,
                    )
                    
                    messages.success(request, 'Pickup scheduled successfully')
                    return redirect('rentals:order_detail', pk=order.id)
            
            except Exception as e:
                messages.error(request, f'Failed to schedule pickup: {str(e)}')
    else:
        form = PickupScheduleForm()
    
    return render(request, 'rentals/schedule_pickup.html', {
        'order': order,
        'form': form,
    })


@login_required
@require_http_methods(["POST"])
def complete_pickup(request, order_id):
    """
    Record pickup completion.
    Business Use: Confirm items handed to customer.
    """
    order = get_object_or_404(RentalOrder, pk=order_id)
    
    if request.user != order.vendor:
        return HttpResponseForbidden('Only vendor can complete pickups.')
    
    form = PickupCompletionForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                pickup = order.pickup if hasattr(order, 'pickup') else None
                if not pickup:
                    pickup = Pickup.objects.create(
                        rental_order=order,
                        pickup_number=f"PU-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    )
                
                pickup.actual_pickup_date = form.cleaned_data['actual_pickup_date']
                pickup.items_checked = form.cleaned_data.get('items_checked', False)
                pickup.customer_id_verified = form.cleaned_data.get('customer_id_verified', False)
                pickup.pickup_notes = form.cleaned_data.get('pickup_notes', '')
                pickup.save()
                
                AuditLog.log_action(
                    user=request.user,
                    action_type='update',
                    model_instance=pickup,
                    description='Pickup completed',
                    request=request,
                )
                
                messages.success(request, 'Pickup recorded')
                return redirect('rentals:order_detail', pk=order.id)
        
        except Exception as e:
            messages.error(request, f'Failed to complete pickup: {str(e)}')
    
    return render(request, 'rentals/complete_pickup.html', {
        'order': order,
        'form': form,
    })


@login_required
@require_http_methods(["GET", "POST"])
def schedule_return(request, order_id):
    """
    Schedule return of rental items.
    Business Use: Plan item collection after rental period.
    """
    order = get_object_or_404(RentalOrder, pk=order_id)
    
    if request.user != order.vendor:
        return HttpResponseForbidden('Only vendor can schedule returns.')
    
    if request.method == 'POST':
        form = ReturnScheduleForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    return_record = Return.objects.create(
                        rental_order=order,
                        return_number=f"RET-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        scheduled_return_date=form.cleaned_data['scheduled_return_date'],
                    )
                    
                    AuditLog.log_action(
                        user=request.user,
                        action_type='create',
                        model_instance=return_record,
                        description=f'Return scheduled: {return_record.return_number}',
                        request=request,
                    )
                    
                    messages.success(request, 'Return scheduled successfully')
                    return redirect('rentals:order_detail', pk=order.id)
            
            except Exception as e:
                messages.error(request, f'Failed to schedule return: {str(e)}')
    else:
        form = ReturnScheduleForm()
    
    return render(request, 'rentals/schedule_return.html', {
        'order': order,
        'form': form,
    })


@login_required
@require_http_methods(["POST"])
def complete_return(request, order_id):
    """
    Record return completion with damage assessment.
    Business Use: Process returned items, calculate late fees.
    """
    order = get_object_or_404(RentalOrder, pk=order_id)
    
    if request.user != order.vendor:
        return HttpResponseForbidden('Only vendor can complete returns.')
    
    form = ReturnCompletionForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                return_record = order.return_doc if hasattr(order, 'return_doc') else None
                if not return_record:
                    return_record = Return.objects.create(
                        rental_order=order,
                        return_number=f"RET-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    )
                
                return_record.actual_return_date = form.cleaned_data['actual_return_date']
                return_record.all_items_returned = form.cleaned_data.get('all_items_returned', False)
                return_record.items_damaged = form.cleaned_data.get('items_damaged', False)
                return_record.damage_description = form.cleaned_data.get('damage_description', '')
                return_record.damage_cost = form.cleaned_data.get('damage_cost') or 0
                
                # Calculate late fees
                for order_line in order.order_lines.all():
                    if return_record.actual_return_date > order_line.rental_end_date:
                        order_line.is_late_return = True
                        order_line.late_days = (return_record.actual_return_date - order_line.rental_end_date).days
                        order_line.calculate_late_fee()
                        order_line.save()
                
                return_record.save()
                order.calculate_totals()
                
                # Complete reservations
                Reservation.objects.filter(
                    rental_order_line__rental_order=order,
                    status__in=['confirmed', 'active']
                ).update(status='completed')
                
                AuditLog.log_action(
                    user=request.user,
                    action_type='update',
                    model_instance=return_record,
                    description='Return completed, late fees calculated',
                    request=request,
                )
                
                messages.success(request, 'Return recorded and late fees calculated')
                return redirect('rentals:order_detail', pk=order.id)
        
        except Exception as e:
            messages.error(request, f'Failed to complete return: {str(e)}')
    
    return render(request, 'rentals/complete_return.html', {
        'order': order,
        'form': form,
    })


@require_http_methods(["GET"])
def get_variants_ajax(request):
    """
    AJAX endpoint to get product variants.
    Used when product is selected in quotation form.
    """
    product_id = request.GET.get('product_id')
    if not product_id:
        return JsonResponse([])
    
    from catalog.models import ProductVariant
    variants = ProductVariant.objects.filter(product_id=product_id).values('id', 'variant_name')
    return JsonResponse(list(variants), safe=False)


@require_http_methods(["GET"])
def get_pricing_ajax(request):
    """
    AJAX endpoint to calculate rental price.
    Used when rental dates are selected.
    """
    product_id = request.GET.get('product_id')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if not all([product_id, start_date_str, end_date_str]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)
        product = Product.objects.get(id=product_id)
        
        # Find applicable pricing
        duration_days = (end_date - start_date).days
        pricing = RentalPricing.objects.filter(
            product=product,
            duration_type='daily',
            is_active=True
        ).first()
        
        if not pricing:
            return JsonResponse({'error': 'No pricing available'}, status=404)
        
        unit_price = pricing.get_effective_price()
        total_price = unit_price * duration_days
        
        return JsonResponse({
            'unit_price': float(unit_price),
            'duration_days': duration_days,
            'total_price': float(total_price),
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =====================================================================
# APPROVAL WORKFLOW VIEWS (Phase 8)
# =====================================================================

@login_required
@require_http_methods(["GET"])
def approval_list(request):
    """
    List all pending approval requests.
    
    Business Flow:
    - Admin/Vendor sees pending quotations and orders requiring approval
    - Filters by status, type, amount
    - Quick approve/reject actions
    - Audit logging for compliance
    
    RBAC: Only admin/vendor can approve
    """
    # Check permission - only admin can approve quotations/orders
    if request.user.role not in ['admin', 'vendor']:
        return HttpResponseForbidden("You don't have permission to view approvals")
    
    # Get all pending approvals
    from rentals.models import ApprovalRequest
    
    status_filter = request.GET.get('status', 'pending')
    request_type_filter = request.GET.get('type', '')
    amount_min = request.GET.get('amount_min', '')
    amount_max = request.GET.get('amount_max', '')
    
    approvals = ApprovalRequest.objects.all()
    
    # Filter by status
    if status_filter in ['pending', 'approved', 'rejected']:
        approvals = approvals.filter(status=status_filter)
    
    # Filter by request type
    if request_type_filter in ['quotation', 'order']:
        approvals = approvals.filter(request_type=request_type_filter)
    
    # Filter by amount
    if amount_min:
        try:
            approvals = approvals.filter(approval_amount__gte=float(amount_min))
        except ValueError:
            pass
    
    if amount_max:
        try:
            approvals = approvals.filter(approval_amount__lte=float(amount_max))
        except ValueError:
            pass
    
    # Admin sees all, vendor sees only their own quotations' approvals
    if request.user.role == 'vendor':
        approvals = approvals.filter(
            quotation__customer__vendorprofile__user=request.user
        ) | approvals.filter(
            rental_order__vendor=request.user
        )
    
    approvals = approvals.select_related(
        'quotation', 'rental_order', 'requested_by', 'approved_by'
    ).order_by('-created_at')
    
    context = {
        'approvals': approvals,
        'current_status': status_filter,
        'current_type': request_type_filter,
        'current_amount_min': amount_min,
        'current_amount_max': amount_max,
    }
    
    return render(request, 'rentals/approval_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def approval_detail(request, approval_id):
    """
    View and act on a specific approval request.
    
    Business Flow:
    - Display full quotation/order details
    - Show approval history
    - Allow approve/reject with notes
    - Update document status and audit log
    
    RBAC: Only admin can approve
    """
    from rentals.models import ApprovalRequest
    
    approval = get_object_or_404(ApprovalRequest, id=approval_id)
    
    # Check permission
    if request.user.role != 'admin':
        if request.user.role == 'vendor' and approval.rental_order and approval.rental_order.vendor == request.user:
            # Vendors can only view their own order approvals
            pass
        else:
            return HttpResponseForbidden("You don't have permission to view this approval")
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            with transaction.atomic():
                approval.approve(request.user, notes)
                
                # Log the action
                AuditLog.objects.create(
                    user=request.user,
                    user_email=request.user.email,
                    user_role=request.user.role,
                    action='state_change',
                    model_name='ApprovalRequest',
                    object_id=approval.id,
                    description=f"Approved {approval.request_type}: {approval.request_number}",
                    changes=f"Status: pending → approved",
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
                
                messages.success(request, f"Approval {approval.request_number} has been approved!")
        
        elif action == 'reject':
            with transaction.atomic():
                approval.reject(request.user, notes)
                
                # Log the action
                AuditLog.objects.create(
                    user=request.user,
                    user_email=request.user.email,
                    user_role=request.user.role,
                    action='state_change',
                    model_name='ApprovalRequest',
                    object_id=approval.id,
                    description=f"Rejected {approval.request_type}: {approval.request_number}",
                    changes=f"Status: pending → rejected",
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
                
                messages.success(request, f"Approval {approval.request_number} has been rejected!")
        
        return redirect('approval_list')
    
    # GET request - show approval detail
    context = {
        'approval': approval,
        'quotation': approval.quotation,
        'rental_order': approval.rental_order,
    }
    
    return render(request, 'rentals/approval_detail.html', context)


@login_required
@require_http_methods(["POST"])
def approve_request(request, approval_id):
    """
    Quick AJAX endpoint to approve a request.
    """
    from rentals.models import ApprovalRequest
    
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        approval = ApprovalRequest.objects.get(id=approval_id)
        notes = request.POST.get('notes', '')
        
        with transaction.atomic():
            approval.approve(request.user, notes)
            
            AuditLog.objects.create(
                user=request.user,
                user_email=request.user.email,
                user_role=request.user.role,
                action='state_change',
                model_name='ApprovalRequest',
                object_id=approval.id,
                description=f"Quick approved {approval.request_type}: {approval.request_number}",
                changes=f"Status: pending → approved",
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Approval {approval.request_number} approved',
            'status': approval.status,
        })
    
    except ApprovalRequest.DoesNotExist:
        return JsonResponse({'error': 'Approval not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def reject_request(request, approval_id):
    """
    Quick AJAX endpoint to reject a request.
    """
    from rentals.models import ApprovalRequest
    
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        approval = ApprovalRequest.objects.get(id=approval_id)
        notes = request.POST.get('notes', '')
        
        with transaction.atomic():
            approval.reject(request.user, notes)
            
            AuditLog.objects.create(
                user=request.user,
                user_email=request.user.email,
                user_role=request.user.role,
                action='state_change',
                model_name='ApprovalRequest',
                object_id=approval.id,
                description=f"Quick rejected {approval.request_type}: {approval.request_number}",
                changes=f"Status: pending → rejected",
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Approval {approval.request_number} rejected',
            'status': approval.status,
        })
    
    except ApprovalRequest.DoesNotExist:
        return JsonResponse({'error': 'Approval not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

