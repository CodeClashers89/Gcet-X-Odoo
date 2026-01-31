"""
Management command to create default email templates.
Usage: python manage.py create_default_templates
"""
from django.core.management.base import BaseCommand
from system_settings.models import EmailTemplate


class Command(BaseCommand):
    help = 'Creates default email templates for the system'

    def handle(self, *args, **kwargs):
        templates = [
            {
                'template_type': 'welcome_customer',
                'subject': 'Welcome to {site_title} - Get Started!',
                'body_html': '''
                <h2>Welcome, {customer_name}!</h2>
                <p>Thank you for registering with {site_title}.</p>
                <p>You can now browse our catalog and request quotations for rental equipment.</p>
                <p>Best regards,<br>{company_name}</p>
                ''',
                'body_text': 'Welcome {customer_name}! Thank you for registering with {site_title}.',
                'is_active': True
            },
            {
                'template_type': 'welcome_vendor',
                'subject': 'Welcome to {site_title} - Vendor Onboarding',
                'body_html': '''
                <h2>Welcome, {vendor_name}!</h2>
                <p>Your vendor registration is pending approval.</p>
                <p>Our team will review your application and activate your account soon.</p>
                <p>Best regards,<br>{company_name}</p>
                ''',
                'body_text': 'Welcome {vendor_name}! Your vendor registration is pending approval.',
                'is_active': True
            },
            {
                'template_type': 'vendor_approved',
                'subject': 'Your Vendor Account Has Been Approved! 🎉',
                'body_html': '''
                <h2>Congratulations, {vendor_name}!</h2>
                <p>Your vendor account has been approved by our team.</p>
                <p>You can now log in and start listing your products.</p>
                <p><a href="{login_url}">Login to Dashboard</a></p>
                <p>Best regards,<br>{company_name}</p>
                ''',
                'body_text': 'Congratulations {vendor_name}! Your vendor account has been approved.',
                'is_active': True
            },
            {
                'template_type': 'quotation_created',
                'subject': 'New Quotation Request #{quotation_number}',
                'body_html': '''
                <h2>New Quotation Request</h2>
                <p>Dear {vendor_name},</p>
                <p>You have received a new quotation request from {customer_name}.</p>
                <p><strong>Quotation #:</strong> {quotation_number}</p>
                <p><strong>Rental Period:</strong> {rental_period}</p>
                <p>Please log in to review and respond.</p>
                <p>Best regards,<br>{company_name}</p>
                ''',
                'body_text': 'New quotation request #{quotation_number} from {customer_name}.',
                'is_active': True
            },
            {
                'template_type': 'quotation_responded',
                'subject': 'Quotation Response for #{quotation_number}',
                'body_html': '''
                <h2>Quotation Response Ready</h2>
                <p>Dear {customer_name},</p>
                <p>The vendor has responded to your quotation request.</p>
                <p><strong>Quotation #:</strong> {quotation_number}</p>
                <p><strong>Quoted Amount:</strong> ₹{quoted_amount}</p>
                <p>Please log in to review and proceed.</p>
                <p>Best regards,<br>{company_name}</p>
                ''',
                'body_text': 'Vendor has responded to quotation #{quotation_number}.',
                'is_active': True
            },
            {
                'template_type': 'order_confirmed',
                'subject': 'Order Confirmed #{order_number}',
                'body_html': '''
                <h2>Order Confirmation</h2>
                <p>Dear {customer_name},</p>
                <p>Your rental order has been confirmed!</p>
                <p><strong>Order #:</strong> {order_number}</p>
                <p><strong>Pickup Date:</strong> {pickup_date}</p>
                <p><strong>Return Date:</strong> {return_date}</p>
                <p>Best regards,<br>{company_name}</p>
                ''',
                'body_text': 'Your order #{order_number} has been confirmed.',
                'is_active': True
            },
            {
                'template_type': 'payment_received',
                'subject': 'Payment Received - Invoice #{invoice_number}',
                'body_html': '''
                <h2>Payment Confirmation</h2>
                <p>Dear {customer_name},</p>
                <p>We have received your payment.</p>
                <p><strong>Invoice #:</strong> {invoice_number}</p>
                <p><strong>Amount:</strong> ₹{amount}</p>
                <p><strong>Payment Method:</strong> {payment_method}</p>
                <p>Thank you for your business!</p>
                <p>Best regards,<br>{company_name}</p>
                ''',
                'body_text': 'Payment of ₹{amount} received for invoice #{invoice_number}.',
                'is_active': True
            },
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = EmailTemplate.objects.update_or_create(
                template_type=template_data['template_type'],
                defaults={
                    'subject': template_data['subject'],
                    'body_html': template_data['body_html'],
                    'body_text': template_data['body_text'],
                    'is_active': template_data['is_active']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {template.get_template_type_display()}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'→ Updated: {template.get_template_type_display()}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Done! Created {created_count}, Updated {updated_count} templates'))
