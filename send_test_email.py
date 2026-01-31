#!/usr/bin/env python
"""
Quick test script to send email to kamanipoojan@gmail.com
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_erp.settings')
django.setup()

from django.core.mail import EmailMessage
from django.conf import settings

def send_test_email():
    """Send a test email"""
    print(f"Email Backend: {settings.EMAIL_BACKEND}")
    print(f"Email Host: {settings.EMAIL_HOST}")
    print(f"Email Port: {settings.EMAIL_PORT}")
    print(f"Email User: {settings.EMAIL_HOST_USER}")
    print(f"Email Use TLS: {settings.EMAIL_USE_TLS}")
    print(f"Email Use SSL: {settings.EMAIL_USE_SSL}")
    print(f"From Email: {settings.DEFAULT_FROM_EMAIL}")
    print("-" * 50)
    
    try:
        subject = 'Test Email from Gcet-X-Odoo System'
        message = '''
Hello,

This is a test email from the Gcet-X-Odoo Rental ERP System.

If you received this email, it means the email configuration is working correctly!

Timestamp: 2026-02-01 04:03:50 IST

Best regards,
Gcet-X-Odoo Team
        '''
        
        recipient = 'kamanipoojan@gmail.com'
        
        print(f"Sending test email to: {recipient}")
        print(f"Subject: {subject}")
        print(f"From: {settings.DEFAULT_FROM_EMAIL}")
        
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
