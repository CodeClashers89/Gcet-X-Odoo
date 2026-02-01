"""
Two-Factor Authentication (2FA) and Multi-Factor Authentication (MFA) implementation.
Phase 10 - Enhanced authentication security with TOTP and email verification.
"""
import logging
import secrets
from io import BytesIO
from base64 import b64encode
from datetime import datetime, timedelta

# Try to import pyotp FIRST before any Django imports
try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError as e:
    pyotp = None
    PYOTP_AVAILABLE = False
    print(f"PyOTP import failed: {e}")

# Now import qrcode
import qrcode

# Now Django imports
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()

if not PYOTP_AVAILABLE:
    logger.warning('pyotp library not installed. TOTP functionality will be limited.')



class TOTPManager:
    """Manage Time-based One-Time Passwords (TOTP) for 2FA."""
    
    def _get_pyotp(self):
        """Dynamic import of pyotp to ensure it's available."""
        try:
            import pyotp
            return pyotp
        except ImportError:
            return None
    
    def generate_secret(self):
        """
        Generate a new TOTP secret key.
        """
        pyotp_lib = self._get_pyotp()
        if not pyotp_lib:
            logger.error("Cannot generate secret: pyotp library not installed")
            return None
        return pyotp_lib.random_base32()
    
    def get_totp(self, secret):
        """
        Create TOTP instance for a secret.
        """
        pyotp_lib = self._get_pyotp()
        if not pyotp_lib or not secret:
            return None
        return pyotp_lib.TOTP(secret)
    
    def verify_token(self, secret, token):
        """
        Verify a TOTP token.
        """
        pyotp_lib = self._get_pyotp()
        if not pyotp_lib:
            return False
        
        try:
            totp = self.get_totp(secret)
            if not totp:
                return False
            return totp.verify(token, valid_window=1)
        except Exception as e:
            logger.error(f'TOTP verification failed: {str(e)}')
            return False
    
    def get_provisioning_uri(self, secret, email, issuer='RentalERP'):
        """
        Get provisioning URI for QR code generation.
        """
        pyotp_lib = self._get_pyotp()
        if not pyotp_lib:
            return None
        
        totp = self.get_totp(secret)
        if not totp:
            return None
        return totp.provisioning_uri(name=email, issuer_name=issuer)
    
    def generate_qr_code(self, secret, email):
        """
        Generate QR code for TOTP setup.
        """
        provisioning_uri = self.get_provisioning_uri(secret, email)
        if not provisioning_uri:
            logger.error('Cannot generate QR code: Provisioning URI is None (check if pyotp is installed)')
            return None
        
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = b64encode(buffer.getvalue()).decode()
            
            return f'data:image/png;base64,{img_str}'
        except Exception as e:
            logger.error(f'QR code generation failed: {str(e)}')
            return None
    
    def generate_backup_codes(self, count=10):
        """
        Generate backup codes for account recovery.
        
        Args:
            count: Number of backup codes to generate
        
        Returns:
            List of backup codes
        """
        codes = []
        for _ in range(count):
            code = secrets.token_hex(3).upper()  # 6 character hex code
            codes.append(code)
        return codes


class EmailVerificationManager:
    """Manage email verification for 2FA."""
    
    def generate_verification_code(self, length=6):
        """
        Generate a random verification code.
        
        Args:
            length: Length of code
        
        Returns:
            Numeric code as string
        """
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    def send_verification_email(self, user, code):
        """
        Send verification code to user's email.
        
        Args:
            user: User instance
            code: Verification code
        
        Returns:
            Boolean indicating if email was sent successfully
        """
        try:
            subject = 'RentalERP - Email Verification Code'
            message = f'''
Hello {user.first_name or user.email},

Your email verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
RentalERP Team
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            # Cache the code with 10 minute expiry
            cache.set(f'email_verification_{user.id}', code, 600)
            
            return True
        except Exception as e:
            logger.error(f'Failed to send verification email: {str(e)}')
            return False
    
    def verify_code(self, user, code):
        """
        Verify email verification code.
        
        Args:
            user: User instance
            code: Verification code to check
        
        Returns:
            Boolean indicating if code is valid
        """
        cached_code = cache.get(f'email_verification_{user.id}')
        return cached_code and cached_code == code


class MFAManager:
    """Manage Multi-Factor Authentication flows."""
    
    def __init__(self):
        """Initialize MFA manager."""
        self.totp_manager = TOTPManager()
        self.email_manager = EmailVerificationManager()
    
    def setup_totp(self, user):
        """
        Setup TOTP 2FA for user.
        
        Args:
            user: User instance
        
        Returns:
            Dictionary with secret and QR code
        """
        secret = self.totp_manager.generate_secret()
        qr_code = self.totp_manager.generate_qr_code(secret, user.email)
        backup_codes = self.totp_manager.generate_backup_codes()
        
        return {
            'secret': secret,
            'qr_code': qr_code,
            'backup_codes': backup_codes,
        }
    
    def enable_totp(self, user, secret, backup_codes):
        """
        Enable TOTP 2FA for user.
        
        Args:
            user: User instance
            secret: TOTP secret
            backup_codes: List of backup codes
        """
        try:
            # Store TOTP secret
            user.totp_secret = secret
            user.totp_enabled = True
            
            # Store backup codes (in production, encrypt and hash these)
            from django.contrib.auth.models import Group
            backup_code_str = '|'.join(backup_codes)
            
            # This would be better stored in a separate model
            # For now, we'll cache them temporarily
            cache.set(f'mfa_backup_codes_{user.id}', backup_codes, 86400 * 365)
            
            user.save()
            
            logger.info(f'TOTP 2FA enabled for user {user.email}')
            return True
        except Exception as e:
            logger.error(f'Failed to enable TOTP for user {user.email}: {str(e)}')
            return False
    
    def verify_mfa_method(self, user, method, code):
        """
        Verify MFA using specified method.
        
        Args:
            user: User instance
            method: MFA method ('totp' or 'email')
            code: Verification code
        
        Returns:
            Boolean indicating if verification successful
        """
        if method == 'totp':
            if not user.totp_enabled or not user.totp_secret:
                return False
            
            # Check if code is backup code
            backup_codes = cache.get(f'mfa_backup_codes_{user.id}')
            if backup_codes and code in backup_codes:
                # Remove used backup code
                backup_codes.remove(code)
                cache.set(f'mfa_backup_codes_{user.id}', backup_codes, 86400 * 365)
                return True
            
            # Verify TOTP code
            return self.totp_manager.verify_token(user.totp_secret, code)
        
        elif method == 'email':
            return self.email_manager.verify_code(user, code)
        
        return False
    
    def send_verification_code(self, user, method='email'):
        """
        Send verification code to user.
        
        Args:
            user: User instance
            method: Verification method ('email')
        
        Returns:
            Boolean indicating if code was sent successfully
        """
        if method == 'email':
            code = self.email_manager.generate_verification_code()
            return self.email_manager.send_verification_email(user, code)
        
        return False
    
    def get_backup_codes(self, user):
        """
        Get backup codes for user (for display during setup).
        
        Args:
            user: User instance
        
        Returns:
            List of backup codes or empty list
        """
        return cache.get(f'mfa_backup_codes_{user.id}', [])
    
    def disable_mfa(self, user, method='totp'):
        """
        Disable MFA for user.
        
        Args:
            user: User instance
            method: MFA method to disable
        """
        try:
            if method == 'totp':
                user.totp_enabled = False
                user.totp_secret = None
                cache.delete(f'mfa_backup_codes_{user.id}')
            
            user.save()
            logger.info(f'{method.upper()} 2FA disabled for user {user.email}')
            return True
        except Exception as e:
            logger.error(f'Failed to disable {method} 2FA for user {user.email}: {str(e)}')
            return False


# Global MFA manager instance
mfa_manager = MFAManager()
