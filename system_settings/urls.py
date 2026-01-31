from django.urls import path
from . import views

app_name = 'system_settings'

urlpatterns = [
    path('admin/config/', views.admin_system_config, name='admin_system_config'),
    path('admin/email-templates/', views.admin_email_template_list, name='admin_email_template_list'),
    path('admin/email-templates/<int:pk>/edit/', views.admin_email_template_edit, name='admin_email_template_edit'),
    path('admin/gst/', views.admin_gst_list, name='admin_gst_list'),
    path('admin/gst/add/', views.admin_gst_add, name='admin_gst_add'),
    path('admin/gst/<int:pk>/edit/', views.admin_gst_edit, name='admin_gst_edit'),
]
