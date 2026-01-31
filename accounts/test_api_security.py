"""Security tests for API key management, request signing, and rate limiting."""
from types import SimpleNamespace
from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.utils import timezone

from accounts.models import User, APIKey
from rental_erp.api_security import (
    APIKeyManager,
    RequestSigningManager,
    RateLimitManager,
    require_api_key,
    verify_request_signature,
    apply_rate_limit,
)


class APISecurityTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='apiuser',
            email='apiuser@example.com',
            password='testpass123',
            role='customer',
            is_verified=True,
        )

    def test_api_key_generation_and_hashing(self):
        api_key = APIKeyManager.generate_api_key()
        key_hash = APIKeyManager.hash_api_key(api_key)

        self.assertTrue(api_key.startswith('sk_'))
        self.assertEqual(len(key_hash), 64)

    def test_api_key_validation_active(self):
        raw_key = APIKeyManager.generate_api_key()
        key_hash = APIKeyManager.hash_api_key(raw_key)

        api_key = APIKey.objects.create(
            user=self.user,
            name='Test Key',
            key_hash=key_hash,
            prefix=raw_key[:3],
            last_four=raw_key[-4:],
        )

        validated = APIKeyManager.validate_api_key(self.user, raw_key)
        self.assertIsNotNone(validated)
        self.assertEqual(validated.id, api_key.id)

    def test_api_key_validation_revoked(self):
        raw_key = APIKeyManager.generate_api_key()
        key_hash = APIKeyManager.hash_api_key(raw_key)

        api_key = APIKey.objects.create(
            user=self.user,
            name='Revoked Key',
            key_hash=key_hash,
            prefix=raw_key[:3],
            last_four=raw_key[-4:],
            revoked_at=timezone.now(),
        )

        validated = APIKeyManager.validate_api_key(self.user, raw_key)
        self.assertIsNone(validated)

    def test_require_api_key_decorator(self):
        raw_key = APIKeyManager.generate_api_key()
        key_hash = APIKeyManager.hash_api_key(raw_key)

        APIKey.objects.create(
            user=self.user,
            name='Decorator Key',
            key_hash=key_hash,
            prefix=raw_key[:3],
            last_four=raw_key[-4:],
        )

        @require_api_key
        def protected_view(request):
            return JsonResponse({'ok': True})

        # Missing key
        request = self.factory.get('/api/test')
        response = protected_view(request)
        self.assertEqual(response.status_code, 401)

        # Valid key
        request = self.factory.get('/api/test', HTTP_X_API_KEY=raw_key)
        response = protected_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(request, 'api_key_obj'))

    def test_request_signing(self):
        secret = 'test_secret'
        path = '/api/signed'
        method = 'POST'
        body = '{"hello": "world"}'
        timestamp = str(int(timezone.now().timestamp()))

        signature = RequestSigningManager.sign_request(
            secret, method, path, timestamp, body
        )

        @verify_request_signature
        def signed_view(request):
            return JsonResponse({'ok': True})

        request = self.factory.post(path, data=body, content_type='application/json')
        request.user = SimpleNamespace(api_secret=secret, __str__=lambda self: 'apiuser')
        request.META['HTTP_X_SIGNATURE'] = signature
        request.META['HTTP_X_TIMESTAMP'] = timestamp

        response = signed_view(request)
        self.assertEqual(response.status_code, 200)

    def test_api_rate_limiting(self):
        @apply_rate_limit(max_requests=2, window=60)
        def limited_view(request):
            return JsonResponse({'ok': True})

        request = self.factory.get('/api/limited')
        request.user = self.user

        # First two allowed
        response1 = limited_view(request)
        response2 = limited_view(request)
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

        # Third denied
        response3 = limited_view(request)
        self.assertEqual(response3.status_code, 429)
        self.assertIn('X-RateLimit-Limit', response3)
        self.assertIn('X-RateLimit-Remaining', response3)
        self.assertIn('X-RateLimit-Reset', response3)
