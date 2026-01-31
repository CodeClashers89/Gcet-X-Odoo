#!/usr/bin/env python
"""
Test Brevo SMTP connection with proper debugging
"""
import smtplib
import ssl
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Brevo SMTP Settings
EMAIL_HOST = 'smtp-relay.brevo.com'
EMAIL_PORT = 587  # Try TLS first
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'hetmungara107@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

print("=" * 60)
print("BREVO SMTP CONNECTION TEST")
print("=" * 60)
print(f"Host: {EMAIL_HOST}")
print(f"Port: {EMAIL_PORT}")
print(f"User: {EMAIL_HOST_USER}")
print(f"Password length: {len(EMAIL_HOST_PASSWORD)} characters")
print(f"Password preview: {EMAIL_HOST_PASSWORD[:20]}...")
print()

# Try TLS connection (port 587)
print("Attempting connection with TLS (port 587)...")
try:
    server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10)
    server.starttls()
    
    print("✓ TLS connection established")
    print("Attempting login...")
    
    server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    print("✓ Login successful!")
    
    # Try sending test email
    from_email = 'noreply@rentalerp.com'
    to_email = 'neel9086@gmail.com'
    subject = 'Test from Brevo SMTP Direct'
    body = 'This is a test email sent directly via Brevo SMTP (TLS)'
    
    message = f'Subject: {subject}\nFrom: {from_email}\nTo: {to_email}\n\n{body}'
    
    print(f"Sending test email to {to_email}...")
    result = server.sendmail(from_email, to_email, message)
    print(f"✓ Email sent successfully! (Result: {result})")
    
    server.quit()
    print("\n✓ ALL TESTS PASSED - SMTP IS WORKING!")
    sys.exit(0)
    
except smtplib.SMTPAuthenticationError as e:
    print(f"✗ Authentication failed: {e}")
    print("\nTrying with SSL (port 465)...")
    
    try:
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(EMAIL_HOST, 465, context=context, timeout=10)
        
        print("✓ SSL connection established")
        print("Attempting login...")
        
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        print("✓ Login successful!")
        
        from_email = 'noreply@rentalerp.com'
        to_email = 'neel9086@gmail.com'
        subject = 'Test from Brevo SMTP Direct'
        body = 'This is a test email sent directly via Brevo SMTP (SSL)'
        
        message = f'Subject: {subject}\nFrom: {from_email}\nTo: {to_email}\n\n{body}'
        
        print(f"Sending test email to {to_email}...")
        result = server.sendmail(from_email, to_email, message)
        print(f"✓ Email sent successfully! (Result: {result})")
        
        server.quit()
        print("\n✓ ALL TESTS PASSED - SMTP IS WORKING!")
        sys.exit(0)
        
    except Exception as e:
        print(f"✗ SSL connection failed: {e}")
        print("\nPossible causes:")
        print("1. Email credentials (username/password) are incorrect")
        print("2. SMTP key has expired or been revoked in Brevo")
        print("3. Special characters in password need URL encoding")
        print("\nSolution: Generate new SMTP credentials in Brevo dashboard")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print("Check internet connectivity and Brevo server status")
    sys.exit(1)
