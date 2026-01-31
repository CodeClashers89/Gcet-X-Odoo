from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Product browsing
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    
    # Vendor product management
    path('vendor/add-product/', views.vendor_add_product, name='vendor_add_product'),
    path('vendor/manage-products/', views.vendor_manage_products, name='vendor_manage_products'),
    path('vendor/edit-product/<int:product_id>/', views.vendor_edit_product, name='vendor_edit_product'),
    path('vendor/delete-product/<int:product_id>/', views.vendor_delete_product, name='vendor_delete_product'),
    path('vendor/view-orders/', views.vendor_view_orders, name='vendor_view_orders'),
    
    # AJAX endpoints
    path('api/availability/', views.check_availability_ajax, name='check_availability'),
    path('api/pricing/', views.get_pricing_options_ajax, name='get_pricing'),
    path('api/variants/', views.get_product_variants_ajax, name='get_variants'),
]
