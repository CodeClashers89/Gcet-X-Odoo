"""
Security middleware for Phase 10 - Enhanced authentication and compliance.
Includes request validation, rate limiting, audit logging, and security checks.
"""
import logging
import hashlib
import json
from datetime import datetime
from functools import wraps
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.core.cache import cache
from django.contrib.auth import get_user_model
from audit.models import AuditLog
import re

logger = logging.getLogger('django.security')
User = get_user_model()


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add additional security headers to all responses."""
    
    def process_response(self, request, response):
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'same-origin'
        
        # Feature Policy / Permissions Policy
        response['Permissions-Policy'] = (
            'accelerometer=(), camera=(), microphone=(), geolocation=()'
        )
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Implement rate limiting to prevent brute force attacks."""
    
    # Rate limit configuration (requests per minute)
    RATE_LIMITS = {
        'login': 5,
        'password_reset': 3,
        'api': 60,
        'default': 120,
    }
    
    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_rate_limit_key(self, request):
        """Generate cache key for rate limiting."""
        ip = self.get_client_ip(request)
        path = request.path
        return f'rate_limit:{ip}:{path}'
    
    def process_request(self, request):
        """Check rate limits before processing request."""
        # Determine rate limit based on path
        path = request.path
        
        if 'login' in path or 'signin' in path:
            limit = self.RATE_LIMITS['login']
        elif 'password-reset' in path or 'forgot-password' in path:
            limit = self.RATE_LIMITS['password_reset']
        elif path.startswith('/api/'):
            limit = self.RATE_LIMITS['api']
        else:
            limit = self.RATE_LIMITS['default']
        
        # Get rate limit key and current count
        key = self.get_rate_limit_key(request)
        count = cache.get(key, 0)
        
        # Check if limit exceeded
        if count >= limit:
            logger.warning(f'Rate limit exceeded for {self.get_client_ip(request)} on {path}')
            return HttpResponse('Rate limit exceeded. Please try again later.', status=429)
        
        # Increment counter
        cache.set(key, count + 1, 60)  # Reset every 60 seconds
        
        return None


class AuditLoggingMiddleware(MiddlewareMixin):
    """Log sensitive operations for compliance and audit purposes."""
    
    SENSITIVE_PATHS = [
        '/admin/',
        '/approval/',
        '/payment/',
        '/invoices/',
        '/settings/',
        '/accounts/password/',
        '/users/',
    ]
    
    SENSITIVE_METHODS = ['POST', 'PUT', 'DELETE', 'PATCH']
    
    def is_sensitive_operation(self, request):
        """Check if request is a sensitive operation."""
        if request.method not in self.SENSITIVE_METHODS:
            return False
        
        path = request.path
        return any(path.startswith(p) for p in self.SENSITIVE_PATHS)
    
    def get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def process_request(self, request):
        """Log sensitive requests."""
        if self.is_sensitive_operation(request):
            request._audit_log_ip = self.get_client_ip(request)
            request._audit_log_timestamp = datetime.now()
        return None
    
    def process_response(self, request, response):
        """Log sensitive operations after processing."""
        if not self.is_sensitive_operation(request):
            return response
        
        # Only log if user is authenticated
        if request.user.is_authenticated:
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action=f'{request.method} {request.path}',
                    resource_type='system',
                    resource_id=None,
                    change_details=f'Status: {response.status_code}',
                    ip_address=getattr(request, '_audit_log_ip', ''),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                )
            except Exception as e:
                logger.error(f'Failed to create audit log: {str(e)}')
        
        return response


class InputValidationMiddleware(MiddlewareMixin):
    """Validate and sanitize user inputs to prevent injection attacks."""
    
    # Patterns to detect potential injection attempts
    INJECTION_PATTERNS = [
        r'(?i)(union|select|insert|update|delete|drop|create)',  # SQL injection
        r'(?i)(<script|javascript:|onerror=|onclick=)',  # XSS attempts
        r'(?i)(%00|\.\.\/|\.\.\\)',  # Path traversal
    ]
    
    def check_injection_attempts(self, data):
        """Check for potential injection attempts in data."""
        if isinstance(data, str):
            for pattern in self.INJECTION_PATTERNS:
                if re.search(pattern, data):
                    return True
        elif isinstance(data, dict):
            for value in data.values():
                if self.check_injection_attempts(value):
                    return True
        elif isinstance(data, (list, tuple)):
            for item in data:
                if self.check_injection_attempts(item):
                    return True
        return False
    
    def process_request(self, request):
        """Validate inputs."""
        # Check GET parameters
        if request.GET and self.check_injection_attempts(dict(request.GET)):
            logger.warning(f'Potential injection attack from {request.META.get("REMOTE_ADDR")} on {request.path}')
            return HttpResponse('Invalid input detected', status=400)
        
        # Check POST data
        if request.method == 'POST' and request.POST:
            if self.check_injection_attempts(dict(request.POST)):
                logger.warning(f'Potential injection attack from {request.META.get("REMOTE_ADDR")} on {request.path}')
                return HttpResponse('Invalid input detected', status=400)
        
        return None


class APISecurityMiddleware(MiddlewareMixin):
    """Secure API endpoints with authentication and validation."""
    
    def process_request(self, request):
        """Validate API requests."""
        if not request.path.startswith('/api/'):
            return None
        
        # Check for API key if required
        from django.conf import settings
        from rental_erp.api_security import APIKeyManager

        header_name = getattr(settings, 'API_KEY_HEADER', 'HTTP_X_API_KEY')
        api_key = request.META.get(header_name)
        if api_key:
            try:
                api_key_obj = APIKeyManager.validate_api_key(None, api_key, request=request)
                if not api_key_obj:
                    raise ValueError('Invalid API key')
                request.api_key = api_key
                request.api_key_obj = api_key_obj
                request.api_key_owner = api_key_obj.user
            except Exception as e:
                logger.warning(f'Invalid API key attempt: {str(e)}')
                return JsonResponse({'error': 'Invalid API key'}, status=401)
        
        return None


def rate_limit_view(max_requests=10, period=3600):
    """
    Decorator to rate limit individual views.
    
    Args:
        max_requests: Maximum number of requests allowed
        period: Time period in seconds
    
    Usage:
        @rate_limit_view(max_requests=5, period=60)
        def my_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            
            # Generate cache key
            key = f'rate_limit_view:{ip}:{view_func.__name__}'
            
            # Check and update counter
            count = cache.get(key, 0)
            if count >= max_requests:
                logger.warning(f'View rate limit exceeded for {ip} on {view_func.__name__}')
                retry_after = period
                accept_header = request.headers.get('Accept', '')
                is_api_request = request.path.startswith('/api/') or 'application/json' in accept_header

                if is_api_request:
                    response = JsonResponse(
                        {
                            'error': 'rate_limit_exceeded',
                            'message': 'Too many requests. Please try again later.',
                            'retry_after_seconds': retry_after,
                        },
                        status=429,
                    )
                else:
                    response = render(
                        request,
                        'rate_limit_exceeded.html',
                        {
                            'retry_after_seconds': retry_after,
                            'max_requests': max_requests,
                            'period_seconds': period,
                        },
                        status=429,
                    )

                response['Retry-After'] = str(retry_after)
                return response
            
            cache.set(key, count + 1, period)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def check_permission(permission_string):
    """
    Decorator to check specific permissions.
    
    Usage:
        @check_permission('can_approve_quotations')
        def approve_quotation(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponse('Unauthorized', status=401)
            
            if not request.user.has_perm(permission_string):
                logger.warning(f'Permission denied for {request.user} on {view_func.__name__}')
                return HttpResponse('Permission denied', status=403)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator
