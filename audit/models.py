from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    Comprehensive audit trail for all critical ERP state changes.
    
    Business Use: Legal compliance, dispute resolution, and system transparency.
    Tracks WHO changed WHAT, WHEN, and WHY across the entire ERP system.
    
    Critical for:
    - Fraud detection (who modified invoice amounts?)
    - Dispute resolution (when did order status change?)
    - Compliance (GST audit trail)
    - Performance analysis (how long does order confirmation take?)
    
    Examples of tracked changes:
    - Quotation: Draft → Confirmed
    - Order: Confirmed → In Progress
    - Invoice: Draft → Sent → Paid
    - Payment: Pending → Success
    - Product: Published → Unpublished
    """
    
    ACTION_CHOICES = [
        ('create', 'Created'),         # New record created
        ('update', 'Updated'),         # Existing record modified
        ('delete', 'Deleted'),         # Record deleted
        ('state_change', 'State Changed'),  # Workflow state transition
        ('payment', 'Payment Recorded'),    # Payment transaction
        ('login', 'User Login'),            # User authentication
        ('logout', 'User Logout'),
    ]
    
    # Who performed the action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='audit_logs',
        help_text="User who performed the action (null if system-automated)"
    )
    
    user_email = models.EmailField(
        help_text="Email of user (stored for record even if user deleted)"
    )
    
    user_role = models.CharField(
        max_length=20,
        help_text="User's role at time of action (customer/vendor/admin)"
    )
    
    # What was changed
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text="Type of action performed"
    )
    
    model_name = models.CharField(
        max_length=100,
        help_text="Django model that was affected (e.g., 'RentalOrder', 'Invoice')"
    )
    
    object_id = models.CharField(
        max_length=50,
        help_text="ID of the affected record"
    )
    
    object_repr = models.CharField(
        max_length=255,
        help_text="String representation of the object (e.g., 'RO-2026-0001')"
    )
    
    # Change details
    field_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Specific field changed (e.g., 'status', 'paid_amount')"
    )
    
    old_value = models.TextField(
        blank=True,
        null=True,
        help_text="Previous value before change"
    )
    
    new_value = models.TextField(
        blank=True,
        null=True,
        help_text="New value after change"
    )
    
    # Additional context
    description = models.TextField(
        help_text="Human-readable description of the action"
    )
    
    # Request metadata
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="User's IP address"
    )
    
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Browser/device information"
    )
    
    # Session tracking
    session_key = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text="Django session key for grouping related actions"
    )
    
    # Additional data (flexible JSON field for custom data)
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context-specific data (e.g., {'payment_gateway': 'razorpay', 'transaction_id': 'pay_123'})"
    )
    
    # Timestamp
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the action occurred"
    )
    
    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['action_type', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.user_email} - {self.action_type} - {self.model_name}"
    
    @classmethod
    def log_action(cls, user, action_type, model_instance, field_name=None, old_value=None, new_value=None, description=None, request=None):
        """
        Convenience method to create audit log entries.
        
        Usage:
            AuditLog.log_action(
                user=request.user,
                action_type='state_change',
                model_instance=rental_order,
                field_name='status',
                old_value='draft',
                new_value='confirmed',
                description='Order confirmed by customer',
                request=request
            )
        """
        
        # Extract request metadata
        ip_address = None
        user_agent = None
        session_key = None
        
        if request:
            # Get client IP (considering proxies)
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            session_key = request.session.session_key
        
        # Create audit log
        return cls.objects.create(
            user=user,
            user_email=user.email if user else 'system@automated',
            user_role=user.role if user and hasattr(user, 'role') else 'system',
            action_type=action_type,
            model_name=model_instance.__class__.__name__,
            object_id=str(model_instance.pk),
            object_repr=str(model_instance),
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            description=description or f"{action_type.title()} {model_instance.__class__.__name__}",
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=session_key,
        )
    
    @classmethod
    def get_object_history(cls, model_instance):
        """Get complete change history for a specific object"""
        return cls.objects.filter(
            model_name=model_instance.__class__.__name__,
            object_id=str(model_instance.pk)
        ).order_by('-timestamp')
    
    @classmethod
    def get_user_activity(cls, user, days=30):
        """Get user's activity for the last N days"""
        from django.utils import timezone
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        return cls.objects.filter(
            user=user,
            timestamp__gte=since
        ).order_by('-timestamp')
