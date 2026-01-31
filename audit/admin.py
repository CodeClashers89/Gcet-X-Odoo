from django.contrib import admin
from django.utils.html import format_html
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Read-only admin for audit trail.
    Business Use: Track all critical system changes for compliance and debugging.
    """
    
    list_display = (
        'timestamp', 'user_email', 'user_role', 'get_action_badge',
        'model_name', 'object_repr', 'field_name', 'get_change_summary'
    )
    
    list_filter = (
        'action_type', 'user_role', 'model_name', 'timestamp'
    )
    
    search_fields = (
        'user_email', 'model_name', 'object_repr',
        'description', 'old_value', 'new_value'
    )
    
    readonly_fields = (
        'user', 'user_email', 'user_role', 'action_type',
        'model_name', 'object_id', 'object_repr',
        'field_name', 'old_value', 'new_value', 'description',
        'ip_address', 'user_agent', 'session_key',
        'extra_data', 'timestamp'
    )
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_email', 'user_role')
        }),
        ('Action Details', {
            'fields': (
                'action_type', 'model_name', 'object_id',
                'object_repr', 'description'
            )
        }),
        ('Change Information', {
            'fields': ('field_name', 'old_value', 'new_value')
        }),
        ('Request Metadata', {
            'fields': ('ip_address', 'user_agent', 'session_key'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation of audit logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of audit logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make audit logs read-only"""
        return False
    
    def get_action_badge(self, obj):
        """Display color-coded action type"""
        colors = {
            'create': 'green',
            'update': 'blue',
            'delete': 'red',
            'state_change': 'orange',
            'payment': 'purple',
            'login': 'gray',
            'logout': 'gray'
        }
        color = colors.get(obj.action_type, 'gray')
        return format_html(
            '<span style="padding: 3px 10px; background-color: {}; color: white; border-radius: 3px;">{}</span>',
            color, obj.get_action_type_display()
        )
    get_action_badge.short_description = 'Action'
    
    def get_change_summary(self, obj):
        """Show change summary"""
        if obj.field_name and obj.old_value and obj.new_value:
            return format_html(
                '<strong>{}</strong>: {} → {}',
                obj.field_name,
                obj.old_value[:30] + '...' if len(obj.old_value) > 30 else obj.old_value,
                obj.new_value[:30] + '...' if len(obj.new_value) > 30 else obj.new_value
            )
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    get_change_summary.short_description = 'Change Summary'
