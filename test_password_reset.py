#!/usr/bin/env python
"""
Test password reset email functionality
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_erp.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

User = get_user_model()

def test_password_reset():
    """Test sending a password reset email"""
    print("=" * 60)
    print("TESTING PASSWORD RESET EMAIL")
    print("=" * 60)
    
    # Check if test user exists
    test_email = 'kamanipoojan@gmail.com'
    
    try:
        user = User.objects.filter(email=test_email).first()
        
        if not user:
            print(f"\n⚠️  No user found with email: {test_email}")
            print("   Creating a test user...")
            user = User.objects.create_user(
                username='test_user_pooja',
                email=test_email,
                first_name='Pooja',
                password='TestPassword123!@#'
            )
            print(f"✓ Test user created: {user.email}")
        else:
            print(f"✓ Found existing user: {user.email} (ID: {user.id})")
        
        # Generate reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build reset URL
        reset_url = f'http://localhost:8000/accounts/reset-password/{uid}/{token}/'
        
        print(f"\nReset URL: {reset_url}")
        print(f"User: {user.first_name or user.email}")
        print(f"Email: {user.email}")
        print(f"\nSending password reset email...")
        print(f"Backend: {settings.EMAIL_BACKEND}")
        
        # Send reset email
        subject = 'Password Reset Request - Rental ERP'
        message = f"""
Hello {user.first_name or user.email},

You requested to reset your password. Click the link below to proceed:

{reset_url}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
Rental ERP Team
        """
        
        result = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        print(f"\n✓ Email sent successfully! (Result: {result})")
        print(f"  To: {user.email}")
        print(f"  From: {settings.DEFAULT_FROM_EMAIL}")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_password_reset()
