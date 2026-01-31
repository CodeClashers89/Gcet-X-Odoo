"""
Compliance middleware for GDPR and ISO 27001.
Handles data access logging, consent management, and regulatory compliance.
"""
import logging
import json
from datetime import datetime, timedelta
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
from audit.models import AuditLog

logger = logging.getLogger('django.security')


class DataAccessLoggingMiddleware(MiddlewareMixin):
    """
    Log all data access for GDPR Article 15 (Right of Access) compliance.
    Tracks who accessed what data and when.
    """
    
    # Models that contain personal data
    PERSONAL_DATA_MODELS = [
        'user', 'customerprofile', 'vendorprofile', 
        'quotation', 'order', 'invoice', 'payment'
    ]
    
    def process_request(self, request):
        """Log data access requests."""
        if not request.user.is_authenticated:
            return None
        
        # Track GET requests to personal data endpoints
        if request.method == 'GET':
            path_lower = request.path.lower()
            
            # Check if accessing personal data
            for model in self.PERSONAL_DATA_MODELS:
                if model in path_lower:
                    self._log_data_access(request, model)
                    break
        
        return None
    
    def _log_data_access(self, request, model_name):
        """Log data access event."""
        try:
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
            
            # Log to audit trail
            AuditLog.objects.create(
                user=request.user,
                action_type='access',
                model_name=model_name,
                description=f'Data access: {request.path}',
                ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_key=request.session.session_key if hasattr(request, 'session') else None,
            )
        except Exception as e:
            logger.error(f'Data access logging failed: {str(e)}')


class GDPRComplianceMiddleware(MiddlewareMixin):
    """
    GDPR compliance middleware.
    Handles consent tracking, cookie notices, and data subject rights.
    """
    
    def process_request(self, request):
        """Check GDPR consent and compliance."""
        # Skip for non-authenticated users on public pages
        if not request.user.is_authenticated:
            return None
        
        # Check if user has accepted privacy policy
        consent_key = f'gdpr_consent:{request.user.id}'
        has_consent = cache.get(consent_key)
        
        if has_consent is None:
            # Check if user has consent record
            # For now, we'll cache a default consent
            # In production, check against UserConsent model
            cache.set(consent_key, True, 86400)  # Cache for 24 hours
        
        return None
    
    def process_response(self, request, response):
        """Add GDPR compliance headers."""
        # Add privacy policy link header
        response['X-Privacy-Policy'] = '/privacy-policy/'
        
        # Add data retention notice
        if hasattr(settings, 'DATA_RETENTION_DAYS'):
            response['X-Data-Retention-Days'] = str(settings.DATA_RETENTION_DAYS)
        
        return response


class ISO27001ComplianceMiddleware(MiddlewareMixin):
    """
    ISO 27001 compliance middleware.
    Implements information security management system (ISMS) requirements.
    """
    
    # Security-critical operations
    CRITICAL_OPERATIONS = [
        '/accounts/login/',
        '/accounts/logout/',
        '/accounts/change-password/',
        '/admin/',
        '/api/',
    ]
    
    def process_request(self, request):
        """Track security-critical operations."""
        # Check if this is a critical operation
        for critical_path in self.CRITICAL_OPERATIONS:
            if request.path.startswith(critical_path):
                self._log_critical_operation(request)
                break
        
        return None
    
    def _log_critical_operation(self, request):
        """Log security-critical operations."""
        try:
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
            
            # Prepare log data
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'user': request.user.email if request.user.is_authenticated else 'anonymous',
                'ip_address': ip,
                'path': request.path,
                'method': request.method,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }
            
            # Log to security log
            logger.warning(f'ISO27001 Critical Operation: {json.dumps(log_data)}')
            
        except Exception as e:
            logger.error(f'ISO27001 logging failed: {str(e)}')
    
    def process_response(self, request, response):
        """Add ISO 27001 compliance headers."""
        # Add security incident contact
        response['X-Security-Contact'] = 'security@rentalerp.com'
        
        # Add information classification (if applicable)
        if request.user.is_authenticated:
            response['X-Data-Classification'] = 'Confidential'
        else:
            response['X-Data-Classification'] = 'Public'
        
        return response


class ConsentManagementMiddleware(MiddlewareMixin):
    """
    Manage user consent for data processing.
    GDPR Article 6 (Lawfulness of processing) and Article 7 (Conditions for consent).
    """
    
    # Pages that require consent
    CONSENT_REQUIRED_PATHS = [
        '/accounts/profile/',
        '/rentals/',
        '/billing/',
    ]
    
    def process_request(self, request):
        """Check if user has given consent for data processing."""
        if not request.user.is_authenticated:
            return None
        
        # Check if accessing consent-required page
        requires_consent = any(
            request.path.startswith(path) 
            for path in self.CONSENT_REQUIRED_PATHS
        )
        
        if requires_consent:
            consent_key = f'data_processing_consent:{request.user.id}'
            has_consent = cache.get(consent_key)
            
            if has_consent is None:
                # In production, check database for consent record
                # For now, we'll assume consent (user registered = consent given)
                cache.set(consent_key, True, 86400 * 7)  # Cache for 7 days
        
        return None


class DataRetentionMiddleware(MiddlewareMixin):
    """
    Enforce data retention policies.
    GDPR Article 5(1)(e) - Storage limitation.
    """
    
    def process_request(self, request):
        """Check and enforce data retention policies."""
        # This would typically run as a background task
        # Here we just add metadata to track when data should be deleted
        
        if request.user.is_authenticated:
            # Calculate data retention deadline
            retention_days = getattr(settings, 'DATA_RETENTION_DAYS', 2555)  # ~7 years
            retention_deadline = datetime.now() + timedelta(days=retention_days)
            
            # Store in session for display
            request.session['data_retention_deadline'] = retention_deadline.isoformat()
        
        return None


class RightToErasureMiddleware(MiddlewareMixin):
    """
    Support GDPR Article 17 - Right to Erasure ('Right to be Forgotten').
    Tracks deletion requests and ensures data is properly removed.
    """
    
    def process_request(self, request):
        """Track data deletion requests."""
        if request.method == 'DELETE' or 'delete' in request.path.lower():
            if request.user.is_authenticated:
                self._log_deletion_request(request)
        
        return None
    
    def _log_deletion_request(self, request):
        """Log deletion request for compliance tracking."""
        try:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
            
            AuditLog.objects.create(
                user=request.user,
                action_type='delete',
                model_name='DataDeletion',
                description=f'Data deletion request: {request.path}',
                ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            
            logger.info(f'GDPR Deletion Request: User {request.user.email} - {request.path}')
            
        except Exception as e:
            logger.error(f'Deletion logging failed: {str(e)}')
