#!/usr/bin/env python
"""
Check current email configuration loaded by Django
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_erp.settings')
django.setup()

from django.conf import settings

print("=" * 60)
print("CURRENT EMAIL CONFIGURATION")
print("=" * 60)
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print("=" * 60)

if 'filebased' in settings.EMAIL_BACKEND:
    print("\n⚠️  WARNING: Email backend is still set to 'filebased'")
    print("   Emails will be saved to files instead of being sent via SMTP")
    print("   Please restart the Django server to load the new configuration!")
elif 'smtp' in settings.EMAIL_BACKEND:
    print("\n✓ Email backend is correctly set to SMTP")
    print("  Emails will be sent via Brevo SMTP")
else:
    print(f"\n⚠️  Unknown email backend: {settings.EMAIL_BACKEND}")
