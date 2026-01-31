"""
API Security utilities for Phase 10 - Secure REST API endpoints.
Includes API key management, request signing, and rate limiting.
"""
import logging
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.apps import apps
from django.conf import settings
from functools import wraps
from django.http import JsonResponse

logger = logging.getLogger(__name__)
User = get_user_model()


class APIKeyManager:
    """Manage API keys for external API access."""
    
    @staticmethod
    def generate_api_key(prefix='sk_', length=32):
        """
        Generate a new API key.
        
        Args:
            prefix: Prefix for the API key
            length: Length of random portion
        
        Returns:
            API key string
        """
        random_part = secrets.token_urlsafe(length)
        api_key = f'{prefix}{random_part}'
        return api_key
    
    @staticmethod
    def hash_api_key(api_key):
        """
        Hash an API key for storage.
        
        Args:
            api_key: API key to hash
        
        Returns:
            SHA256 hash
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def validate_api_key(user, api_key, request=None):
        """
        Validate an API key for a user.
        
        Args:
            user: User instance
            api_key: API key to validate
        
        Returns:
            APIKey instance if valid, otherwise None
        """
        try:
            key_hash = APIKeyManager.hash_api_key(api_key)
            APIKey = apps.get_model('accounts', 'APIKey')
            now = timezone.now()
            qs = APIKey.objects.filter(
                key_hash=key_hash,
                revoked_at__isnull=True,
            ).filter(
                models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
            )

            if user:
                qs = qs.filter(user=user)

            api_key_obj = qs.first()
            if not api_key_obj:
                return None

            # Track usage if request provided
            if request:
                api_key_obj.last_used_at = now
                api_key_obj.last_used_ip = request.META.get('REMOTE_ADDR')
                api_key_obj.usage_count = api_key_obj.usage_count + 1
                api_key_obj.save(update_fields=['last_used_at', 'last_used_ip', 'usage_count'])

            return api_key_obj
        except Exception as e:
            logger.error(f'API key validation failed: {str(e)}')
            return None


class RequestSigningManager:
    """Manage request signing and validation for API security."""
    
    @staticmethod
    def sign_request(secret, method, path, timestamp, body=''):
        """
        Sign a request using HMAC-SHA256.
        
        Args:
            secret: Secret key for signing
            method: HTTP method
            path: Request path
            timestamp: Request timestamp
            body: Request body (optional)
        
        Returns:
            Signature as hexadecimal string
        """
        # Create canonical request
        canonical_request = f'{method}\n{path}\n{timestamp}\n{body}'
        
        # Sign with secret
        signature = hmac.new(
            secret.encode(),
            canonical_request.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    @staticmethod
    def verify_signature(secret, method, path, timestamp, body, signature):
        """
        Verify a request signature.
        
        Args:
            secret: Secret key for verification
            method: HTTP method
            path: Request path
            timestamp: Request timestamp
            body: Request body
            signature: Signature to verify
        
        Returns:
            Boolean indicating if signature is valid
        """
        expected_signature = RequestSigningManager.sign_request(
            secret, method, path, timestamp, body
        )
        
        return hmac.compare_digest(signature, expected_signature)


class RateLimitManager:
    """Manage rate limiting for API endpoints."""
    
    @staticmethod
    def get_rate_limit_key(identifier, endpoint):
        """
        Generate rate limit cache key.
        
        Args:
            identifier: User ID or API key
            endpoint: API endpoint path
        
        Returns:
            Cache key
        """
        return f'rate_limit_api:{identifier}:{endpoint}'
    
    @staticmethod
    def check_rate_limit(identifier, endpoint, max_requests=100, window=3600):
        """
        Check if request is within rate limit.
        
        Args:
            identifier: User ID or API key
            endpoint: API endpoint path
            max_requests: Maximum requests allowed
            window: Time window in seconds
        
        Returns:
            Tuple of (allowed, remaining_requests, reset_timestamp)
        """
        key = RateLimitManager.get_rate_limit_key(identifier, endpoint)
        
        current_count = cache.get(key, 0)
        
        if current_count >= max_requests:
            ttl = getattr(cache, 'ttl', None)
            if callable(ttl):
                reset_time = cache.ttl(key)
                if isinstance(reset_time, int):
                    reset_time = timezone.now() + timedelta(seconds=reset_time)
            else:
                reset_time = timezone.now() + timedelta(seconds=window)
            return (False, 0, reset_time)
        
        # Increment counter
        cache.set(key, current_count + 1, window)
        remaining = max_requests - current_count - 1
        reset_time = timezone.now() + timedelta(seconds=window)
        
        return (True, remaining, reset_time)
    
    @staticmethod
    def get_rate_limit_headers(allowed, remaining, reset_time):
        """
        Generate rate limit headers for response.
        
        Args:
            allowed: Whether request is allowed
            remaining: Remaining requests
            reset_time: Reset timestamp
        
        Returns:
            Dictionary of headers
        """
        headers = {
            'X-RateLimit-Limit': '100',
            'X-RateLimit-Remaining': str(max(0, remaining)),
            'X-RateLimit-Reset': str(int(reset_time.timestamp())),
        }
        
        if not allowed:
            headers['Retry-After'] = str(int(reset_time.timestamp()))
        
        return headers


def require_api_key(view_func):
    """
    Decorator to require API key authentication.
    
    Usage:
        @require_api_key
        def my_api_view(request):
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get API key from header
        header_name = getattr(settings, 'API_KEY_HEADER', 'HTTP_X_API_KEY')
        api_key = request.META.get(header_name)
        
        if not api_key:
            return JsonResponse(
                {'error': 'API key required'},
                status=401,
                headers={'WWW-Authenticate': 'Bearer realm="api"'}
            )
        
        # Validate API key
        api_key_obj = APIKeyManager.validate_api_key(None, api_key, request=request)
        if not api_key_obj:
            logger.warning(f'Invalid API key attempt: {api_key[:10]}...')
            return JsonResponse({'error': 'Invalid API key'}, status=401)
        
        # Attach user to request (would query database)
        request.api_key = api_key
        request.api_key_obj = api_key_obj
        request.api_key_owner = api_key_obj.user
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def verify_request_signature(view_func):
    """
    Decorator to verify request signature for API security.
    
    Usage:
        @verify_request_signature
        def my_api_view(request):
            pass
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get signature from header
        signature = request.META.get('HTTP_X_SIGNATURE')
        timestamp = request.META.get('HTTP_X_TIMESTAMP')
        
        if not signature or not timestamp:
            return JsonResponse(
                {'error': 'Signature and timestamp required'},
                status=400
            )
        
        # Validate timestamp (must be within 5 minutes)
        try:
            ts = int(timestamp)
            current_ts = int(datetime.now().timestamp())
            if abs(current_ts - ts) > 300:
                return JsonResponse(
                    {'error': 'Request timestamp expired'},
                    status=401
                )
        except ValueError:
            return JsonResponse({'error': 'Invalid timestamp'}, status=400)
        
        # Verify signature
        secret = getattr(request.user, 'api_secret', None)
        if not secret:
            return JsonResponse({'error': 'No API secret configured'}, status=401)
        
        body = request.body.decode() if request.body else ''
        is_valid = RequestSigningManager.verify_signature(
            secret,
            request.method,
            request.path,
            timestamp,
            body,
            signature
        )
        
        if not is_valid:
            logger.warning(f'Invalid signature for user {request.user}')
            return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def apply_rate_limit(max_requests=100, window=3600):
    """
    Decorator to apply rate limiting to an API endpoint.
    
    Args:
        max_requests: Maximum requests allowed
        window: Time window in seconds
    
    Usage:
        @apply_rate_limit(max_requests=50, window=3600)
        def my_api_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get identifier (user ID or API key)
            identifier = getattr(request, 'api_key', request.user.id)
            
            # Check rate limit
            allowed, remaining, reset_time = RateLimitManager.check_rate_limit(
                identifier,
                request.path,
                max_requests,
                window
            )
            
            if not allowed:
                return JsonResponse(
                    {'error': 'Rate limit exceeded'},
                    status=429,
                    headers=RateLimitManager.get_rate_limit_headers(
                        allowed, remaining, reset_time
                    )
                )
            
            response = view_func(request, *args, **kwargs)
            
            # Add rate limit headers
            headers = RateLimitManager.get_rate_limit_headers(
                allowed, remaining, reset_time
            )
            for key, value in headers.items():
                response[key] = value
            
            return response
        
        return wrapper
    return decorator
