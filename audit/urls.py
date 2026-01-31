from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('admin/logs/', views.admin_audit_log_list, name='admin_audit_log_list'),
]
