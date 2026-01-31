from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import role_required
from .models import SystemConfiguration, EmailTemplate, GSTConfiguration
from .forms import SystemConfigurationForm, EmailTemplateForm, GSTConfigurationForm
from audit.models import AuditLog

@login_required
@role_required(['admin'])
def admin_system_config(request):
    """View to manage global system settings."""
    config = SystemConfiguration.get_config()
    if request.method == 'POST':
        form = SystemConfigurationForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            
            # Log the change
            AuditLog.log_action(
                user=request.user,
                action_type='update',
                model_instance=config,
                description='Updated global system configuration',
                request=request
            )
            
            messages.success(request, 'System configuration updated successfully.')
            return redirect('system_settings:admin_system_config')
    else:
        form = SystemConfigurationForm(instance=config)
    
    return render(request, 'system_settings/admin_config.html', {'form': form, 'config': config})


@login_required
@role_required(['admin'])
def admin_email_template_list(request):
    """List all customizable email templates."""
    templates = EmailTemplate.objects.all()
    return render(request, 'system_settings/admin_email_template_list.html', {'templates': templates})


@login_required
@role_required(['admin'])
def admin_email_template_edit(request, pk):
    """Edit a specific email template."""
    template = get_object_or_404(EmailTemplate, pk=pk)
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            
            # Log the change
            AuditLog.log_action(
                user=request.user,
                action_type='update',
                model_instance=template,
                description=f'Updated email template: {template.get_template_type_display()}',
                request=request
            )
            
            messages.success(request, f'Email template "{template.get_template_type_display()}" updated.')
            return redirect('system_settings:admin_email_template_list')
    else:
        form = EmailTemplateForm(instance=template)
    
    return render(request, 'system_settings/admin_email_template_edit.html', {
        'form': form, 
        'template': template
    })


@login_required
@role_required(['admin'])
def admin_gst_list(request):
    """List all category-specific GST configurations."""
    gst_configs = GSTConfiguration.objects.select_related('category').all()
    return render(request, 'system_settings/admin_gst_list.html', {'gst_configs': gst_configs})


@login_required
@role_required(['admin'])
def admin_gst_add(request):
    """Add a new GST configuration."""
    if request.method == 'POST':
        form = GSTConfigurationForm(request.POST)
        if form.is_valid():
            gst_config = form.save()
            
            # Log the change
            AuditLog.log_action(
                user=request.user,
                action_type='create',
                model_instance=gst_config,
                description=f'Created GST configuration for category: {gst_config.category.name}',
                request=request
            )
            
            messages.success(request, 'GST configuration added successfully.')
            return redirect('system_settings:admin_gst_list')
    else:
        form = GSTConfigurationForm()
    
    return render(request, 'system_settings/admin_gst_form.html', {
        'form': form,
        'title': 'Add GST Configuration'
    })


@login_required
@role_required(['admin'])
def admin_gst_edit(request, pk):
    """Edit an existing GST configuration."""
    gst_config = get_object_or_404(GSTConfiguration, pk=pk)
    if request.method == 'POST':
        form = GSTConfigurationForm(request.POST, instance=gst_config)
        if form.is_valid():
            form.save()
            
            # Log the change
            AuditLog.log_action(
                user=request.user,
                action_type='update',
                model_instance=gst_config,
                description=f'Updated GST configuration for category: {gst_config.category.name}',
                request=request
            )
            
            messages.success(request, 'GST configuration updated successfully.')
            return redirect('system_settings:admin_gst_list')
    else:
        form = GSTConfigurationForm(instance=gst_config)
    
    return render(request, 'system_settings/admin_gst_form.html', {
        'form': form,
        'title': 'Edit GST Configuration',
        'gst_config': gst_config
    })
