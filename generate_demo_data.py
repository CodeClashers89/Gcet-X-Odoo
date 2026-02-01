import os
import shutil
import random
from datetime import datetime, timedelta
from decimal import Decimal
import django
from django.utils import timezone
from django.utils.text import slugify

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_erp.settings')
django.setup()

from accounts.models import User, CustomerProfile, VendorProfile
from catalog.models import ProductCategory, Product, ProductVariant, RentalPricing
from rentals.models import Quotation, QuotationLine, RentalOrder, RentalOrderLine, Reservation
from billing.models import Invoice, Payment

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_DIR = r'C:/Users/dell/.gemini/antigravity/brain/288e9a4b-9306-4921-a007-7606166dc13d'
MEDIA_DIR = os.path.join(BASE_DIR, 'media')

def clear_data():
    print("Clearing existing demo data...")
    Payment.objects.all().delete()
    Invoice.objects.all().delete()
    Reservation.objects.all().delete()
    RentalOrderLine.objects.all().delete()
    RentalOrder.objects.all().delete()
    QuotationLine.objects.all().delete()
    Quotation.objects.all().delete()
    RentalPricing.objects.all().delete()
    ProductVariant.objects.all().delete()
    Product.objects.all().delete()
    ProductCategory.objects.all().delete()
    # Don't delete all users, just demo ones
    User.objects.filter(email__contains='demo').delete()

def move_images():
    print("Moving images to media directory...")
    image_mappings = {
        'app_logo_1769919438602.png': 'logo.png',
        'vendor1_logo_1769919460714.png': 'vendors/logos/lenspro_logo.png',
        'vendor2_logo_1769919478663.png': 'vendors/logos/comfortrent_logo.png',
        'canon_eos_r5_1769919499982.png': 'products/images/canon_eos_r5.png',
        'luxury_sofa_1769919519437.png': 'products/images/luxury_sofa.png',
    }
    
    for src, dst in image_mappings.items():
        src_path = os.path.join(ARTIFACT_DIR, src)
        dst_path = os.path.join(MEDIA_DIR, dst)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        if os.path.exists(src_path):
            shutil.copy(src_path, dst_path)
            print(f"Copied {src} to {dst}")

def create_users():
    print("Creating demo users...")
    # Admin
    admin, created = User.objects.get_or_create(
        email='admin@demo.local',
        defaults={
            'username': 'admin_demo',
            'first_name': 'System',
            'last_name': 'Administrator',
            'role': 'admin',
            'is_staff': True,
            'is_superuser': True,
            'is_verified': True
        }
    )
    if created: admin.set_password('demo12345678')
    admin.is_verified = True # Ensure existing users are also verified
    admin.save()

    # Vendor 1 - Camera
    v1, created = User.objects.get_or_create(
        email='vendor1@demo.local',
        defaults={
            'username': 'lenspro_vendor',
            'first_name': 'John',
            'last_name': 'Lens',
            'role': 'vendor',
            'is_verified': True
        }
    )
    if created: v1.set_password('demo12345678')
    v1.is_verified = True
    v1.save()
    
    vp1, _ = VendorProfile.objects.get_or_create(
        user=v1,
        defaults={
            'company_name': 'LensPRO Camera Rentals',
            'gstin': '27AAAAA0000A1Z5',
            'business_address': '123 Photography Lane, Mumbai',
            'state': 'Maharashtra',
            'city': 'Mumbai',
            'pincode': '400001',
            'vendor_logo': 'vendors/logos/lenspro_logo.png',
            'is_approved': True
        }
    )

    # Vendor 2 - Furniture
    v2, created = User.objects.get_or_create(
        email='vendor2@demo.local',
        defaults={
            'username': 'comfort_vendor',
            'first_name': 'Sarah',
            'last_name': 'Comfort',
            'role': 'vendor',
            'is_verified': True
        }
    )
    if created: v2.set_password('demo12345678')
    v2.is_verified = True
    v2.save()
    
    vp2, _ = VendorProfile.objects.get_or_create(
        user=v2,
        defaults={
            'company_name': 'ComfortRent Furniture',
            'gstin': '27BBBBB1111B1Z5',
            'business_address': '456 Interior Road, Delhi',
            'state': 'Delhi',
            'city': 'New Delhi',
            'pincode': '110001',
            'vendor_logo': 'vendors/logos/comfortrent_logo.png',
            'is_approved': True
        }
    )

    # Customers
    customers = []
    for i in range(1, 6):
        c, created = User.objects.get_or_create(
            email=f'customer{i}@demo.local',
            defaults={
                'username': f'customer_demo_{i}',
                'first_name': f'Customer',
                'last_name': f'Number {i}',
                'role': 'customer',
                'is_verified': True
            }
        )
        if created: c.set_password('demo12345678')
        c.is_verified = True
        c.save()
        
        CustomerProfile.objects.get_or_create(
            user=c,
            defaults={
                'company_name': f'Demo Corp {i}',
                'gstin': f'27CCCCC{i}{i}{i}{i}C1Z5',
                'billing_address': f'Suite {i}, Business Towers, Pune',
                'state': 'Maharashtra',
                'city': 'Pune',
                'pincode': '411001'
            }
        )
        customers.append(c)
    
    return admin, v1, v2, customers

def create_catalog(v1, v2):
    print("Creating product catalog...")
    # Categories
    cat_camera = ProductCategory.objects.create(name='Camera Equipment', slug='camera-equipment')
    cat_furniture = ProductCategory.objects.create(name='Furniture', slug='furniture')
    cat_audio = ProductCategory.objects.create(name='Audio & Sound', slug='audio-sound')
    cat_tools = ProductCategory.objects.create(name='Power Tools', slug='power-tools')
    
    # Products Vendor 1
    p1 = Product.objects.create(
        vendor=v1, category=cat_camera,
        name='Canon EOS R5 Mirrorless Camera', slug='canon-eos-r5',
        description='Professional mirrorless camera with 45MP sensor.',
        short_description='45MP, 8K Camera',
        image_main='products/images/canon_eos_r5.png',
        quantity_on_hand=5, cost_price=Decimal('350000.00'), is_published=True
    )
    RentalPricing.objects.create(product=p1, duration_type='daily', duration_value=1, price=Decimal('2500.00'))

    p3 = Product.objects.create(
        vendor=v1, category=cat_audio,
        name='JBL PartyBox 310', slug='jbl-partybox',
        description='Powerful portable party speaker with lights and sound.',
        short_description='Portable Bluetooth Speaker',
        quantity_on_hand=8, cost_price=Decimal('40000.00'), is_published=True
    )
    RentalPricing.objects.create(product=p3, duration_type='daily', duration_value=1, price=Decimal('1500.00'))

    # Products Vendor 2
    p2 = Product.objects.create(
        vendor=v2, category=cat_furniture,
        name='Luxury Emerald Green Sofa', slug='luxury-emerald-sofa',
        description='Modern luxury 3-seater velvet sofa.',
        short_description='Luxury Velvet Sofa',
        image_main='products/images/luxury_sofa.png',
        quantity_on_hand=10, cost_price=Decimal('45000.00'), is_published=True
    )
    RentalPricing.objects.create(product=p2, duration_type='daily', duration_value=1, price=Decimal('1200.00'))

    p4 = Product.objects.create(
        vendor=v2, category=cat_tools,
        name='Bosch Professional Jackhammer', slug='bosch-jackhammer',
        description='Heavy-duty concrete demolition hammer.',
        short_description='Concrete Demolition Hammer',
        quantity_on_hand=4, cost_price=Decimal('65000.00'), is_published=True
    )
    RentalPricing.objects.create(product=p4, duration_type='daily', duration_value=1, price=Decimal('1800.00'))

    return [p1, p2, p3, p4]

def create_transactions(customers, products):
    print("Creating rental transactions...")
    
    statuses = ['confirmed', 'in_progress', 'completed', 'cancelled']
    
    for customer in customers:
        # Create 5-8 transactions per customer
        for _ in range(random.randint(5, 8)):
            day_offset = random.randint(0, 45)
            start_date = timezone.now() - timedelta(days=day_offset)
            end_date = start_date + timedelta(days=random.randint(2, 7))
            
            product = random.choice(products)
            
            # Create Quotation
            qt_num = f'QT-DEMO-{random.randint(10000, 99999)}'
            q = Quotation.objects.create(
                quotation_number=qt_num,
                customer=customer,
                status='confirmed',
                valid_until=timezone.now().date() + timedelta(days=14),
            )
            
            price_obj = product.rental_prices.filter(duration_type='daily').first()
            unit_price = price_obj.price if price_obj else Decimal('1000.00')
            
            line = QuotationLine.objects.create(
                quotation=q,
                product=product,
                rental_start_date=start_date,
                rental_end_date=end_date,
                quantity=random.randint(1, 2),
                unit_price=unit_price,
            )
            q.calculate_totals()
            
            # Convert to Order
            ro_num = f'RO-DEMO-{random.randint(10000, 99999)}'
            # Older orders are more likely to be completed
            if day_offset > 15:
                status = random.choice(['completed', 'completed', 'cancelled'])
            else:
                status = random.choice(['confirmed', 'in_progress', 'in_progress'])
                
            o = RentalOrder.objects.create(
                order_number=ro_num,
                quotation=q,
                customer=customer,
                vendor=product.vendor,
                status=status,
                delivery_address=customer.customer_profile.billing_address,
                billing_address=customer.customer_profile.billing_address,
                created_at=start_date
            )
            
            RentalOrderLine.objects.create(
                rental_order=o,
                product=product,
                rental_start_date=start_date,
                rental_end_date=end_date,
                quantity=line.quantity,
                unit_price=line.unit_price,
            )
            o.calculate_totals()
            
            # Create Invoice if not cancelled
            if status != 'cancelled':
                inv_num = f'INV-DEMO-{random.randint(1000, 9999)}'
                is_paid = (status == 'completed')
                inv = Invoice.objects.create(
                    invoice_number=inv_num,
                    rental_order=o,
                    customer=customer,
                    vendor=product.vendor,
                    status='paid' if is_paid else 'sent',
                    total=o.total,
                    paid_amount=o.total if is_paid else Decimal('0.00'),
                    balance_due=Decimal('0.00') if is_paid else o.total,
                    due_date=timezone.now().date(),
                    invoice_date=timezone.now().date(),
                    billing_name=customer.customer_profile.company_name,
                    billing_gstin=customer.customer_profile.gstin,
                    billing_address=customer.customer_profile.billing_address,
                    billing_state=customer.customer_profile.state,
                    vendor_name=product.vendor.vendorprofile.company_name,
                    vendor_gstin=product.vendor.vendorprofile.gstin,
                    vendor_address=product.vendor.vendorprofile.business_address,
                    vendor_state=product.vendor.vendorprofile.state,
                )
                
                if is_paid:
                    # Update RentalOrder paid_amount
                    o.paid_amount = o.total
                    o.save()
                    
                    pay = Payment.objects.create(
                        payment_number=f'PAY-DEMO-{random.randint(1000, 9999)}',
                        invoice=inv,
                        customer=customer,
                        amount=inv.total,
                        payment_method='online',
                        transaction_id=f'TXN-{random.randint(100000, 999999)}',
                        payment_status='success',
                        payment_date=timezone.now()
                    )
                    # Use a small delay or manual update to ensure processed_at is set
                    pay.processed_at = timezone.now()
                    pay.save()

if __name__ == "__main__":
    clear_data()
    move_images()
    admin, v1, v2, customers = create_users()
    products = create_catalog(v1, v2)
    create_transactions(customers, products)
    print("Demo data generation complete!")
