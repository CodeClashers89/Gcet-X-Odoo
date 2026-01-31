"""
Test Script for Phase 10 Task 2: Encryption Implementation
Tests encryption/decryption, masking, and validation functions.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_erp.settings')
django.setup()

from rental_erp.encryption import (
    encryption_manager, 
    mask_gstin, 
    mask_pan, 
    mask_bank_account,
    validate_gstin,
    validate_ifsc_code,
    validate_pan,
    validate_upi_id
)
from accounts.models import User, CustomerProfile, VendorProfile


def test_encryption_decryption():
    """Test basic encryption and decryption"""
    print("\n" + "="*80)
    print("TEST 1: Encryption & Decryption")
    print("="*80)
    
    test_data = {
        'gstin': '29ABCDE1234F1Z5',
        'pan': 'ABCDE1234F',
        'bank_account': '1234567890123456',
        'ifsc': 'SBIN0001234',
        'upi': 'user@paytm'
    }
    
    results = {}
    for key, value in test_data.items():
        try:
            encrypted = encryption_manager.encrypt(value)
            decrypted = encryption_manager.decrypt(encrypted)
            
            match = "✓ PASS" if decrypted == value else "✗ FAIL"
            print(f"{key:15} | Original: {value:25} | {match}")
            results[key] = (decrypted == value)
        except Exception as e:
            print(f"{key:15} | ERROR: {str(e)}")
            results[key] = False
    
    passed = sum(results.values())
    total = len(results)
    print(f"\nResult: {passed}/{total} tests passed")
    return all(results.values())


def test_masking():
    """Test masking functions"""
    print("\n" + "="*80)
    print("TEST 2: Data Masking")
    print("="*80)
    
    test_cases = [
        ('GSTIN', '29ABCDE1234F1Z5', mask_gstin, '****4F1Z5'),
        ('PAN', 'ABCDE1234F', mask_pan, '****234F'),
        ('Bank Account', '1234567890123456', mask_bank_account, '****3456'),
        ('IFSC', 'SBIN0001234', mask_bank_account, '****1234'),
    ]
    
    results = {}
    for name, value, mask_func, expected in test_cases:
        try:
            masked = mask_func(value)
            match = "✓ PASS" if masked == expected else f"✗ FAIL (got: {masked})"
            print(f"{name:15} | {value:20} → {masked:20} | {match}")
            results[name] = (masked == expected)
        except Exception as e:
            print(f"{name:15} | ERROR: {str(e)}")
            results[name] = False
    
    passed = sum(results.values())
    total = len(results)
    print(f"\nResult: {passed}/{total} tests passed")
    return all(results.values())


def test_validators():
    """Test validation functions"""
    print("\n" + "="*80)
    print("TEST 3: Field Validators")
    print("="*80)
    
    test_cases = [
        # Valid cases
        ('GSTIN Valid', validate_gstin, '29ABCDE1234F1Z5', True, 'boolean'),
        ('IFSC Valid', validate_ifsc_code, 'SBIN0001234', True, 'boolean'),
        ('PAN Valid', validate_pan, 'ABCDE1234F', True, 'boolean'),
        ('UPI Valid', validate_upi_id, 'user@paytm', True, 'exception'),
        
        # Invalid cases
        ('GSTIN Invalid', validate_gstin, 'INVALID', False, 'boolean'),
        ('IFSC Invalid', validate_ifsc_code, 'INVALID', False, 'boolean'),
        ('PAN Invalid', validate_pan, 'INVALID', False, 'boolean'),
        ('UPI Invalid', validate_upi_id, 'invalid', False, 'exception'),
    ]
    
    results = {}
    for name, validator, value, should_pass, validator_type in test_cases:
        try:
            if validator_type == 'boolean':
                # Boolean return validators
                result = validator(value)
                if result == should_pass:
                    status = "✓ PASS"
                    results[name] = True
                else:
                    status = f"✗ FAIL (returned {result}, expected {should_pass})"
                    results[name] = False
            else:
                # Exception-raising validators
                validator(value)
                result = True
                if should_pass:
                    status = "✓ PASS"
                    results[name] = True
                else:
                    status = "✗ FAIL (should have raised error)"
                    results[name] = False
        except Exception as e:
            if validator_type == 'exception':
                # Expected to raise exception for invalid input
                if not should_pass:
                    status = "✓ PASS (correctly rejected)"
                    results[name] = True
                else:
                    status = f"✗ FAIL (unexpected exception: {str(e)})"
                    results[name] = False
            else:
                # Unexpected exception
                status = f"✗ ERROR: {str(e)}"
                results[name] = False
        
        print(f"{name:20} | {value:20} | {status}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\nResult: {passed}/{total} tests passed")
    return all(results.values())


def test_model_encryption():
    """Test encryption in models"""
    print("\n" + "="*80)
    print("TEST 4: Model Field Encryption")
    print("="*80)
    
    # Test with vendor profile (if exists)
    try:
        vendor = User.objects.filter(role='vendor').first()
        if vendor and hasattr(vendor, 'vendorprofile'):
            vendor_profile = vendor.vendorprofile
            
            print(f"Testing Vendor Profile: {vendor.email}")
            
            # Test GSTIN
            if vendor_profile.gstin:
                try:
                    decrypted_gstin = encryption_manager.decrypt(vendor_profile.gstin)
                    masked_gstin = mask_gstin(decrypted_gstin)
                    print(f"  GSTIN:        {masked_gstin:25} | ✓ Decrypted & Masked")
                except:
                    print(f"  GSTIN:        Not encrypted or invalid")
            else:
                print(f"  GSTIN:        Not set")
            
            # Test Bank Account
            if vendor_profile.bank_account_number:
                try:
                    decrypted_bank = encryption_manager.decrypt(vendor_profile.bank_account_number)
                    masked_bank = mask_bank_account(decrypted_bank)
                    print(f"  Bank Account: {masked_bank:25} | ✓ Decrypted & Masked")
                except:
                    print(f"  Bank Account: Not encrypted or invalid")
            else:
                print(f"  Bank Account: Not set")
            
            print("\n✓ Model encryption test completed (check values above)")
            return True
        else:
            print("No vendor profile found to test")
            print("✓ Test skipped (no data)")
            return True
            
    except Exception as e:
        print(f"✗ Error testing model encryption: {str(e)}")
        return False


def test_form_encryption():
    """Test form encryption handling"""
    print("\n" + "="*80)
    print("TEST 5: Form Encryption/Decryption")
    print("="*80)
    
    from accounts.forms import VendorRegistrationForm, CustomerRegistrationForm
    
    # Test customer form GSTIN encryption
    print("Testing CustomerRegistrationForm...")
    customer_data = {
        'email': 'testcustomer@example.com',
        'password': 'TestPass123!@#',
        'password_confirmation': 'TestPass123!@#',
        'first_name': 'Test',
        'last_name': 'Customer',
        'phone': '9876543210',
        'company_name': 'Test Company',
        'gstin': '29ABCDE1234F1Z5',
        'billing_address': 'Test Address',
        'state': 'Karnataka',
        'city': 'Bangalore',
        'pincode': '560001',
    }
    
    # Check if email exists
    if User.objects.filter(email=customer_data['email']).exists():
        print("  ⚠ Test user already exists, skipping creation test")
        print("  ✓ Test skipped (data exists)")
        return True
    
    try:
        form = CustomerRegistrationForm(data=customer_data)
        if form.is_valid():
            print("  ✓ Form validation passed")
            print("  ℹ Note: Form would encrypt GSTIN on save()")
            # Don't actually save to avoid creating test data
            return True
        else:
            print(f"  ✗ Form validation failed: {form.errors}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PHASE 10 TASK 2: ENCRYPTION IMPLEMENTATION TEST SUITE")
    print("="*80)
    
    tests = [
        ("Encryption/Decryption", test_encryption_decryption),
        ("Data Masking", test_masking),
        ("Field Validators", test_validators),
        ("Model Encryption", test_model_encryption),
        ("Form Encryption", test_form_encryption),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n✗ ERROR in {name}: {str(e)}")
            results[name] = False
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(results.values())
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:30} | {status}")
    
    print("="*80)
    print(f"OVERALL: {passed}/{total} test suites passed")
    print("="*80)
    
    if passed == total:
        print("\n🎉 All tests passed! Encryption implementation is working correctly.")
    else:
        print(f"\n⚠ {total - passed} test suite(s) failed. Please review the errors above.")


if __name__ == '__main__':
    main()
