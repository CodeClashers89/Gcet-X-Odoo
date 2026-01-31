from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.decorators import role_required
from .models import AuditLog

@login_required
@role_required(['admin'])
def admin_audit_log_list(request):
    """
    Searchable and filterable audit log explorer for admins.
    Business Use: Investigation, compliance, and system transparency.
    """
    logs = AuditLog.objects.all().order_by('-timestamp')
    
    # Simple filtering
    user_query = request.GET.get('user')
    action_type = request.GET.get('action')
    model_name = request.GET.get('model')
    
    if user_query:
        logs = logs.filter(user_email__icontains=user_query)
    if action_type:
        logs = logs.filter(action_type=action_type)
    if model_name:
        logs = logs.filter(model_name=model_name)
        
    return render(request, 'audit/admin_audit_log_list.html', {
        'logs': logs[:500],  # Limit to 500 for performance
        'action_choices': AuditLog.ACTION_CHOICES,
        'current_filters': {
            'user': user_query,
            'action': action_type,
            'model': model_name
        }
    })
