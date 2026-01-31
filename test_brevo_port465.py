#!/usr/bin/env python
"""
Test Brevo SMTP authentication on port 465 (SSL)
"""
import smtplib
import ssl
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_HOST = 'smtp-relay.brevo.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'hetmungara107@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

print("=" * 70)
print("BREVO SMTP CONNECTION TEST - PORT 465 (SSL)")
print("=" * 70)
print(f"Host: {EMAIL_HOST}")
print(f"Port: {EMAIL_PORT}")
print(f"User: {EMAIL_HOST_USER}")
print(f"Password length: {len(EMAIL_HOST_PASSWORD)} characters")
print()

try:
    print("Connecting to Brevo SMTP server...")
    context = ssl.create_default_context()
    server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, context=context, timeout=10)
    print("✓ SSL connection established")
    
    print("\nAttempting login...")
    print(f"  Username: {EMAIL_HOST_USER}")
    
    server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    print("✓ Login successful!")
    
    # Try sending test email
    from_email = 'noreply@rentalerp.com'
    to_email = 'neel9086@gmail.com'
    subject = 'Password Reset - Rental ERP'
    body = '''Hello,

Here's your password reset link. If you requested a password reset, click the link below:

https://example.com/accounts/reset-password/

This link will expire in 24 hours.

If you did not request this, please ignore this email.

Best regards,
Rental ERP System'''
    
    message = f'Subject: {subject}\nFrom: {from_email}\nTo: {to_email}\n\n{body}'
    
    print(f"\nSending test email to {to_email}...")
    result = server.sendmail(from_email, [to_email], message)
    
    if result == {}:
        print(f"✓ Email sent successfully!")
        print(f"  Status: DELIVERED")
    else:
        print(f"⚠ Email sent with warnings: {result}")
    
    server.quit()
    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED - BREVO SMTP IS WORKING!")
    print("=" * 70)
    print("\nYou can now enable SMTP in your Django settings:")
    print("  EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend")
    print("  EMAIL_PORT=465")
    print("  EMAIL_USE_SSL=True")
    print("  EMAIL_USE_TLS=False")
    
except smtplib.SMTPAuthenticationError as e:
    print(f"\n✗ Authentication failed: {e}")
    print("\nPossible causes:")
    print("1. Email/password is incorrect")
    print("2. SMTP credentials have been revoked")
    print("3. Need to generate new SMTP key in Brevo dashboard")
    print("\nAction required:")
    print("Go to https://app.brevo.com/settings/smtp and generate new SMTP credentials")
    
except smtplib.SMTPException as e:
    print(f"\n✗ SMTP Error: {e}")
    print("This might be a temporary Brevo server issue")
    
except Exception as e:
    print(f"\n✗ Unexpected error: {e}")
    print("Check network connectivity and firewall settings")
