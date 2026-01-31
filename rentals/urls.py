from django.urls import path
from . import views

app_name = 'rentals'

urlpatterns = [
    # Quotation URLs
    path('quotation/create/', views.create_quotation, name='create_quotation'),
    path('quotation/list/', views.quotation_list, name='quotation_list'),
    path('quotation/<int:pk>/', views.quotation_detail, name='quotation_detail'),
    
    # Order URLs
    path('order/list/', views.order_list, name='order_list'),
    path('order/<int:pk>/', views.order_detail, name='order_detail'),
    
    # Pickup URLs
    path('order/<int:order_id>/pickup/schedule/', views.schedule_pickup, name='schedule_pickup'),
    path('order/<int:order_id>/pickup/complete/', views.complete_pickup, name='complete_pickup'),
    
    # Return URLs
    path('order/<int:order_id>/return/schedule/', views.schedule_return, name='schedule_return'),
    path('order/<int:order_id>/return/complete/', views.complete_return, name='complete_return'),
    
    # Approval URLs (Phase 8)
    path('approval/', views.approval_list, name='approval_list'),
    path('approval/<int:approval_id>/', views.approval_detail, name='approval_detail'),
    path('approval/<int:approval_id>/approve/', views.approve_request, name='approve_request'),
    path('approval/<int:approval_id>/reject/', views.reject_request, name='reject_request'),
    
    # AJAX endpoints
    path('api/variants/', views.get_variants_ajax, name='get_variants'),
    path('api/pricing/', views.get_pricing_ajax, name='get_pricing'),
]

