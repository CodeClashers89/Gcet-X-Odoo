"""
Notification Service for Rental Workflow
Handles email and SMS notifications at each stage of the rental process
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications to customers and vendors"""
    
    @staticmethod
    def send_email(subject, recipient_email, template_name, context, attachments=None):
        """
        Send email notification with optional attachments
        
        Args:
            subject: Email subject
            recipient_email: Recipient email address
            template_name: Path to email template
            context: Template context variables
            attachments: List of tuples (filename, content, mimetype)
        """
        try:
            from django.core.mail import EmailMessage
            # Render HTML email from template
            html_message = render_to_string(template_name, context)
            
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            email.content_subtype = "html"  # Main content is now text/html
            
            if attachments:
                for filename, content, mimetype in attachments:
                    email.attach(filename, content, mimetype)
            
            email.send(fail_silently=False)
            logger.info(f"Email sent to {recipient_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_sms(phone_number, message):
        """
        Send SMS notification
        
        TODO: Integrate with SMS provider (Twilio, AWS SNS, etc.)
        For now, this is a placeholder
        """
        try:
            # Placeholder for SMS integration
            logger.info(f"SMS sent to {phone_number}: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            return False


class RentalWorkflowNotifications:
    """Notifications specific to rental workflow stages"""
    
    # Stage 1: Customer submits inquiry
    @staticmethod
    def notify_customer_inquiry_submitted(inquiry):
        """Notify customer that inquiry was submitted"""
        context = {
            'customer_name': inquiry.customer.get_full_name(),
            'product_name': inquiry.product.name,
            'quantity': inquiry.quantity,
            'inquiry_number': inquiry.inquiry_number,
            'rental_start': inquiry.rental_start_date,
            'rental_end': inquiry.rental_end_date,
        }
        
        NotificationService.send_email(
            subject=f'Rental Inquiry Submitted - {inquiry.inquiry_number}',
            recipient_email=inquiry.customer.email,
            template_name='rentals/emails/inquiry_submitted.html',
            context=context
        )
    
    # Stage 2: Vendor receives inquiry
    @staticmethod
    def notify_vendor_inquiry_received(inquiry):
        """Notify vendor of new inquiry"""
        context = {
            'vendor_name': inquiry.vendor.get_full_name(),
            'customer_name': inquiry.customer.get_full_name(),
            'product_name': inquiry.product.name,
            'quantity': inquiry.quantity,
            'inquiry_number': inquiry.inquiry_number,
            'rental_start': inquiry.rental_start_date,
            'rental_end': inquiry.rental_end_date,
            'inquiry_url': f'/catalog/vendor/inquiries/{inquiry.id}/',
        }
        
        NotificationService.send_email(
            subject=f'New Rental Inquiry - {inquiry.inquiry_number}',
            recipient_email=inquiry.vendor.email,
            template_name='rentals/emails/vendor_inquiry_received.html',
            context=context
        )
    
    # Stage 3: Vendor accepts/rejects inquiry
    @staticmethod
    def notify_customer_inquiry_accepted(inquiry):
        """Notify customer that vendor accepted inquiry"""
        context = {
            'customer_name': inquiry.customer.get_full_name(),
            'vendor_name': inquiry.vendor.get_full_name(),
            'product_name': inquiry.product.name,
            'inquiry_number': inquiry.inquiry_number,
        }
        
        NotificationService.send_email(
            subject=f'Inquiry Accepted - Quotation Coming Soon',
            recipient_email=inquiry.customer.email,
            template_name='rentals/emails/inquiry_accepted.html',
            context=context
        )
    
    @staticmethod
    def notify_customer_inquiry_rejected(inquiry, reason=''):
        """Notify customer that vendor rejected inquiry"""
        context = {
            'customer_name': inquiry.customer.get_full_name(),
            'vendor_name': inquiry.vendor.get_full_name(),
            'product_name': inquiry.product.name,
            'inquiry_number': inquiry.inquiry_number,
            'reason': reason,
        }
        
        NotificationService.send_email(
            subject=f'Inquiry Not Available',
            recipient_email=inquiry.customer.email,
            template_name='rentals/emails/inquiry_rejected.html',
            context=context
        )
    
    # Stage 4: Vendor sends quotation
    @staticmethod
    def notify_customer_quotation_sent(quotation):
        """Notify customer that quotation is ready"""
        context = {
            'customer_name': quotation.customer.get_full_name(),
            'vendor_name': quotation.quotation.vendor.get_full_name() if hasattr(quotation, 'quotation') else 'Vendor',
            'quotation_number': quotation.quotation_number,
            'total_amount': quotation.total_amount,
            'valid_until': quotation.valid_until,
            'quotation_url': f'/rentals/quotation/{quotation.id}/',
        }
        
        # Generate PDF for attachment
        from rentals.pdf_utils import generate_rental_document
        pdf_content = generate_rental_document(quotation, doc_type='quotation')
        attachments = [
            (f"Quotation_{quotation.quotation_number}.pdf", pdf_content, 'application/pdf')
        ]
        
        NotificationService.send_email(
            subject=f'Your Quotation is Ready - {quotation.quotation_number}',
            recipient_email=quotation.customer.email,
            template_name='rentals/emails/quotation_sent.html',
            context=context,
            attachments=attachments
        )
    
    # Stage 5: Customer accepts quotation
    @staticmethod
    def notify_vendor_quotation_accepted(quotation):
        """Notify vendor that customer accepted quotation"""
        context = {
            'vendor_name': quotation.customer.vendorprofile.company_name if hasattr(quotation.customer, 'vendorprofile') else 'Vendor',
            'customer_name': quotation.customer.get_full_name(),
            'quotation_number': quotation.quotation_number,
            'total_amount': quotation.total_amount,
        }
        
        NotificationService.send_email(
            subject=f'Quotation Accepted - {quotation.quotation_number}',
            recipient_email=quotation.customer.email,
            template_name='rentals/emails/vendor_quotation_accepted.html',
            context=context
        )
    
    # Stage 6: Vendor confirms rental order
    @staticmethod
    def notify_customer_order_confirmed(rental_order):
        """Notify customer that rental order is confirmed"""
        context = {
            'customer_name': rental_order.customer.get_full_name(),
            'order_number': rental_order.order_number,
            'total_amount': rental_order.total_amount,
            'rental_start': rental_order.rental_start_date,
            'rental_end': rental_order.rental_end_date,
            'pickup_location': rental_order.pickup_location,
            'order_url': f'/rentals/order/{rental_order.id}/',
        }
        
        # Generate PDF for attachment
        from rentals.pdf_utils import generate_rental_document
        pdf_content = generate_rental_document(rental_order, doc_type='order')
        attachments = [
            (f"Order_{rental_order.order_number}.pdf", pdf_content, 'application/pdf')
        ]
        
        NotificationService.send_email(
            subject=f'Rental Order Confirmed - {rental_order.order_number}',
            recipient_email=rental_order.customer.email,
            template_name='rentals/emails/order_confirmed.html',
            context=context,
            attachments=attachments
        )
    
    @staticmethod
    def notify_customer_order_rejected(rental_order, reason=''):
        """Notify customer that rental order was rejected"""
        context = {
            'customer_name': rental_order.customer.get_full_name(),
            'order_number': rental_order.order_number,
            'reason': reason,
        }
        
        NotificationService.send_email(
            subject=f'Rental Order Could Not Be Confirmed',
            recipient_email=rental_order.customer.email,
            template_name='rentals/emails/order_rejected.html',
            context=context
        )
    
    # Stage 7: Payment received
    @staticmethod
    def notify_customer_payment_received(payment):
        """Notify customer that payment was received"""
        context = {
            'customer_name': payment.rental_order.customer.get_full_name(),
            'order_number': payment.rental_order.order_number,
            'payment_number': payment.payment_number,
            'amount': payment.amount,
            'payment_date': payment.payment_date,
            'payment_method': payment.get_payment_method_display(),
        }
        
        NotificationService.send_email(
            subject=f'Payment Received - {payment.payment_number}',
            recipient_email=payment.rental_order.customer.email,
            template_name='rentals/emails/payment_received.html',
            context=context
        )
    
    @staticmethod
    def notify_vendor_payment_received(payment):
        """Notify vendor that payment was received"""
        context = {
            'vendor_name': payment.rental_order.vendor.get_full_name(),
            'customer_name': payment.rental_order.customer.get_full_name(),
            'order_number': payment.rental_order.order_number,
            'amount': payment.amount,
        }
        
        NotificationService.send_email(
            subject=f'Payment Received for Order - {payment.rental_order.order_number}',
            recipient_email=payment.rental_order.vendor.email,
            template_name='rentals/emails/vendor_payment_received.html',
            context=context
        )
    
    # Stage 8: Invoice generated
    @staticmethod
    def notify_customer_invoice_generated(invoice):
        """Notify customer that invoice was generated"""
        context = {
            'customer_name': invoice.rental_order.customer.get_full_name(),
            'invoice_number': invoice.invoice_number,
            'order_number': invoice.rental_order.order_number,
            'amount': invoice.total_amount,
            'due_date': invoice.due_date,
            'invoice_url': f'/rentals/invoice/{invoice.id}/',
        }
        
        # Generate PDF for attachment
        from rentals.pdf_utils import generate_rental_document
        pdf_content = generate_rental_document(invoice, doc_type='invoice')
        attachments = [
            (f"Invoice_{invoice.invoice_number}.pdf", pdf_content, 'application/pdf')
        ]
        
        NotificationService.send_email(
            subject=f'Invoice Generated - {invoice.invoice_number}',
            recipient_email=invoice.rental_order.customer.email,
            template_name='rentals/emails/invoice_generated.html',
            context=context,
            attachments=attachments
        )
    
    # Stage 9: Rental period reminder
    @staticmethod
    def notify_customer_pickup_reminder(rental_order, days_until_pickup=1):
        """Notify customer about upcoming pickup"""
        context = {
            'customer_name': rental_order.customer.get_full_name(),
            'pickup_date': rental_order.pickup_date,
            'pickup_location': rental_order.pickup_location,
            'order_number': rental_order.order_number,
            'days_until': days_until_pickup,
        }
        
        NotificationService.send_email(
            subject=f'Pickup Reminder - {rental_order.order_number}',
            recipient_email=rental_order.customer.email,
            template_name='rentals/emails/pickup_reminder.html',
            context=context
        )
    
    # Stage 10: Return reminder
    @staticmethod
    def notify_customer_return_reminder(rental_order, days_until_return=1):
        """Notify customer about upcoming return date"""
        context = {
            'customer_name': rental_order.customer.get_full_name(),
            'return_date': rental_order.rental_end_date,
            'order_number': rental_order.order_number,
            'days_until': days_until_return,
        }
        
        NotificationService.send_email(
            subject=f'Return Reminder - {rental_order.order_number}',
            recipient_email=rental_order.customer.email,
            template_name='rentals/emails/return_reminder.html',
            context=context
        )
    
    # Stage 11: Return initiated
    @staticmethod
    def notify_vendor_return_initiated(rental_return):
        """Notify vendor that return process initiated"""
        context = {
            'vendor_name': rental_return.rental_order.vendor.get_full_name(),
            'customer_name': rental_return.rental_order.customer.get_full_name(),
            'return_number': rental_return.return_number,
            'return_expected_date': rental_return.return_expected_date,
            'order_number': rental_return.rental_order.order_number,
        }
        
        NotificationService.send_email(
            subject=f'Return Initiated - {rental_return.return_number}',
            recipient_email=rental_return.rental_order.vendor.email,
            template_name='rentals/emails/vendor_return_initiated.html',
            context=context
        )
    
    # Stage 12: Return completed & settled
    @staticmethod
    def notify_customer_rental_settled(rental_return):
        """Notify customer that rental has been settled"""
        context = {
            'customer_name': rental_return.rental_order.customer.get_full_name(),
            'return_number': rental_return.return_number,
            'refund_amount': rental_return.refund_amount,
            'settled_at': rental_return.settled_at,
            'damage_cost': rental_return.damage_cost,
            'late_fees': rental_return.late_return_fees,
        }
        
        NotificationService.send_email(
            subject=f'Rental Settled - Refund Processed',
            recipient_email=rental_return.rental_order.customer.email,
            template_name='rentals/emails/rental_settled.html',
            context=context
        )
    
    @staticmethod
    def notify_vendor_rental_settled(rental_return):
        """Notify vendor that rental has been settled"""
        context = {
            'vendor_name': rental_return.rental_order.vendor.get_full_name(),
            'customer_name': rental_return.rental_order.customer.get_full_name(),
            'return_number': rental_return.return_number,
            'damage_cost': rental_return.damage_cost,
            'late_fees': rental_return.late_return_fees,
            'settled_at': rental_return.settled_at,
        }
        
        NotificationService.send_email(
            subject=f'Rental Settled - {rental_return.return_number}',
            recipient_email=rental_return.rental_order.vendor.email,
            template_name='rentals/emails/vendor_rental_settled.html',
            context=context
        )


# Convenience functions for use in views
def notify_inquiry_stage(inquiry, stage, reason=''):
    """Send appropriate notification based on inquiry stage"""
    if stage == 'submitted':
        RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)
        RentalWorkflowNotifications.notify_vendor_inquiry_received(inquiry)
    elif stage == 'accepted':
        RentalWorkflowNotifications.notify_customer_inquiry_accepted(inquiry)
    elif stage == 'rejected':
        RentalWorkflowNotifications.notify_customer_inquiry_rejected(inquiry, reason)


def notify_quotation_stage(quotation, stage):
    """Send appropriate notification based on quotation stage"""
    if stage == 'sent':
        RentalWorkflowNotifications.notify_customer_quotation_sent(quotation)
    elif stage == 'accepted':
        RentalWorkflowNotifications.notify_vendor_quotation_accepted(quotation)


def notify_order_stage(rental_order, stage, reason=''):
    """Send appropriate notification based on order stage"""
    if stage == 'confirmed':
        RentalWorkflowNotifications.notify_customer_order_confirmed(rental_order)
    elif stage == 'rejected':
        RentalWorkflowNotifications.notify_customer_order_rejected(rental_order, reason)


def notify_payment_stage(payment):
    """Send notifications when payment is received"""
    RentalWorkflowNotifications.notify_customer_payment_received(payment)
    RentalWorkflowNotifications.notify_vendor_payment_received(payment)


def notify_invoice_stage(invoice):
    """Send invoice notification"""
    RentalWorkflowNotifications.notify_customer_invoice_generated(invoice)


def notify_return_stage(rental_return, stage):
    """Send appropriate notification based on return stage"""
    if stage == 'initiated':
        RentalWorkflowNotifications.notify_vendor_return_initiated(rental_return)
    elif stage == 'settled':
        RentalWorkflowNotifications.notify_customer_rental_settled(rental_return)
        RentalWorkflowNotifications.notify_vendor_rental_settled(rental_return)
