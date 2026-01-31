from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

from accounts.models import CustomerProfile, VendorProfile, APIKey
from rental_erp.api_security import APIKeyManager
from catalog.models import ProductCategory, Product


class Command(BaseCommand):
    help = "Seed demo data for hackathon presentation"

    def handle(self, *args, **options):
        User = get_user_model()

        with transaction.atomic():
            # Admin user
            admin_user, admin_created = self._get_or_create_user(
                User,
                email='admin@demo.local',
                username='admin',
                password='Admin@123',
                role='admin',
                is_staff=True,
                is_superuser=True,
                is_verified=True,
                first_name='Admin',
                last_name='User',
            )

            # Vendor user
            vendor_user, vendor_created = self._get_or_create_user(
                User,
                email='vendor@demo.local',
                username='vendor_demo',
                password='Vendor@123',
                role='vendor',
                is_verified=True,
                first_name='Vikram',
                last_name='Vendor',
            )

            VendorProfile.objects.get_or_create(
                user=vendor_user,
                defaults={
                    'company_name': 'Demo Rentals Pvt Ltd',
                    'gstin': '29ABCDE1234F1Z5',
                    'business_address': 'MG Road, Bengaluru',
                    'state': 'Karnataka',
                    'city': 'Bengaluru',
                    'pincode': '560001',
                    'is_approved': True,
                    'approved_at': timezone.now(),
                }
            )

            # Customer user
            customer_user, customer_created = self._get_or_create_user(
                User,
                email='customer@demo.local',
                username='customer_demo',
                password='Customer@123',
                role='customer',
                is_verified=True,
                first_name='Chetan',
                last_name='Customer',
            )

            CustomerProfile.objects.get_or_create(
                user=customer_user,
                defaults={
                    'company_name': 'Demo Corp',
                    'gstin': '27ABCDE1234F1Z6',
                    'billing_address': 'Connaught Place, New Delhi',
                    'shipping_address': 'Connaught Place, New Delhi',
                    'state': 'Delhi',
                    'city': 'New Delhi',
                    'pincode': '110001',
                }
            )

            # Categories
            camera_cat, _ = ProductCategory.objects.get_or_create(
                name='Camera Equipment',
                defaults={
                    'slug': 'camera-equipment',
                    'description': 'Cameras, lenses, and accessories'
                }
            )
            furniture_cat, _ = ProductCategory.objects.get_or_create(
                name='Office Furniture',
                defaults={
                    'slug': 'office-furniture',
                    'description': 'Chairs, desks, and office essentials'
                }
            )

            # Products
            self._create_product(
                vendor_user,
                camera_cat,
                name='Canon EOS R5 Mirrorless Camera',
                description='High-end mirrorless camera for professional shoots.',
                cost_price=250000.00,
                quantity=5,
                attributes={'brand': 'Canon', 'model': 'EOS R5'}
            )

            self._create_product(
                vendor_user,
                furniture_cat,
                name='Ergonomic Office Chair',
                description='Comfortable ergonomic chair for long working hours.',
                cost_price=12000.00,
                quantity=15,
                attributes={'brand': 'ErgoFit', 'color': 'Black'}
            )

            # Demo API key for vendor (created only if none exists)
            if not APIKey.objects.filter(user=vendor_user, name='Demo API Key').exists():
                raw_key = APIKeyManager.generate_api_key()
                APIKey.objects.create(
                    user=vendor_user,
                    name='Demo API Key',
                    key_hash=APIKeyManager.hash_api_key(raw_key),
                    prefix=raw_key[:3],
                    last_four=raw_key[-4:],
                )
                self.stdout.write(f"Demo API Key (vendor): {raw_key}")

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
        self.stdout.write('Demo credentials:')
        self.stdout.write('  Admin: admin@demo.local / Admin@123')
        self.stdout.write('  Vendor: vendor@demo.local / Vendor@123')
        self.stdout.write('  Customer: customer@demo.local / Customer@123')

    def _create_product(self, vendor, category, name, description, cost_price, quantity, attributes):
        slug = slugify(name)
        Product.objects.get_or_create(
            slug=slug,
            defaults={
                'vendor': vendor,
                'category': category,
                'name': name,
                'description': description,
                'short_description': description[:120],
                'is_rentable': True,
                'is_published': True,
                'quantity_on_hand': quantity,
                'cost_price': cost_price,
                'attributes': attributes,
            }
        )

    def _get_or_create_user(self, User, email, username, password, **defaults):
        existing = User.objects.filter(email=email).first()
        if existing:
            return existing, False

        base_username = username
        candidate = base_username
        counter = 1
        while User.objects.filter(username=candidate).exists():
            counter += 1
            candidate = f"{base_username}{counter}"

        user = User.objects.create_user(
            username=candidate,
            email=email,
            password=password,
            **defaults,
        )
        return user, True
