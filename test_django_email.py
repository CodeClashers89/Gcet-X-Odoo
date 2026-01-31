"""
Test script to verify Brevo email delivery with detailed logging
"""
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
import django
import os

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_erp.settings')
django.setup()

print("=" * 60)
print("BREVO SMTP CONFIGURATION TEST")
print("=" * 60)
print(f"Email Backend: {settings.EMAIL_BACKEND}")
print(f"SMTP Host: {settings.EMAIL_HOST}")
print(f"SMTP Port: {settings.EMAIL_PORT}")
print(f"Use SSL: {settings.EMAIL_USE_SSL}")
print(f"Use TLS: {settings.EMAIL_USE_TLS}")
print(f"SMTP User: {settings.EMAIL_HOST_USER}")
print(f"From Email: {settings.DEFAULT_FROM_EMAIL}")
print(f"Has Password: {'Yes' if settings.EMAIL_HOST_PASSWORD else 'No'}")
print("=" * 60)

# Test 1: Simple send_mail
print("\nTest 1: Sending simple email...")
try:
    result = send_mail(
        subject='Django Test Email - Configuration Verified',
        message='This email confirms your Django application is correctly configured with Brevo SMTP.\n\nSent from: Django Rental ERP\nTimestamp: 2026-01-31\n\nIf you receive this, the setup is working!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['kamanipoojan@gmail.com'],
        fail_silently=False,
    )
    print(f"✓ Simple email sent successfully! Result: {result}")
except Exception as e:
    print(f"✗ Error sending simple email: {e}")
    import traceback
    traceback.print_exc()

# Test 2: EmailMessage with more details
print("\nTest 2: Sending detailed email with HTML...")
try:
    email = EmailMessage(
        subject='Django HTML Test - Brevo SMTP',
        body='<html><body><h1>Test Email</h1><p>This is an HTML test email from Django using Brevo SMTP on port 465.</p><p><strong>Timestamp:</strong> 2026-01-31</p></body></html>',
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=['kamanipoojan@gmail.com'],
    )
    email.content_subtype = 'html'
    result = email.send(fail_silently=False)
    print(f"✓ HTML email sent successfully! Result: {result}")
except Exception as e:
    print(f"✗ Error sending HTML email: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("EMAIL TESTS COMPLETED")
print("=" * 60)
print("\nIMPORTANT NOTES:")
print("1. Check spam/junk folder in Gmail")
print("2. Verify sender email (hetmungara107@gmail.com) is authenticated in Brevo")
print("3. Check Brevo dashboard for send logs and delivery status")
print("4. Email delivery may take 1-5 minutes")
