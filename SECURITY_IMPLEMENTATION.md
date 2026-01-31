# Phase 10: Security & Compliance - Implementation Guide

## Overview
This document covers the security enhancements implemented in Phase 10 of the Rental Management System. All code follows enterprise security best practices and addresses OWASP Top 10 vulnerabilities.

---

## Security Configuration Summary

### Enabled Security Features

#### 1. HTTPS/SSL Configuration (Production)
```python
# In production (DEBUG=False):
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
```

#### 2. CSRF Protection
```python
CSRF_COOKIE_HTTPONLY = True      # Prevents JavaScript access
CSRF_COOKIE_SAMESITE = 'Strict'  # Only same-site requests
```

#### 3. Session Security
```python
SESSION_COOKIE_HTTPONLY = True    # HttpOnly flag
SESSION_COOKIE_SAMESITE = 'Strict'  # Strict SameSite policy
SESSION_COOKIE_AGE = 3600         # 1 hour timeout
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
```

#### 4. XSS Protection
```python
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'          # Prevent clickjacking
```

#### 5. Content Security Policy
```python
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net"),
    'style-src': ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net"),
    'img-src': ("'self'", "data:", "https:"),
}
```

#### 6. Password Security
- Minimum 12 characters (enhanced from 8)
- Argon2 hashing (most secure)
- Common password validation
- Numeric-only password rejection

#### 7. Security Middleware
- SecurityHeadersMiddleware: Adds protective headers
- RateLimitMiddleware: Prevents brute force
- AuditLoggingMiddleware: Logs sensitive operations
- InputValidationMiddleware: Detects injection attempts
- APISecurityMiddleware: Validates API requests

---

## Module Reference

### 1. `rental_erp/security.py` (500+ lines)

#### SecurityHeadersMiddleware
Adds security headers to all responses:
```python
# Response headers added automatically:
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: same-origin
Permissions-Policy: accelerometer=(), camera=(), microphone=(), geolocation=()
```

#### RateLimitMiddleware
Prevents brute force attacks:
```python
# Rate limits (per IP):
- /login, /signin: 5 requests/minute
- /password-reset: 3 requests/minute
- /api/*: 60 requests/minute
- Default: 120 requests/minute
```

**Response**: 429 Too Many Requests when limit exceeded

#### AuditLoggingMiddleware
Logs sensitive operations:
```python
# Logs POST/PUT/DELETE/PATCH on:
- /admin/
- /approval/
- /payment/
- /invoices/
- /settings/
- /users/

# Captured data:
- User ID
- IP Address
- User Agent
- HTTP Method & Path
- Response Status
- Timestamp
```

#### InputValidationMiddleware
Detects injection attempts:
```python
# Detects:
- SQL injection: UNION, SELECT, INSERT, DELETE, DROP
- XSS attacks: <script>, onclick=, onerror=
- Path traversal: ../, ..\

# Response: 400 Bad Request
```

#### Decorators

**@rate_limit_view(max_requests, period)**
```python
@rate_limit_view(max_requests=5, period=60)
def sensitive_view(request):
    # Max 5 requests per 60 seconds per IP
    pass
```

**@check_permission(permission_string)**
```python
@check_permission('can_approve_quotations')
def approve_quotation(request):
    # Only users with this permission can access
    pass
```

---

### 2. `rental_erp/encryption.py` (400+ lines)

#### EncryptionManager
Encrypt/decrypt sensitive data:
```python
from rental_erp.encryption import encryption_manager

# Encrypt
encrypted = encryption_manager.encrypt('sensitive_data')

# Decrypt
plaintext = encryption_manager.decrypt(encrypted)
```

#### Sensitive Data Masking
Display masked values:
```python
from rental_erp.encryption import mask_bank_account, mask_gstin

# Mask bank account (show last 4 digits)
masked = mask_bank_account('1234567890')  # Returns: ****7890

# Mask GSTIN (show last 5 digits)
masked = mask_gstin('29AABCT1234M1Z0')  # Returns: ****1Z0
```

#### India-Specific Validation
Validate Indian financial data:
```python
from rental_erp.encryption import (
    validate_gstin,
    validate_ifsc_code,
    validate_pan,
)

# GSTIN validation (15 characters)
if validate_gstin('29AABCT1234M1Z0'):
    print("Valid GSTIN")

# IFSC validation (11 characters: 4 letters + 0 + 6 alphanumeric)
if validate_ifsc_code('SBIN0012345'):
    print("Valid IFSC")

# PAN validation (10 characters: 5 letters + 4 digits + 1 digit + 1 letter)
if validate_pan('AAAPA5055K'):
    print("Valid PAN")
```

---

### 3. `rental_erp/mfa.py` (400+ lines)

#### TOTPManager
Time-based One-Time Password (2FA):
```python
from rental_erp.mfa import mfa_manager

# Setup TOTP
setup = mfa_manager.setup_totp(user)
# Returns: {
#     'secret': 'JBSWY3DPEBLW64TMMQXG22LJN5XX2IDN',
#     'qr_code': 'data:image/png;base64,...',
#     'backup_codes': ['ABC123', 'DEF456', ...]
# }

# Enable TOTP
mfa_manager.enable_totp(user, setup['secret'], setup['backup_codes'])

# Verify TOTP code
if mfa_manager.verify_mfa_method(user, 'totp', '123456'):
    print("TOTP code valid")
```

#### EmailVerificationManager
Email-based 2FA:
```python
# Send verification code
mfa_manager.send_verification_code(user, method='email')
# User receives 6-digit code via email

# Verify code
if mfa_manager.verify_mfa_method(user, 'email', '123456'):
    print("Email verification successful")
```

#### QR Code Generation
Display QR code in TOTP setup:
```python
# Generate QR code
qr_code = mfa_manager.totp_manager.generate_qr_code(secret, user.email)
# Returns: data:image/png;base64,iVBORw0KGgoAAAANS...

# Display in template:
# <img src="{{ qr_code }}" alt="Scan with authenticator app">
```

---

### 4. `rental_erp/api_security.py` (350+ lines)

#### API Key Management
```python
from rental_erp.api_security import APIKeyManager

# Generate API key
api_key = APIKeyManager.generate_api_key()
# Returns: sk_abcdef1234567890...

# Hash for storage
key_hash = APIKeyManager.hash_api_key(api_key)

# Validate
if APIKeyManager.validate_api_key(user, api_key):
    print("Valid API key")
```

#### Request Signing
Prevent request tampering:
```python
from rental_erp.api_security import RequestSigningManager

# Sign request
signature = RequestSigningManager.sign_request(
    secret='user_secret',
    method='POST',
    path='/api/quotations/',
    timestamp='1234567890',
    body='{"name": "test"}'
)

# Verify signature
is_valid = RequestSigningManager.verify_signature(
    secret='user_secret',
    method='POST',
    path='/api/quotations/',
    timestamp='1234567890',
    body='{"name": "test"}',
    signature=signature
)
```

#### API Decorators
```python
from rental_erp.api_security import (
    require_api_key,
    verify_request_signature,
    apply_rate_limit
)

# Require API key
@require_api_key
def api_quotations(request):
    # Only accessible with X-API-KEY header
    pass

# Verify signature
@verify_request_signature
def api_create_order(request):
    # Requires X-SIGNATURE and X-TIMESTAMP headers
    pass

# Rate limit API
@apply_rate_limit(max_requests=50, window=3600)
def api_list_products(request):
    # Max 50 requests per hour
    pass
```

#### Rate Limit Headers
Responses include rate limit information:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1609459200
```

---

## Environment Configuration

### Setup `.env` File
```bash
# Copy template
cp .env.example .env

# Edit .env with production values:
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (if using PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=rental_erp
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432

# Email configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Encryption
ENCRYPTION_KEY=<generated-from-cryptography.fernet.Fernet>

# 2FA Settings
TWO_FACTOR_AUTH_ENABLED=True
OTP_TOTP_ISSUER=RentalERP

# Redis (for caching)
REDIS_URL=redis://localhost:6379/0
```

### Generate Encryption Key
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Usage Examples

### Example 1: Protecting a View with Rate Limiting
```python
from django.shortcuts import render
from rental_erp.security import rate_limit_view

@rate_limit_view(max_requests=10, period=3600)
def my_report(request):
    # Users can generate max 10 reports per hour
    return render(request, 'my_report.html')
```

### Example 2: Encrypting Sensitive User Data
```python
from django.contrib.auth import get_user_model
from rental_erp.encryption import encryption_manager, validate_gstin

User = get_user_model()

# When saving vendor profile
if request.method == 'POST':
    gstin = request.POST.get('gstin')
    
    # Validate format
    if validate_gstin(gstin):
        # Encrypt for storage
        encrypted_gstin = encryption_manager.encrypt(gstin)
        vendor.gstin = encrypted_gstin
        vendor.save()

# When displaying vendor info
vendor = User.objects.get(id=1)
if vendor.gstin:
    # Decrypt for display (in views) or mask (in templates)
    decrypted = encryption_manager.decrypt(vendor.gstin)
    # Or use masked version for lists
    masked = mask_gstin(decrypted)
```

### Example 3: Implementing 2FA
```python
from django.contrib.auth import authenticate
from rental_erp.mfa import mfa_manager

# During login
user = authenticate(username=username, password=password)
if user:
    if user.totp_enabled:
        # Redirect to 2FA verification
        request.session['pending_2fa'] = user.id
        return redirect('verify_2fa')

# Verify 2FA code
user = User.objects.get(id=request.session['pending_2fa'])
if mfa_manager.verify_mfa_method(user, 'totp', otp_code):
    # Login successful
    login(request, user)
    del request.session['pending_2fa']
```

### Example 4: API Security
```python
from django.http import JsonResponse
from rental_erp.api_security import (
    require_api_key,
    apply_rate_limit
)

@require_api_key
@apply_rate_limit(max_requests=100, window=3600)
def api_get_products(request):
    products = Product.objects.all().values()
    return JsonResponse({
        'data': list(products),
        'count': len(products)
    })
```

---

## Security Best Practices

### 1. Password Management
- ✅ Minimum 12 characters
- ✅ Mix of uppercase, lowercase, numbers, special characters
- ✅ Avoid common passwords
- ✅ Use Argon2 hashing
- ✅ Force password reset every 90 days (implement in Task 2)

### 2. API Keys
- ✅ Generate with `APIKeyManager.generate_api_key()`
- ✅ Hash before storage: `APIKeyManager.hash_api_key(api_key)`
- ✅ Rotate quarterly
- ✅ Revoke immediately if compromised
- ✅ Monitor usage patterns

### 3. Data Encryption
- ✅ Use Fernet for encryption (`EncryptionManager`)
- ✅ Encrypt PII: bank accounts, GSTIN, IFSC, PAN, UPI
- ✅ Never log encrypted data
- ✅ Keep encryption key in environment variables
- ✅ Rotate encryption key annually

### 4. Authentication
- ✅ Enforce HTTPS
- ✅ Use secure session cookies (HttpOnly, Secure, SameSite)
- ✅ Implement 2FA for admin users
- ✅ Log authentication failures
- ✅ Rate limit login attempts (5/minute)

### 5. Authorization
- ✅ Check permissions in every view (`@check_permission`)
- ✅ Use role-based access control (already implemented in Phase 5)
- ✅ Never trust user input
- ✅ Validate on both client and server

### 6. Logging & Auditing
- ✅ Log all sensitive operations (AuditLoggingMiddleware)
- ✅ Include timestamp, user, IP, action, result
- ✅ Store logs securely
- ✅ Rotate logs regularly (RotatingFileHandler: 10MB files, 5 backups)
- ✅ Monitor for suspicious patterns

### 7. Dependency Security
- Keep Django and packages updated
- Run `pip audit` to check for vulnerabilities
- Use requirements.txt with pinned versions
- Regularly update packages (Task 7)

---

## Testing Security

### Manual Testing Checklist

- [ ] Test HTTPS redirect (DEBUG=False)
- [ ] Test CSRF protection with invalid token
- [ ] Test XSS with `<script>alert(1)</script>` in inputs
- [ ] Test SQL injection with `' OR '1'='1`
- [ ] Test rate limiting on login (5 fails/minute)
- [ ] Test session expiry (1 hour timeout)
- [ ] Test API key validation
- [ ] Test 2FA setup and verification
- [ ] Test sensitive data masking
- [ ] Test audit logging

### Automated Testing
```bash
# Check for vulnerabilities
pip audit

# Run Django security checks
python manage.py check --deploy

# Run tests
python manage.py test
```

---

## Monitoring & Alerts

### Important Metrics to Monitor
1. **Failed Login Attempts**: Alert if > 10 in 1 hour per user
2. **Rate Limit Violations**: Track by IP address
3. **Encryption Failures**: Log immediately
4. **Sensitive Data Access**: Audit trail of GSTIN, bank details, etc.
5. **API Key Usage**: Monitor for unusual patterns
6. **Session Timeouts**: Track forced logouts

### Log Files
```
# General application logs
logs/rental_erp.log

# Security-specific logs
logs/security.log
```

---

## Compliance Checklist

- [ ] GDPR data deletion capability (Task 4)
- [ ] India DPA data localization (Task 4)
- [ ] PCI DSS for payment data (Task 2)
- [ ] Privacy policy and terms of service
- [ ] Data retention policies (2555 days for India)
- [ ] Consent tracking for communications
- [ ] Incident response plan
- [ ] Data breach notification process
- [ ] Regular security audits (Task 7)

---

## Troubleshooting

### Issue: HTTPS Redirect Not Working
**Solution**: Ensure `DEBUG=False` and `SECURE_SSL_REDIRECT=True` in settings

### Issue: Session Expires Too Quickly
**Solution**: Increase `SESSION_COOKIE_AGE` in settings (currently 3600 seconds = 1 hour)

### Issue: API Key Validation Fails
**Solution**: Ensure API key is sent in `X-API-KEY` header with correct format

### Issue: 2FA Not Working
**Solution**: Ensure `qrcode` and `pyotp` packages are installed:
```bash
pip install qrcode pyotp
```

### Issue: Encryption Key Error
**Solution**: Generate and set ENCRYPTION_KEY in .env:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Next Phase Tasks

**Task 2**: Encrypt sensitive database fields
**Task 3**: Deploy rate limiting on authentication endpoints
**Task 4**: Add compliance middleware for GDPR/India DPA
**Task 5**: Integrate 2FA into login workflow
**Task 6**: Build API key management interface
**Task 7**: Conduct security audit and testing

---

## Additional Resources

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GDPR Compliance Guide](https://gdpr-info.eu/)
- [PCI DSS Standard](https://www.pcisecuritystandards.org/)
- [India Data Protection Act](https://www.meity.gov.in/content/data-protection-0)

---

## Support

For security issues or questions:
1. Review the relevant module (security.py, encryption.py, mfa.py, api_security.py)
2. Check the Django logs (logs/security.log)
3. Run Django system checks: `python manage.py check --deploy`
4. Consult [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)

**DO NOT** commit sensitive data (API keys, secrets, encryption keys) to version control. Use environment variables.
