"""
Data encryption utilities for Phase 10 - Secure sensitive fields.
Provides encryption/decryption for payment info, GSTIN, bank details, etc.
"""
import os
import logging
from cryptography.fernet import Fernet
from django.conf import settings

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manage encryption and decryption of sensitive data."""
    
    def __init__(self):
        """Initialize encryption manager with key from settings."""
        self.key = settings.ENCRYPTION_KEY
        if not self.key:
            logger.warning('ENCRYPTION_KEY not configured in settings')
            self.cipher = None
        else:
            try:
                self.cipher = Fernet(self.key)
            except Exception as e:
                logger.error(f'Failed to initialize encryption cipher: {str(e)}')
                self.cipher = None
    
    def encrypt(self, plaintext):
        """
        Encrypt plaintext data.
        
        Args:
            plaintext: String to encrypt
        
        Returns:
            Encrypted bytes (will be decoded to string for storage)
        """
        if not self.cipher:
            logger.warning('Encryption not available, returning plaintext')
            return plaintext
        
        if not plaintext:
            return None
        
        try:
            encrypted = self.cipher.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f'Encryption failed: {str(e)}')
            return None
    
    def decrypt(self, ciphertext):
        """
        Decrypt ciphertext data.
        
        Args:
            ciphertext: Encrypted string
        
        Returns:
            Decrypted plaintext string
        """
        if not self.cipher:
            logger.warning('Encryption not available, returning ciphertext')
            return ciphertext
        
        if not ciphertext:
            return None
        
        try:
            decrypted = self.cipher.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f'Decryption failed: {str(e)}')
            return None
    
    @staticmethod
    def generate_key():
        """
        Generate a new encryption key.
        
        Returns:
            New Fernet key (bytes)
        """
        return Fernet.generate_key()


class SecureFieldEncryption:
    """Custom field encryption for Django ORM models."""
    
    def __init__(self):
        """Initialize secure field encryption."""
        self.manager = EncryptionManager()
    
    def encrypt_value(self, value):
        """Encrypt a value for storage."""
        return self.manager.encrypt(str(value)) if value else None
    
    def decrypt_value(self, value):
        """Decrypt a value for retrieval."""
        return self.manager.decrypt(value) if value else None


# Global encryption manager instance
encryption_manager = EncryptionManager()


def mask_sensitive_data(data, pattern='****', show_last=4):
    """
    Mask sensitive data for display purposes.
    
    Args:
        data: The data to mask (string)
        pattern: Pattern to use for masking (default: ****)
        show_last: Number of characters to show at end (default: 4)
    
    Returns:
        Masked string
    """
    if not data or len(data) <= show_last:
        return pattern
    
    visible = data[-show_last:]
    return pattern + visible


def hash_sensitive_data(data):
    """
    Create a hash of sensitive data for comparison without storing plaintext.
    
    Args:
        data: The data to hash
    
    Returns:
        SHA256 hash as hexadecimal string
    """
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()


def validate_gstin(gstin):
    """
    Validate Indian GSTIN (Goods and Services Tax Identification Number).
    
    GSTIN Format: 2-digit state code + 10-digit GSTIN + 1-digit check digit = 15 characters
    
    Args:
        gstin: GSTIN string
    
    Returns:
        Boolean indicating if GSTIN is valid
    """
    if not gstin or len(gstin) != 15:
        return False
    
    if not gstin.isalnum():
        return False
    
    # Check if first 2 characters are digits (state code)
    if not gstin[:2].isdigit():
        return False
    
    # Check if last 1 character is alphanumeric (check digit)
    return True


def validate_ifsc_code(ifsc):
    """
    Validate Indian IFSC (Indian Financial System Code) code.
    
    IFSC Format: 4-letter bank code + 0 + 6-digit branch code = 11 characters
    
    Args:
        ifsc: IFSC code string
    
    Returns:
        Boolean indicating if IFSC is valid
    """
    if not ifsc or len(ifsc) != 11:
        return False
    
    # First 4 characters should be letters
    if not ifsc[:4].isalpha():
        return False
    
    # 5th character should be 0
    if ifsc[4] != '0':
        return False
    
    # Last 6 characters should be alphanumeric
    return ifsc[5:].isalnum()


def validate_pan(pan):
    """
    Validate Indian PAN (Permanent Account Number).
    
    PAN Format: AAAAA (5 letters) + 9999 (4 digits) + 9 (1 digit) + Z (1 letter) = 10 characters
    
    Args:
        pan: PAN string
    
    Returns:
        Boolean indicating if PAN is valid
    """
    if not pan or len(pan) != 10:
        return False
    
    if not pan.isalnum():
        return False
    
    # First 5 should be letters
    if not pan[:5].isalpha():
        return False
    
    # Next 4 should be digits
    if not pan[5:9].isdigit():
        return False
    
    # Last 1 should be letter
    return pan[9].isalpha()
def validate_upi_id(upi_id):
    """
    Validate UPI ID format.
    
    UPI Format: identifier@bankname
    Examples: user@paytm, 9876543210@ybl, myname@icici
    
    Args:
        upi_id: UPI ID string
    
    Raises:
        ValidationError if UPI ID is invalid
    """
    if not upi_id or not isinstance(upi_id, str):
        raise ValidationError("UPI ID cannot be empty")
    
    # Must contain @ symbol
    if '@' not in upi_id:
        raise ValidationError("UPI ID must contain @ symbol (e.g., user@paytm)")
    
    # Split by @
    parts = upi_id.split('@')
    if len(parts) != 2:
        raise ValidationError("UPI ID must have format: identifier@bankname")
    
    identifier, bank = parts
    
    # Identifier must be 3-256 characters
    if len(identifier) < 3 or len(identifier) > 256:
        raise ValidationError("UPI identifier must be 3-256 characters")
    
    # Bank name must be 2-64 characters
    if len(bank) < 2 or len(bank) > 64:
        raise ValidationError("UPI bank name must be 2-64 characters")
    
    # Basic alphanumeric check (allow dots, underscores in identifier)
    if not all(c.isalnum() or c in '._' for c in identifier):
        raise ValidationError("UPI identifier can only contain letters, numbers, dots, and underscores")
    
    if not bank.replace('.', '').isalnum():
        raise ValidationError("UPI bank name can only contain letters, numbers, and dots")
    
    return True




def mask_bank_account(account_number):
    """Mask bank account number for display."""
    return mask_sensitive_data(account_number, show_last=4)


def mask_gstin(gstin):
    """Mask GSTIN for display."""
    return mask_sensitive_data(gstin, show_last=5)


def mask_pan(pan):
    """Mask PAN for display."""
    return mask_sensitive_data(pan, show_last=4)


def mask_upi(upi_id):
    """Mask UPI ID for display."""
    # UPI format: identifier@bankname, mask identifier part
    if '@' in upi_id:
        parts = upi_id.split('@')
        return mask_sensitive_data(parts[0], show_last=2) + '@' + parts[1]
    return mask_sensitive_data(upi_id, show_last=2)
