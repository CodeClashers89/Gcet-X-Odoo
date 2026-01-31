from django.urls import path
from . import views

app_name = 'dashboards'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Analytics routes (Phase 9)
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/quotations/', views.quotation_analytics, name='quotation_analytics'),
    path('analytics/orders/', views.order_analytics, name='order_analytics'),
    path('analytics/approvals/', views.approval_analytics, name='approval_analytics'),
    path('analytics/revenue/', views.revenue_analytics, name='revenue_analytics'),
    path('analytics/inventory/', views.inventory_analytics, name='inventory_analytics'),
    path('analytics/late-returns/', views.late_returns_analytics, name='late_returns_analytics'),
    
    # Vendor Financials
    path('vendor/financials/', views.vendor_financials, name='vendor_financials'),
]
