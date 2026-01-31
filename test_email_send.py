#!/usr/bin/env python
"""
Test script to verify email sending functionality
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_erp.settings')
sys.path.insert(0, r'D:\GCETxOdoo')
django.setup()

from django.core.mail import send_mail, EmailMessage
from django.conf import settings

def send_test_email():
    """Send a test email to verify configuration"""
    print(f"Email Backend: {settings.EMAIL_BACKEND}")
    print(f"Email Host: {settings.EMAIL_HOST}")
    print(f"Email Port: {settings.EMAIL_PORT}")
    print(f"Email User: {settings.EMAIL_HOST_USER}")
    print(f"Email Use TLS: {settings.EMAIL_USE_TLS}")
    print(f"Email Use SSL: {settings.EMAIL_USE_SSL}")
    print(f"From Email: {settings.DEFAULT_FROM_EMAIL}")
    print("-" * 50)
    
    try:
        subject = 'Test Email from Rental ERP'
        message = '''
Hello,

This is a test email to verify that the email sending functionality is working correctly.

If you received this email, it means:
1. Brevo SMTP configuration is correct
2. Email credentials are valid
3. Email sending is functional

Best regards,
Rental ERP System
        '''
        
        recipient = 'neel9086@gmail.com'
        
        print(f"Sending test email to: {recipient}")
        print(f"Subject: {subject}")
        print(f"From: {settings.DEFAULT_FROM_EMAIL}")
        
        # Try using EmailMessage for more details
        msg = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        result = msg.send(fail_silently=False)
        
        print(f"✓ Email sent successfully! (Result: {result})")
        
    except Exception as e:
        print(f"✗ Error sending email: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    send_test_email()

