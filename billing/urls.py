from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Invoice URLs
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/pdf/', views.download_invoice_pdf, name='download_pdf'),
    path('invoices/<int:pk>/sent/', views.mark_invoice_sent, name='mark_sent'),
    path('invoices/<int:pk>/payment/', views.record_payment, name='record_payment'),

    # Payment Gateway
    path('gateway/<int:order_id>/', views.payment_gateway, name='payment_gateway'),
    path('gateway/<int:order_id>/process/', views.process_payment, name='process_payment'),
    
    # AJAX endpoints
    path('api/generate/', views.generate_invoice, name='generate_invoice'),
]
