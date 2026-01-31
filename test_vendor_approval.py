"""
Test script to verify vendor approval status is accessible and properly displayed
"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_erp.settings')
django.setup()

from accounts.models import User, VendorProfile
from django.utils import timezone

print("=" * 70)
print("VENDOR APPROVAL STATUS FIX VERIFICATION")
print("=" * 70)

# Get all vendor users
vendors = User.objects.filter(role='vendor')
print(f"\nTotal Vendors in System: {vendors.count()}\n")

if vendors.exists():
    print("Vendor Status Report:")
    print("-" * 70)
    print(f"{'Email':<35} {'Status':<15} {'Approved At':<20}")
    print("-" * 70)
    
    for vendor in vendors:
        try:
            # Test the related_name 'vendorprofile'
            vendor_profile = vendor.vendorprofile
            status = "✓ APPROVED" if vendor_profile.is_approved else "⏳ PENDING"
            approved_at = vendor_profile.approved_at.strftime("%Y-%m-%d %H:%M") if vendor_profile.approved_at else "N/A"
            print(f"{vendor.email:<35} {status:<15} {approved_at:<20}")
        except Exception as e:
            print(f"{vendor.email:<35} ✗ ERROR: {str(e)}")

    print("-" * 70)
    
    # Test admin approval action
    pending_vendors = vendors.filter(vendorprofile__is_approved=False)
    if pending_vendors.exists():
        print(f"\nPending Vendors: {pending_vendors.count()}")
        first_pending = pending_vendors.first()
        print(f"\nTest: Approving vendor '{first_pending.email}'...")
        
        try:
            vendor_profile = first_pending.vendorprofile
            vendor_profile.is_approved = True
            vendor_profile.approved_at = timezone.now()
            vendor_profile.save()
            
            # Verify the change
            refreshed = User.objects.get(id=first_pending.id).vendorprofile
            if refreshed.is_approved:
                print(f"✓ SUCCESS: Vendor '{first_pending.email}' is now APPROVED")
                print(f"  - is_approved: {refreshed.is_approved}")
                print(f"  - approved_at: {refreshed.approved_at}")
            else:
                print(f"✗ FAILED: Vendor not approved after save")
        except Exception as e:
            print(f"✗ ERROR during approval: {str(e)}")
    else:
        print("\nNo pending vendors to test approval workflow")
        
else:
    print("⚠ No vendors found in system. Create a vendor first to test the fix.")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print("\nNOTE: The issue has been fixed by updating related_name from")
print("'vendor_profile' to 'vendorprofile' to match template usage.")
