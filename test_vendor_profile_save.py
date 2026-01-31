import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_erp.settings')
django.setup()

from accounts.models import VendorProfile, User
from accounts.forms import VendorProfileUpdateForm
import uuid

# Get a vendor user
vendors = User.objects.filter(role='vendor')
if vendors.exists():
    vendor = vendors.first()
    profile = vendor.vendorprofile
    
    print(f"Testing vendor: {vendor.email}")
    print(f"Current company_name: {profile.company_name}")
    print(f"Current city: {profile.city}")
    print(f"Current pincode: {profile.pincode}")
    print(f"Current bank_name: {profile.bank_name}")
    print("\nTesting form save...")
    
    # Test with form data
    test_company = 'TEST COMPANY ' + str(uuid.uuid4())[:8]
    data = {
        'company_name': test_company,
        'business_address': 'Test Address',
        'state': 'Karnataka',
        'city': 'TestCity',
        'pincode': '560001',
        'bank_name': 'Test Bank',
        'advance_payment_type': 'none',
        'advance_payment_percentage': '0.00'
    }
    
    form = VendorProfileUpdateForm(data=data, instance=profile)
    if form.is_valid():
        form.save()
        profile.refresh_from_db()
        print(f"\nAfter save:")
        print(f"company_name: {profile.company_name}")
        print(f"city: {profile.city}")
        print(f"pincode: {profile.pincode}")
        print(f"bank_name: {profile.bank_name}")
        
        if profile.company_name == test_company:
            print("\n✓ Form saved successfully! Changes are persisted!")
        else:
            print(f"\n✗ ERROR: company_name wasn't saved properly")
            print(f"  Expected: {test_company}")
            print(f"  Got: {profile.company_name}")
    else:
        print(f"Form errors: {form.errors}")
else:
    print("No vendors found")
