"""
Test 2FA functionality
"""
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from rental_erp.mfa import mfa_manager


class TwoFactorAuthenticationTests(TestCase):
    """Test Two-Factor Authentication features."""
    
    def setUp(self):
        """Set up test user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='customer',
            is_verified=True
        )
    
    def test_totp_secret_generation(self):
        """Test TOTP secret generation."""
        secret = mfa_manager.totp_manager.generate_secret()
        self.assertIsNotNone(secret)
        self.assertGreater(len(secret), 0)
        print(f"✓ TOTP secret generated: {secret[:8]}...")
    
    def test_totp_qr_code_generation(self):
        """Test QR code generation."""
        secret = mfa_manager.totp_manager.generate_secret()
        qr_code = mfa_manager.totp_manager.generate_qr_code(secret, self.user.email)
        self.assertIsNotNone(qr_code)
        self.assertTrue(qr_code.startswith('data:image/png;base64,'))
        print("✓ QR code generated successfully")
    
    def test_backup_codes_generation(self):
        """Test backup codes generation."""
        codes = mfa_manager.totp_manager.generate_backup_codes(10)
        self.assertEqual(len(codes), 10)
        # Each code should be 6 characters (3 hex bytes = 6 chars)
        for code in codes:
            self.assertEqual(len(code), 6)
        print(f"✓ Generated 10 backup codes: {codes[:2]}...")
    
    def test_totp_verification(self):
        """Test TOTP token verification."""
        secret = mfa_manager.totp_manager.generate_secret()
        
        # Generate current token
        totp = mfa_manager.totp_manager.get_totp(secret)
        current_token = totp.now()
        
        # Verify token
        is_valid = mfa_manager.totp_manager.verify_token(secret, current_token)
        self.assertTrue(is_valid)
        print(f"✓ TOTP token verified: {current_token}")
    
    def test_setup_2fa_page_loads(self):
        """Test 2FA setup page loads."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('accounts:setup_2fa'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Two-Factor Authentication')
        print("✓ 2FA setup page loads successfully")
    
    def test_2fa_enable_workflow(self):
        """Test enabling 2FA workflow."""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Step 1: Generate secret
        response = self.client.post(reverse('accounts:setup_2fa'), {
            'action': 'generate'
        })
        self.assertEqual(response.status_code, 200)
        
        # Check session has secret
        secret = self.client.session.get('totp_secret')
        self.assertIsNotNone(secret)
        print(f"✓ 2FA setup initiated, secret stored in session")
        
        # Step 2: Verify token and enable
        totp = mfa_manager.totp_manager.get_totp(secret)
        current_token = totp.now()
        
        response = self.client.post(reverse('accounts:setup_2fa'), {
            'action': 'verify',
            'token': current_token
        })
        
        # Should redirect to manage page
        self.assertEqual(response.status_code, 302)
        
        # Check user has 2FA enabled
        self.user.refresh_from_db()
        self.assertTrue(self.user.totp_enabled)
        self.assertIsNotNone(self.user.totp_secret)
        print("✓ 2FA enabled successfully")
    
    def test_login_with_2fa(self):
        """Test login flow with 2FA enabled."""
        # Enable 2FA for user
        secret = mfa_manager.totp_manager.generate_secret()
        backup_codes = mfa_manager.totp_manager.generate_backup_codes()
        mfa_manager.enable_totp(self.user, secret, backup_codes)
        
        # Attempt login
        response = self.client.post(reverse('accounts:login'), {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        # Should redirect to 2FA verification
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('accounts:verify_2fa')))
        print("✓ Login redirects to 2FA verification")
        
        # Verify 2FA code
        totp = mfa_manager.totp_manager.get_totp(secret)
        current_token = totp.now()
        
        response = self.client.post(reverse('accounts:verify_2fa'), {
            'token': current_token
        }, follow=False, QUERY_STRING='next=/accounts/profile/')
        
        # Should redirect to provided next URL (302)
        self.assertEqual(response.status_code, 302)
        print("✓ 2FA verification successful, login complete")
    
    def test_backup_code_usage(self):
        """Test using backup code for login."""
        # Enable 2FA for user
        secret = mfa_manager.totp_manager.generate_secret()
        backup_codes = mfa_manager.totp_manager.generate_backup_codes()
        mfa_manager.enable_totp(self.user, secret, backup_codes)
        
        # Get first backup code
        backup_code = backup_codes[0]
        
        # Use backup code
        is_valid = mfa_manager.verify_mfa_method(self.user, 'totp', backup_code)
        self.assertTrue(is_valid)
        print(f"✓ Backup code verified: {backup_code}")
        
        # Verify backup code is removed (can't be reused)
        is_valid_again = mfa_manager.verify_mfa_method(self.user, 'totp', backup_code)
        self.assertFalse(is_valid_again)
        print("✓ Backup code removed after use (one-time use)")
    
    def test_disable_2fa(self):
        """Test disabling 2FA."""
        # Enable 2FA first
        secret = mfa_manager.totp_manager.generate_secret()
        backup_codes = mfa_manager.totp_manager.generate_backup_codes()
        mfa_manager.enable_totp(self.user, secret, backup_codes)
        
        # Login
        self.client.login(email='test@example.com', password='testpass123')
        
        # Disable 2FA
        response = self.client.post(reverse('accounts:manage_2fa'), {
            'action': 'disable',
            'password': 'testpass123'
        })
        
        # Should redirect to profile
        self.assertEqual(response.status_code, 302)
        
        # Check user has 2FA disabled
        self.user.refresh_from_db()
        self.assertFalse(self.user.totp_enabled)
        self.assertIsNone(self.user.totp_secret)
        print("✓ 2FA disabled successfully")
