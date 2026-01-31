from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Product browsing
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    
    # AJAX endpoints
    path('api/availability/', views.check_availability_ajax, name='check_availability'),
    path('api/pricing/', views.get_pricing_options_ajax, name='get_pricing'),
    path('api/variants/', views.get_product_variants_ajax, name='get_variants'),
]
