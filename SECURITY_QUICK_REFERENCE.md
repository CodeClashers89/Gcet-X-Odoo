# Phase 10 Security Features - Quick Reference Card

## 🔐 Security Modules Overview

| Module | Purpose | Key Classes | Lines |
|--------|---------|------------|-------|
| `security.py` | Middleware & request protection | 5 middleware + 2 decorators | 500+ |
| `encryption.py` | Data encryption & validation | EncryptionManager, validators | 400+ |
| `mfa.py` | 2FA/MFA implementation | TOTPManager, EmailManager, MFAManager | 400+ |
| `api_security.py` | API key & request signing | APIKeyManager, RequestSigning, RateLimit | 350+ |

---

## 🛡️ Security Middleware Enabled

```python
# Applied to ALL requests automatically:
SecurityHeadersMiddleware      → Adds protective headers
RateLimitMiddleware           → Prevents brute force (5/min login, 3/min reset)
AuditLoggingMiddleware        → Logs sensitive operations
InputValidationMiddleware     → Detects injection attempts
APISecurityMiddleware         → Validates API requests
```

---

## 🔑 Common Security Functions

### Encryption
```python
from rental_erp.encryption import encryption_manager

# Encrypt sensitive data
encrypted = encryption_manager.encrypt('secret_value')

# Decrypt
plaintext = encryption_manager.decrypt(encrypted)
```

### Data Masking (for display)
```python
from rental_erp.encryption import mask_bank_account, mask_gstin, mask_pan, mask_upi

mask_bank_account('1234567890')    # ****7890
mask_gstin('29AABCT1234M1Z0')      # ****1Z0
mask_pan('AAAPA5055K')              # ****5K
mask_upi('user@upi')                # **@upi
```

### Validation (India-specific)
```python
from rental_erp.encryption import validate_gstin, validate_ifsc_code, validate_pan

validate_gstin('29AABCT1234M1Z0')   # True/False
validate_ifsc_code('SBIN0012345')   # True/False
validate_pan('AAAPA5055K')           # True/False
```

### 2FA/MFA
```python
from rental_erp.mfa import mfa_manager

# Setup TOTP
setup = mfa_manager.setup_totp(user)  # Returns: secret, qr_code, backup_codes

# Enable 2FA
mfa_manager.enable_totp(user, setup['secret'], setup['backup_codes'])

# Verify 2FA code
if mfa_manager.verify_mfa_method(user, 'totp', '123456'):
    print("2FA verification successful")

# Send email code
mfa_manager.send_verification_code(user, method='email')
```

### API Security
```python
from rental_erp.api_security import (
    APIKeyManager,
    RequestSigningManager,
    require_api_key,
    apply_rate_limit
)

# Generate API key
api_key = APIKeyManager.generate_api_key()  # sk_xxxxx...

# Protect view with API key requirement
@require_api_key
@apply_rate_limit(max_requests=50, window=3600)
def my_api_view(request):
    pass
```

### Rate Limiting per View
```python
from rental_erp.security import rate_limit_view

@rate_limit_view(max_requests=10, period=3600)
def sensitive_view(request):
    pass  # Max 10 requests per hour per user
```

### Permission Checking
```python
from rental_erp.security import check_permission

@check_permission('can_approve_quotations')
def approve_quotation(request):
    pass  # Only users with this permission
```

---

## 📊 Rate Limits (Per IP)

| Endpoint | Limit | Window |
|----------|-------|--------|
| Login | 5 requests | 1 minute |
| Password Reset | 3 requests | 1 minute |
| API | 60 requests | 1 minute |
| Default | 120 requests | 1 minute |

**Response when exceeded**: `429 Too Many Requests`

---

## 🔒 Security Settings Enabled

| Setting | Value | Purpose |
|---------|-------|---------|
| `HTTPS` | Enabled (prod) | Encrypt data in transit |
| `HSTS` | 1 year | Force HTTPS for all requests |
| `CSP` | Restrictive | Prevent inline script injection |
| `CSRF` | Strict SameSite | Prevent cross-site request forgery |
| `Session Timeout` | 1 hour | Automatic logout after inactivity |
| `Min Password Length` | 12 chars | Stronger passwords |
| `Password Hasher` | Argon2 | Most secure hashing |
| `X-Frame-Options` | DENY | Prevent clickjacking |

---

## 📝 Audit Logging

**Automatically logs** POST/PUT/DELETE/PATCH on:
- /admin/
- /approval/
- /payment/
- /invoices/
- /settings/
- /users/

**Captured data**:
- User ID & IP Address
- HTTP Method & Path
- Response Status Code
- User Agent
- Timestamp

**Log location**: `logs/security.log` (rotating, 10MB max)

---

## 🚨 Input Validation

**InputValidationMiddleware automatically detects**:

| Attack Type | Examples | Response |
|------------|----------|----------|
| SQL Injection | UNION, SELECT, DELETE, DROP | 400 Bad Request |
| XSS | `<script>`, `onclick=`, `onerror=` | 400 Bad Request |
| Path Traversal | `../`, `..\` | 400 Bad Request |

---

## 🔑 Environment Variables Required

```bash
# Essential
SECRET_KEY              # Django secret (keep safe!)
DEBUG                   # False in production
ALLOWED_HOSTS           # Your domain

# Database
DB_ENGINE              # django.db.backends.postgresql
DB_NAME                # rental_erp
DB_USER                # postgres
DB_PASSWORD            # password

# Email
EMAIL_HOST             # smtp.gmail.com
EMAIL_PORT             # 587
EMAIL_HOST_USER        # your-email@gmail.com
EMAIL_HOST_PASSWORD    # app-password

# Encryption & Security
ENCRYPTION_KEY         # from cryptography.fernet.Fernet
TWO_FACTOR_AUTH_ENABLED  # True/False
REDIS_URL              # redis://localhost:6379/0 (optional)
```

**Generate Encryption Key**:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 📋 Integration Checklist

### For Vendors (Phase 5)
- [ ] Encrypt GSTIN field
- [ ] Encrypt bank account details
- [ ] Mask display values in templates
- [ ] Validate GSTIN format on form submission

### For Billing (Phase 7)
- [ ] Encrypt payment method (UPI, card, bank)
- [ ] Encrypt IFSC code
- [ ] Audit log all payment operations
- [ ] Rate limit payment endpoints

### For Authentication (Accounts)
- [ ] Add 2FA setup page to profile
- [ ] Modify login to request 2FA after password
- [ ] Show backup codes during setup
- [ ] Add MFA disable option

### For Admin Panel
- [ ] Add 2FA requirement
- [ ] View audit logs
- [ ] Monitor rate limit violations
- [ ] Check security logs

---

## 🧪 Testing Commands

```bash
# Django security checks
python manage.py check --deploy

# Check for dependency vulnerabilities
pip audit

# Run tests
python manage.py test

# View security log
tail -f logs/security.log

# Generate test data
python manage.py shell
>>> from rental_erp.encryption import encryption_manager
>>> encrypted = encryption_manager.encrypt('test@123')
>>> plaintext = encryption_manager.decrypt(encrypted)
>>> print(plaintext)
```

---

## 🚀 API Usage Examples

### Using API Key
```bash
curl -H "X-API-KEY: sk_xxxxx..." https://yourdomain.com/api/quotations/
```

### Response Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1609459200
```

### Signed Request
```bash
curl -X POST \
  -H "X-API-KEY: sk_xxxxx..." \
  -H "X-SIGNATURE: hash..." \
  -H "X-TIMESTAMP: 1609459200" \
  https://yourdomain.com/api/orders/
```

---

## 📂 Log Files

| Log File | Purpose | Level |
|----------|---------|-------|
| `logs/rental_erp.log` | Application logs | INFO/WARNING |
| `logs/security.log` | Security events | WARNING/ERROR |

**Rotation**: 10MB per file, 5 backup files kept

---

## ⚠️ Important Warnings

### DO NOT
- ❌ Commit `.env` file with secrets
- ❌ Set `DEBUG=True` in production
- ❌ Use plain passwords in code
- ❌ Log encrypted data (defeats purpose)
- ❌ Share ENCRYPTION_KEY publicly
- ❌ Disable CSRF protection
- ❌ Allow insecure cookies

### DO
- ✅ Use environment variables for secrets
- ✅ Rotate API keys quarterly
- ✅ Update Django & dependencies monthly
- ✅ Monitor security logs regularly
- ✅ Keep encryption key safe
- ✅ Enable 2FA for admin users
- ✅ Back up database regularly
- ✅ Run `pip audit` periodically

---

## 🔗 Related Files

- **Settings**: `rental_erp/settings.py` (150+ security lines)
- **Middleware**: `rental_erp/security.py` (500+ lines)
- **Encryption**: `rental_erp/encryption.py` (400+ lines)
- **2FA/MFA**: `rental_erp/mfa.py` (400+ lines)
- **API**: `rental_erp/api_security.py` (350+ lines)
- **Config Template**: `.env.example`
- **Documentation**: `SECURITY_IMPLEMENTATION.md`

---

## 📚 Next Steps (Remaining Tasks)

| Task | Status | Priority |
|------|--------|----------|
| 1. Enhanced Django security settings | ✅ DONE | CRITICAL |
| 2. Encrypt sensitive fields | 🔄 TODO | CRITICAL |
| 3. Rate limiting deployment | 🔄 TODO | HIGH |
| 4. Compliance middleware | 🔄 TODO | HIGH |
| 5. 2FA/MFA integration | 🔄 TODO | HIGH |
| 6. API key management | 🔄 TODO | MEDIUM |
| 7. Security testing & audit | 🔄 TODO | MEDIUM |

---

## 🆘 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| HTTPS not redirecting | Set `DEBUG=False` |
| Encryption fails | Generate & set ENCRYPTION_KEY |
| 2FA QR code not showing | Install `qrcode` package |
| Rate limiting not working | Check cache configuration |
| Audit logs empty | Verify middleware registered |
| CSRF token errors | Ensure `csrf_token` in form |

---

## 📞 Support Reference

- **Django Security Docs**: https://docs.djangoproject.com/en/stable/topics/security/
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **Cryptography Docs**: https://cryptography.io/
- **pyotp Documentation**: https://github.com/pyauth/pyotp
- **Django CSRF Docs**: https://docs.djangoproject.com/en/stable/ref/csrf/

---

**Phase 10 Status**: ✅ Task 1 Complete | 🔄 Tasks 2-7 Remaining
**Overall Progress**: 90% (9.5/11 phases complete)
