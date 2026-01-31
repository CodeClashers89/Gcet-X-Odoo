from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
from rentals.pdf_utils import generate_rental_document
from rentals.notifications import notify_invoice_stage
from decimal import Decimal
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from accounts.models import User
from rentals.models import RentalOrder, RentalOrderLine
from billing.models import Invoice, InvoiceLine, Payment
from system_settings.models import SystemConfiguration
from audit.models import AuditLog


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
@require_http_methods(["GET"])
def invoice_list(request):
    """
    List invoices for logged-in user.
    Business Logic:
    - Customers: See invoices for their rental orders
    - Vendors: See invoices for orders of their products
    - Admins: See all invoices
    """
    if request.user.role == 'customer':
        invoices = Invoice.objects.filter(customer=request.user).order_by('-created_at')
    elif request.user.role == 'vendor':
        invoices = Invoice.objects.filter(vendor=request.user).order_by('-created_at')
    elif request.user.is_staff:
        invoices = Invoice.objects.all().order_by('-created_at')
    else:
        return HttpResponseForbidden('You do not have access to invoices.')
    
    # Status filtering
    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status)
    
    return render(request, 'billing/invoice_list.html', {
        'invoices': invoices,
        'status': status,
    })


@login_required
@require_http_methods(["GET"])
def invoice_detail(request, pk):
    """
    View invoice details including line items, taxes, and payment status.
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Permission check
    if request.user.role == 'customer' and invoice.customer != request.user:
        return HttpResponseForbidden('You do not have access to this invoice.')
    elif request.user.role == 'vendor' and invoice.vendor != request.user:
        return HttpResponseForbidden('You do not have access to this invoice.')
    elif not request.user.is_staff and request.user not in [invoice.customer, invoice.vendor]:
        return HttpResponseForbidden('You do not have access to this invoice.')
    
    # Get invoice lines
    lines = invoice.invoice_lines.all()
    
    # Get payments
    payments = invoice.payment_set.filter(is_refund=False).order_by('-payment_date')
    
    return render(request, 'billing/invoice_detail.html', {
        'invoice': invoice,
        'lines': lines,
        'payments': payments,
    })


@login_required
@require_http_methods(["POST"])
def generate_invoice_ajax(request):
    """
    AJAX endpoint to generate invoice from rental order.
    Business Use: When order is completed, auto-generate invoice with all line items.
    
    POST Parameters:
    - rental_order_id: RentalOrder ID to generate invoice for
    
    Response: JSON with invoice_id and success status
    """
    
    try:
        order_id = request.POST.get('rental_order_id')
        if not order_id:
            return JsonResponse({'error': 'Missing rental_order_id'}, status=400)
        
        order = get_object_or_404(RentalOrder, pk=order_id)
        
        # Permission check - only vendor or admin can generate invoice
        if request.user != order.vendor and not request.user.is_staff:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Check if invoice already exists
        existing_invoice = Invoice.objects.filter(rental_order=order).first()
        if existing_invoice:
            return JsonResponse({
                'success': True,
                'invoice_id': existing_invoice.id,
                'message': 'Invoice already exists'
            })
        
        with transaction.atomic():
            # Create invoice
            invoice = Invoice.objects.create(
                invoice_number=f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                rental_order=order,
                customer=order.customer,
                vendor=order.vendor,
                status='draft',
                invoice_date=timezone.now().date(),
                due_date=(timezone.now() + timedelta(days=SystemConfiguration.get_config().payment_due_days)).date(),
                payment_terms='Net 30',
                
                # Billing details
                billing_name=order.customer.get_full_name(),
                billing_gstin=order.customer.customerprofile.gstin if hasattr(order.customer, 'customerprofile') else '',
                billing_address=order.billing_address,
                billing_state='',  # Can be extracted from address if needed
                
                # Vendor details
                vendor_name=order.vendor.get_full_name() if order.vendor else '',
                vendor_gstin=order.vendor.vendorprofile.gstin if order.vendor and hasattr(order.vendor, 'vendorprofile') else '',
                vendor_address=order.delivery_address,
                vendor_state='',
                
                # Financial
                subtotal=order.subtotal,
                discount_amount=order.discount_amount,
                tax_amount=order.tax_amount,
                late_fee=order.late_fee_amount or Decimal('0.00'),
                
                # Deposit
                deposit_collected=order.deposit_amount or Decimal('0.00'),
            )
            
            # Create invoice lines from order lines
            for order_line in order.rental_order_lines.all():
                InvoiceLine.objects.create(
                    invoice=invoice,
                    description=f"{order_line.product.name} ({order_line.rental_start_date.strftime('%d %b %Y')} - {order_line.rental_end_date.strftime('%d %b %Y')})",
                    rental_order_line=order_line,
                    quantity=order_line.quantity,
                    unit_price=order_line.unit_price,
                    line_total=order_line.line_total,
                    is_taxable=True,
                    hsn_code=getattr(order_line.product, 'hsn_code', '998599')
                )
            
            # Add late fees as line item if applicable
            if order.late_fee_amount and order.late_fee_amount > 0:
                InvoiceLine.objects.create(
                    invoice=invoice,
                    description='Late Return Charges',
                    quantity=Decimal('1'),
                    unit_price=order.late_fee_amount,
                    line_total=order.late_fee_amount,
                    is_taxable=True,
                    hsn_code='998599'
                )
            
            # Calculate totals
            invoice.total = invoice.subtotal - invoice.discount_amount + invoice.tax_amount + invoice.late_fee
            invoice.balance_due = invoice.total - invoice.paid_amount
            invoice.save()
            
            # Notify customer with PDF
            notify_invoice_stage(invoice)
            
            # Log invoice generation
            AuditLog.log_action(
                user=request.user,
                action_type='create',
                model_name='Invoice',
                object_id=invoice.id,
                description=f'Invoice generated from order {order.order_number}',
                ip_address=get_client_ip(request),
            )
            
            return JsonResponse({
                'success': True,
                'invoice_id': invoice.id,
                'message': 'Invoice generated successfully'
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["GET"])
def download_invoice_pdf(request, pk):
    """
    Download invoice as PDF.
    Business Use: Generate professional PDF invoice for download/printing.
    """
    
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Permission check
    if request.user.role == 'customer' and invoice.customer != request.user:
        return HttpResponseForbidden('You do not have access to this invoice.')
    elif request.user.role == 'vendor' and invoice.vendor != request.user:
        return HttpResponseForbidden('You do not have access to this invoice.')
    elif not request.user.is_staff and request.user not in [invoice.customer, invoice.vendor]:
        return HttpResponseForbidden('You do not have access to this invoice.')
    
    try:
        pdf_content = generate_rental_document(invoice, doc_type='invoice')
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'
        return response
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_http_methods(["POST"])
def mark_invoice_sent(request, pk):
    """
    Mark invoice as sent to customer.
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Permission check - only vendor or admin
    if request.user != invoice.vendor and not request.user.is_staff:
        return HttpResponseForbidden('You do not have permission to send this invoice.')
    
    try:
        with transaction.atomic():
            invoice.status = 'sent'
            invoice.sent_at = timezone.now()
            invoice.save()
            
            # Log action
            AuditLog.log_action(
                user=request.user,
                action_type='state_change',
                model_name='Invoice',
                object_id=invoice.id,
                field_name='status',
                old_value='draft',
                new_value='sent',
                description='Invoice sent to customer',
                ip_address=get_client_ip(request),
            )
            
            messages.success(request, 'Invoice marked as sent')
            
            # TODO: Send email to customer
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            else:
                return redirect('billing:invoice_detail', pk=invoice.id)
    
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        else:
            return redirect('billing:invoice_detail', pk=invoice.id)


@login_required
@require_http_methods(["POST"])
def record_payment(request, pk):
    """
    Record payment against invoice.
    Business Use: Log payment received from customer.
    
    POST Parameters:
    - amount: Payment amount (required)
    - payment_method: cash, bank_transfer, cheque, card (required)
    - payment_date: Date of payment (optional)
    """
    
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Permission check - only vendor or admin
    if request.user != invoice.vendor and not request.user.is_staff:
        return HttpResponseForbidden('You do not have permission to record payments for this invoice.')
    
    try:
        amount = Decimal(request.POST.get('amount', 0))
        payment_method = request.POST.get('payment_method', 'bank_transfer')
        payment_date_str = request.POST.get('payment_date')
        
        if amount <= 0:
            raise ValueError('Payment amount must be greater than 0')
        
        if amount > invoice.balance_due:
            raise ValueError(f'Payment amount exceeds balance due (₹{invoice.balance_due:,.2f})')
        
        payment_date = timezone.now()
        if payment_date_str:
            try:
                payment_date = datetime.fromisoformat(payment_date_str)
            except ValueError:
                pass
        
        with transaction.atomic():
            # Create payment record
            payment = Payment.objects.create(
                payment_number=f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                invoice=invoice,
                customer=invoice.customer,
                amount=amount,
                payment_method=payment_method,
                payment_status='completed',
                payment_date=payment_date,
            )
            
            # Update invoice
            invoice.paid_amount += amount
            invoice.balance_due -= amount
            
            if invoice.balance_due <= 0:
                invoice.status = 'paid'
                invoice.paid_at = timezone.now()
            else:
                invoice.status = 'partial'
            
            invoice.save()
            
            # Log action
            AuditLog.log_action(
                user=request.user,
                action_type='create',
                model_name='Payment',
                object_id=payment.id,
                description=f'Payment of ₹{amount:,.2f} recorded for invoice {invoice.invoice_number}',
                ip_address=get_client_ip(request),
            )
            
            messages.success(request, f'Payment of ₹{amount:,.2f} recorded successfully')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'paid_amount': float(invoice.paid_amount),
                    'balance_due': float(invoice.balance_due),
                    'status': invoice.status
                })
            else:
                return redirect('billing:invoice_detail', pk=invoice.id)
    
    except ValueError as e:
        messages.error(request, f'Invalid input: {str(e)}')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        else:
            return redirect('billing:invoice_detail', pk=invoice.id)
    except Exception as e:
        messages.error(request, f'Error recording payment: {str(e)}')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        else:
            return redirect('billing:invoice_detail', pk=invoice.id)
