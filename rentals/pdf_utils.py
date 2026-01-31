import os
from io import BytesIO
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from system_settings.models import SystemConfiguration

def generate_rental_document(document_obj, doc_type='quotation'):
    """
    Generates a professional PDF document for Quotations, Rental Orders, or Invoices.
    doc_type: 'quotation', 'order', 'invoice'
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    
    # --- HEADER SECTION (Logos & Basic Info) ---
    config = SystemConfiguration.get_config()
    
    vendor = getattr(document_obj, 'vendor', None)
    if not vendor and hasattr(document_obj, 'quotation_lines'):
        # For quotation, get vendor from first line product
        first_line = document_obj.quotation_lines.first()
        if first_line:
            vendor = first_line.product.vendor
    
    header_data = []
    
    # 1. Logos
    logo_cells = []
    # Website Logo
    if config.company_logo:
        try:
            logo_path = config.company_logo.path
            img = Image(logo_path, width=2.5*cm, height=2.5*cm)
            logo_cells.append(img)
        except:
            logo_cells.append(Paragraph(f"<b>{config.company_name}</b>", styles['Normal']))
    else:
        logo_cells.append(Paragraph(f"<b>{config.company_name}</b>", styles['Normal']))

    # Vendor Logo
    if vendor and hasattr(vendor, 'vendorprofile') and vendor.vendorprofile.vendor_logo:
        try:
            v_logo_path = vendor.vendorprofile.vendor_logo.path
            v_img = Image(v_logo_path, width=2.5*cm, height=2.5*cm)
            logo_cells.append(v_img)
        except:
            logo_cells.append("")
    else:
        logo_cells.append("")

    header_data.append([logo_cells[0], logo_cells[1]])
    
    # 2. Document Title
    titles = {
        'quotation': 'QUOTATION',
        'order': 'RENTAL ORDER',
        'invoice': 'TAX INVOICE'
    }
    header_data.append([Paragraph(f"<font size=18 color='#333333'><b>{titles.get(doc_type)}</b></font>", styles['Normal']), ""])
    
    header_table = Table(header_data, colWidths=[12*cm, 5*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceBefore=0, spaceAfter=0.5*cm))

    # --- CONTACT INFO SECTION ---
    contact_data = []
    
    # Vendor Column
    vendor_info = []
    if vendor and hasattr(vendor, 'vendorprofile'):
        vp = vendor.vendorprofile
        vendor_info.append(f"<b>{vp.company_name}</b>")
        vendor_info.append(vp.business_address)
        vendor_info.append(f"{vp.city}, {vp.state} - {vp.pincode}")
        if vp.gstin:
            vendor_info.append(f"GSTIN: {vp.gstin}")
    else:
        vendor_info.append(f"<b>{config.company_name}</b>")
        vendor_info.append(config.company_address)
    
    # Customer Column
    customer_info = []
    customer = document_obj.customer
    customer_info.append("<b>BILL TO:</b>")
    customer_info.append(customer.get_full_name())
    
    # Case specific address
    if doc_type == 'invoice':
        customer_info.append(getattr(document_obj, 'billing_address', ''))
        if hasattr(document_obj, 'billing_gstin') and document_obj.billing_gstin:
            customer_info.append(f"GSTIN: {document_obj.billing_gstin}")
    else:
        if hasattr(customer, 'customerprofile'):
            customer_info.append(customer.customerprofile.business_address)
        else:
            customer_info.append(getattr(document_obj, 'delivery_address', ''))

    # Document Details
    doc_details = []
    if doc_type == 'quotation':
        doc_details.append(f"Quote #: {document_obj.quotation_number}")
        doc_details.append(f"Date: {document_obj.created_at.strftime('%d/%m/%Y')}")
        doc_details.append(f"Valid Until: {document_obj.valid_until.strftime('%d/%m/%Y')}")
    elif doc_type == 'order':
        doc_details.append(f"Order #: {document_obj.order_number}")
        doc_details.append(f"Date: {document_obj.created_at.strftime('%d/%m/%Y')}")
    else:
        doc_details.append(f"Invoice #: {document_obj.invoice_number}")
        doc_details.append(f"Date: {document_obj.invoice_date.strftime('%d/%m/%Y')}")
        doc_details.append(f"Due Date: {document_obj.due_date.strftime('%d/%m/%Y')}")

    contact_table_data = [
        [Paragraph("<br/>".join(vendor_info), styles['Normal']), 
         Paragraph("<br/>".join(customer_info), styles['Normal']),
         Paragraph("<br/>".join(doc_details), styles['Normal'])]
    ]
    
    contact_table = Table(contact_table_data, colWidths=[6*cm, 6*cm, 5*cm])
    contact_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(contact_table)
    elements.append(Spacer(1, 1*cm))

    # --- ITEMS TABLE SECTION ---
    table_header = ['Product', 'Rental Period', 'Qty', 'Unit Price', 'Amount']
    table_data = [table_header]
    
    lines = []
    if hasattr(document_obj, 'quotation_lines'):
        lines = document_obj.quotation_lines.all()
    elif hasattr(document_obj, 'order_lines'):
        lines = document_obj.order_lines.all()
    elif hasattr(document_obj, 'invoice_lines'):
        lines = document_obj.invoice_lines.all()
        
    for line in lines:
        if doc_type == 'invoice':
            desc = line.description
        else:
            desc = f"<b>{line.product.name}</b>"
        
        period = ""
        if hasattr(line, 'rental_start_date') and hasattr(line, 'rental_end_date'):
            period = f"{line.rental_start_date.strftime('%d/%m/%Y')} - {line.rental_end_date.strftime('%d/%m/%Y')}"
            
        table_data.append([
            Paragraph(desc, styles['Normal']),
            period,
            str(line.quantity),
            f"Rs. {line.unit_price:,.2f}",
            f"Rs. {line.line_total:,.2f}"
        ])

    item_table = Table(table_data, colWidths=[6*cm, 5*cm, 1.5*cm, 2.5*cm, 2.5*cm], repeatRows=1)
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (2,1), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(item_table)
    
    # --- SUMMARY SECTION ---
    summary_data = [
        ["", "", "", "<b>Subtotal:</b>", f"Rs. {document_obj.subtotal:,.2f}"],
        ["", "", "", "<b>Discount:</b>", f"(Rs. {document_obj.discount_amount:,.2f})"],
        ["", "", "", "<b>GST Total:</b>", f"Rs. {document_obj.tax_amount:,.2f}"],
    ]
    
    if hasattr(document_obj, 'late_fee') and document_obj.late_fee > 0:
        summary_data.append(["", "", "", "<b>Late Fees:</b>", f"Rs. {document_obj.late_fee:,.2f}"])
        
    total_val = getattr(document_obj, 'total', getattr(document_obj, 'total_amount', Decimal('0.00')))
    summary_data.append(["", "", "", "<b>Total Amount:</b>", f"<b>Rs. {total_val:,.2f}</b>"])
    
    if hasattr(document_obj, 'advance_payment_amount') and document_obj.advance_payment_amount > 0:
        pct = document_obj.advance_payment_percentage
        summary_data.append(["", "", "", f"<b>Advance Required ({pct}%):</b>", f"<b>Rs. {document_obj.advance_payment_amount:,.2f}</b>"])

    summary_table = Table(summary_data, colWidths=[6*cm, 5*cm, 1.5*cm, 3.5*cm, 1.5*cm])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (-2,0), (-1,-1), 'RIGHT'),
        ('FONTSIZE', (-2,0), (-1,-1), 10),
        ('TOPPADDING', (-2,-1), (-1,-1), 10),
    ]))
    # Adjust total colWidths if needed - wait, reportlab might need help
    summary_table = Table(summary_data, colWidths=[6*cm, 5*cm, 1.5*cm, 3.5*cm, 3*cm])
    summary_table.setStyle(TableStyle([
         ('ALIGN', (-2,0), (-1,-1), 'RIGHT'),
    ]))
    elements.append(summary_table)

    # --- TERMS & FOOTER ---
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("<b>Terms & Conditions:</b>", styles['Normal']))
    terms = [
        "1. Rental period is inclusive of pickup and return dates.",
        "2. Any damage to equipment will be charged as per assessment.",
        "3. Late returns will attract additional daily charges as per policy.",
        f"4. Quotation validity: {config.quotation_validity_days} days." if doc_type == 'quotation' else "4. All payments are subject to standard GST rules."
    ]
    for term in terms:
        elements.append(Paragraph(f"<font size=8>{term}</font>", styles['Normal']))

    elements.append(Spacer(1, 2*cm))
    elements.append(Paragraph("This is a computer generated document and does not require a physical signature.", styles['Center']))
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
