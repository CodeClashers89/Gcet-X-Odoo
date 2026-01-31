# Phase 10: Security Testing Guide

## 🧪 Manual Security Testing Checklist

### 1. HTTPS/SSL Testing (Production Only)

```bash
# Test HTTP → HTTPS redirect
curl -I http://yourdomain.com
# Should see: 301 Moved Permanently to https://

# Test HSTS header
curl -I https://yourdomain.com
# Should see: Strict-Transport-Security: max-age=31536000

# Verify SSL certificate
openssl s_client -connect yourdomain.com:443 < /dev/null
```

---

### 2. CSRF Protection Testing

```bash
# Test missing CSRF token
curl -X POST \
  -d "field=value" \
  http://localhost:8000/form/submit/

# Expected: 403 Forbidden (CSRF token missing or incorrect)

# Test with invalid CSRF token
curl -X POST \
  -d "csrfmiddlewaretoken=invalid123&field=value" \
  http://localhost:8000/form/submit/

# Expected: 403 Forbidden (Invalid CSRF token)
```

---

### 3. XSS Prevention Testing

```bash
# Test via URL parameter
http://localhost:8000/search/?q=<script>alert(1)</script>

# Expected: 400 Bad Request (InputValidationMiddleware blocks)
# Check logs/security.log for injection attempt log

# Test via form field
POST /quotation/create/
name=<img src=x onerror="alert(1)">

# Expected: 400 Bad Request
```

---

### 4. SQL Injection Testing

```bash
# Test SQL injection in URL
http://localhost:8000/products/?search=' OR '1'='1

# Expected: 400 Bad Request (InputValidationMiddleware blocks)

# Test SQL injection in POST
curl -X POST \
  -d "vendor_name='; DROP TABLE vendors;--" \
  http://localhost:8000/vendor/create/

# Expected: 400 Bad Request
```

---

### 5. Rate Limiting Testing

```bash
# Test login rate limiting
for i in {1..6}; do
  curl -X POST \
    -d "username=user&password=wrong" \
    http://localhost:8000/accounts/login/
done

# First 5 requests: 200 OK (incorrect credentials)
# 6th request: 429 Too Many Requests

# Test password reset rate limiting
for i in {1..4}; do
  curl -X POST \
    -d "email=test@example.com" \
    http://localhost:8000/accounts/password-reset/
done

# First 3 requests: 200 OK
# 4th request: 429 Too Many Requests
```

---

### 6. Session Security Testing

```bash
# Test session expires after 1 hour
1. Log in: curl -c cookies.txt -b cookies.txt \
     -d "username=user&password=password" \
     http://localhost:8000/accounts/login/

2. Wait 61 minutes (or modify SESSION_COOKIE_AGE in tests)

3. Try to access protected page:
   curl -b cookies.txt \
     http://localhost:8000/dashboard/

# Expected: Redirect to login page (session expired)

# Test session doesn't persist after browser close
# (This is tested in browser by checking "Remember me" is unchecked)
```

---

### 7. Password Strength Testing

```python
# In Django shell
python manage.py shell

# Test minimum length (should fail)
>>> from django.contrib.auth.models import User
>>> from django.contrib.auth.password_validation import validate_password
>>> validate_password('Short1!@')  # Less than 12 chars
# ValidationError: ['This password is too short...']

# Test numeric-only password (should fail)
>>> validate_password('123456789012')
# ValidationError: ['This password is entirely numeric']

# Test common password (should fail)
>>> validate_password('Password123!')
# ValidationError: ['This password is too common...']

# Test valid password (should pass)
>>> validate_password('MySecurePass123!')
# No exception raised - valid!
```

---

### 8. Encryption Testing

```python
# In Django shell
python manage.py shell

>>> from rental_erp.encryption import encryption_manager, validate_gstin, mask_gstin

# Test encryption
>>> plaintext = '29AABCT1234M1Z0'
>>> encrypted = encryption_manager.encrypt(plaintext)
>>> print(encrypted)  # Should look like: gAAAAAB...

# Test decryption
>>> decrypted = encryption_manager.decrypt(encrypted)
>>> print(decrypted)
'29AABCT1234M1Z0'

# Test GSTIN validation
>>> validate_gstin('29AABCT1234M1Z0')
True

# Test data masking
>>> mask_gstin('29AABCT1234M1Z0')
'****1Z0'
```

---

### 9. 2FA/MFA Testing

```python
# In Django shell
python manage.py shell

>>> from rental_erp.mfa import mfa_manager
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.first()

# Setup TOTP
>>> setup = mfa_manager.setup_totp(user)
>>> print(setup['secret'])  # Secret key
>>> print(setup['qr_code'])[:50]  # QR code image
>>> print(setup['backup_codes'])  # Backup codes

# Enable TOTP
>>> mfa_manager.enable_totp(user, setup['secret'], setup['backup_codes'])

# Verify TOTP (get current code from authenticator app)
>>> from time import time
>>> import pyotp
>>> totp = pyotp.TOTP(setup['secret'])
>>> current_code = totp.now()
>>> mfa_manager.verify_mfa_method(user, 'totp', current_code)
True

# Test backup code
>>> mfa_manager.verify_mfa_method(user, 'totp', setup['backup_codes'][0])
True

# Test email verification
>>> mfa_manager.send_verification_code(user, method='email')
True

# User receives email with code (check logs or email)
>>> # Simulate user entering code
>>> mfa_manager.verify_mfa_method(user, 'email', '123456')
True or False (depends on actual code)
```

---

### 10. API Key Testing

```bash
# Test API without key
curl http://localhost:8000/api/products/

# Expected: 401 Unauthorized (require_api_key decorator)

# Test API with invalid key
curl -H "X-API-KEY: invalid_key_12345" \
  http://localhost:8000/api/products/

# Expected: 401 Unauthorized (Invalid API key)

# Test rate limiting on API
for i in {1..61}; do
  curl -H "X-API-KEY: sk_valid_key" \
    http://localhost:8000/api/products/
done

# First 60 requests: 200 OK
# 61st request: 429 Too Many Requests

# Check rate limit headers in response
curl -I -H "X-API-KEY: sk_valid_key" \
  http://localhost:8000/api/products/

# Expected headers:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 45
# X-RateLimit-Reset: 1609459200
```

---

### 11. Audit Logging Testing

```bash
# Trigger sensitive operation
curl -X POST \
  -d "action=approve&quotation_id=1" \
  -b "sessionid=valid_session" \
  http://localhost:8000/approval/approve/

# Check security log
tail logs/security.log

# Should see entry with:
# - Timestamp
# - User ID
# - IP Address
# - Action: POST /approval/approve/
# - Status: 200 or error code
# - User Agent
```

---

### 12. Security Headers Testing

```bash
# Test all security headers present
curl -I http://localhost:8000/

# Expected headers:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Referrer-Policy: same-origin
# Permissions-Policy: accelerometer=(), camera=(), microphone=(), geolocation=()
# Content-Security-Policy: default-src 'self'; ...
```

---

## 🤖 Automated Security Testing

### Django Security Checks
```bash
# Run all security checks
python manage.py check --deploy

# Expected output:
# System check identified no issues (0 silenced)
```

### Dependency Vulnerability Scanning
```bash
# Install pip-audit
pip install pip-audit

# Scan for vulnerabilities
pip audit

# Expected: 0 vulnerabilities (keep dependencies updated)
```

### Unit Tests for Security
```python
# In tests.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()

class SecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPassword123!'
        )
    
    # Test CSRF protection
    def test_csrf_protection(self):
        response = self.client.post('/form/submit/', {
            'field': 'value'
        })
        self.assertEqual(response.status_code, 403)
    
    # Test XSS prevention
    def test_xss_prevention(self):
        response = self.client.get('/search/?q=<script>alert(1)</script>')
        self.assertEqual(response.status_code, 400)
    
    # Test SQL injection prevention
    def test_sql_injection_prevention(self):
        response = self.client.get(
            "/search/?q=' OR '1'='1"
        )
        self.assertEqual(response.status_code, 400)
    
    # Test password validation
    def test_password_validation(self):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        # Too short
        with self.assertRaises(ValidationError):
            validate_password('Short1!')
        
        # Valid
        try:
            validate_password('ValidPassword123!')
        except ValidationError:
            self.fail('Valid password rejected')
    
    # Test rate limiting
    def test_rate_limiting(self):
        for i in range(5):
            response = self.client.post('/accounts/login/', {
                'username': 'testuser',
                'password': 'wrong'
            })
            self.assertIn(response.status_code, [200, 401, 403])
        
        # 6th attempt should be rate limited
        response = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'wrong'
        })
        self.assertEqual(response.status_code, 429)
    
    # Test session security
    def test_session_cookie_secure(self):
        self.client.login(username='testuser', password='TestPassword123!')
        response = self.client.get('/dashboard/')
        
        # Check session cookie has HttpOnly flag
        self.assertIn('sessionid', response.cookies)
        self.assertTrue(response.cookies['sessionid']['httponly'])
    
    # Test HTTPS redirect
    def test_https_redirect(self):
        # Only relevant in production (DEBUG=False)
        # Can mock by setting SECURE_SSL_REDIRECT=True in test
        pass
```

### Run Tests
```bash
python manage.py test
```

---

## 📊 Security Testing Report Template

Use this to document security testing results:

```markdown
# Security Testing Report - [Date]

## Executive Summary
- Total Tests: 12
- Passed: 12
- Failed: 0
- Critical Issues: 0
- High Issues: 0
- Medium Issues: 0
- Low Issues: 0

## Test Results

### HTTPS/SSL ✅
- HTTP redirect working: Yes
- HSTS header present: Yes
- SSL certificate valid: Yes

### CSRF Protection ✅
- Missing token blocked: Yes
- Invalid token blocked: Yes
- Valid token accepted: Yes

### XSS Prevention ✅
- Script tags blocked: Yes
- Event handlers blocked: Yes
- Path traversal blocked: Yes

### SQL Injection ✅
- SQL keywords blocked: Yes
- Quote escaping works: Yes
- Blind SQL injection blocked: Yes

### Rate Limiting ✅
- Login limited to 5/min: Yes
- Password reset limited to 3/min: Yes
- API limited to 60/min: Yes
- Returns 429 status: Yes

### Session Security ✅
- HttpOnly flag set: Yes
- Secure flag set (HTTPS): Yes
- SameSite policy enforced: Yes
- Timeout after 1 hour: Yes

### Password Security ✅
- Minimum 12 characters enforced: Yes
- Common passwords rejected: Yes
- Numeric-only rejected: Yes
- Argon2 hashing used: Yes

### Encryption ✅
- Data encrypted properly: Yes
- Decryption works: Yes
- GSTIN validation works: Yes
- Data masking works: Yes

### 2FA/MFA ✅
- TOTP setup works: Yes
- QR code generates: Yes
- Backup codes generate: Yes
- Email verification works: Yes

### API Security ✅
- API key required: Yes
- Invalid keys rejected: Yes
- Rate limiting works: Yes
- Headers returned: Yes

### Audit Logging ✅
- Sensitive ops logged: Yes
- User/IP/timestamp captured: Yes
- Log rotation works: Yes

### Security Headers ✅
- All headers present: Yes
- CSP restrictive: Yes
- X-Frame-Options DENY: Yes

### Dependency Scan ✅
- No vulnerabilities: Yes
- All packages current: Yes

## Recommendations
[List any findings and recommendations]

## Sign-off
Tested by: [Name]
Date: [Date]
Status: ✅ PASSED
```

---

## 🚨 Security Incident Response

If a security issue is found:

1. **Document the Issue**
   - What happened?
   - When did it happen?
   - Who was affected?
   - What data was exposed?

2. **Assess Severity**
   - Critical: Active exploitation, data breach
   - High: Vulnerability confirmed, no exploitation
   - Medium: Potential vulnerability, needs investigation
   - Low: Minor security issue

3. **Immediate Actions**
   - Isolate affected system if critical
   - Notify affected users if data breach
   - Disable affected features
   - Apply temporary workarounds

4. **Investigation**
   - Review logs (logs/security.log, logs/rental_erp.log)
   - Identify root cause
   - Check access patterns
   - Determine scope of impact

5. **Remediation**
   - Develop fix
   - Test fix thoroughly
   - Deploy fix
   - Verify fix works

6. **Post-Incident**
   - Document lessons learned
   - Update security procedures
   - Add tests to prevent recurrence
   - Communicate findings to team

---

## 🔗 Security Testing Resources

- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Django Security Docs](https://docs.djangoproject.com/en/stable/topics/security/)
- [CWE Top 25](https://cwe.mitre.org/top25/archive/2023/)
- [NIST Cybersecurity](https://www.nist.gov/cyberframework)

---

**Note**: Always test in a development or staging environment first. Never run security tests on production without proper approval and outside of maintenance windows.
