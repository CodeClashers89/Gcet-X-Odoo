from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
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
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0d6efd'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#0d6efd'),
            spaceAfter=10
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 9
        
        # Title
        elements.append(Paragraph('TAX INVOICE', title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Invoice info
        info_data = [
            ['Invoice #', invoice.invoice_number, 'Invoice Date', invoice.invoice_date.strftime('%d %b %Y')],
            ['Order #', invoice.rental_order.order_number if invoice.rental_order else '-', 'Due Date', invoice.due_date.strftime('%d %b %Y')],
        ]
        
        info_table = Table(info_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Bill From / Bill To
        from_to_data = [
            ['BILL FROM', '', 'BILL TO'],
            [
                f"{invoice.vendor_name}\n{invoice.vendor_gstin}\n{invoice.vendor_address}",
                '',
                f"{invoice.billing_name}\n{invoice.billing_gstin}\n{invoice.billing_address}"
            ],
        ]
        
        from_to_table = Table(from_to_data, colWidths=[2.5*inch, 0.5*inch, 2.5*inch])
        from_to_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTWEIGHT', (0, 0), (-1, 0), 'bold'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(from_to_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Line items table
        line_data = [
            ['Description', 'Qty', 'Unit Price', 'Amount'],
        ]
        
        for line in invoice.invoice_lines.all():
            line_data.append([
                line.description,
                str(line.quantity),
                f"₹{line.unit_price:,.2f}",
                f"₹{line.line_total:,.2f}",
            ])
        
        lines_table = Table(line_data, colWidths=[3.5*inch, 0.8*inch, 1.2*inch, 1.2*inch])
        lines_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(lines_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Totals
        totals_data = [
            ['', 'Subtotal', f"₹{invoice.subtotal:,.2f}"],
            ['', 'Discount', f"-₹{invoice.discount_amount:,.2f}"],
            ['', 'Tax (GST)', f"₹{invoice.tax_amount:,.2f}"],
            ['', 'Late Fees', f"₹{invoice.late_fee:,.2f}"],
            ['', 'TOTAL', f"₹{invoice.total:,.2f}"],
        ]
        
        totals_table = Table(totals_data, colWidths=[3.5*inch, 1.2*inch, 1.2*inch])
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Payment info
        if invoice.status == 'paid':
            elements.append(Paragraph(
                f'<b>Payment Status:</b> PAID on {invoice.paid_at.strftime("%d %b %Y")} | Paid Amount: ₹{invoice.paid_amount:,.2f}',
                normal_style
            ))
        else:
            elements.append(Paragraph(
                f'<b>Payment Status:</b> {invoice.status.upper()} | Balance Due: ₹{invoice.balance_due:,.2f}',
                normal_style
            ))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Return PDF
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'
        return response
    
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('billing:invoice_detail', pk=invoice.id)


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
