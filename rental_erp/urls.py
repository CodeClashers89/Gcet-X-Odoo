"""
URL configuration for rental_erp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from accounts.views import login_view

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),
    
    # Authentication (accounts app)
    path('accounts/', include('accounts.urls')),
    
    # Dashboard (dashboards app)
    path('dashboard/', include('dashboards.urls')),
    
    # Product catalog (browsing, availability)
    path('catalog/', include('catalog.urls')),
    
    # Rentals (quotations, orders, pickup, return)
    path('rentals/', include('rentals.urls')),
    
    # Billing (invoicing, payments)
    path('billing/', include('billing.urls')),
    
    # Custom Admin components
    path('config/', include('system_settings.urls')),
    path('audit/', include('audit.urls')),
    
    # Public landing page (redirect to login by default)
    path('', login_view, name='home'),
]

# Serve static files in development
urlpatterns += staticfiles_urlpatterns()
