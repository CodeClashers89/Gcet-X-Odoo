from django.urls import path
from . import views
from . import gdpr_views
from . import mfa_views
from . import verify_2fa_view

app_name = 'accounts'

urlpatterns = [
    # Authentication Routes
    path('signup/customer/', views.signup_customer, name='signup_customer'),
    path('signup/vendor/', views.signup_vendor, name='signup_vendor'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Two-Factor Authentication
    path('2fa/setup/', mfa_views.setup_2fa, name='setup_2fa'),
    path('2fa/manage/', mfa_views.manage_2fa, name='manage_2fa'),
    path('2fa/verify/', verify_2fa_view.verify_2fa, name='verify_2fa'),
    path('api/2fa/verify/', mfa_views.verify_2fa_api, name='verify_2fa_api'),

    # Email & Password Management
    path('verify-email/<str:uidb64>/<str:token>/', views.verify_email, name='verify_email'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<str:uidb64>/<str:token>/', views.reset_password, name='reset_password'),
    
    # User Profile
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # GDPR Data Subject Rights
    path('my-data/', gdpr_views.my_data, name='my_data'),
    path('export-my-data/', gdpr_views.export_my_data, name='export_my_data'),
    path('request-data-deletion/', gdpr_views.request_data_deletion, name='request_data_deletion'),
    path('withdraw-consent/<int:consent_id>/', gdpr_views.withdraw_consent, name='withdraw_consent'),
    
    # AJAX endpoints
    path('api/verify-gstin/', views.verify_gstin_ajax, name='verify_gstin_ajax'),
]
