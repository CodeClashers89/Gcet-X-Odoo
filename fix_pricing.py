#!/usr/bin/env python
"""
Quick fix script to add default pricing to products without any rental pricing.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_erp.settings')
django.setup()

from catalog.models import Product, RentalPricing

# Find products without pricing
products_without_pricing = Product.objects.filter(
    is_published=True,
    is_rentable=True,
    rental_prices__isnull=True
).distinct()

print(f'Found {products_without_pricing.count()} products without pricing:')
for p in products_without_pricing:
    print(f'  - {p.id}: {p.name}')

if products_without_pricing.exists():
    print('\nAdding default pricing (₹100/day)...')
    for product in products_without_pricing:
        RentalPricing.objects.create(
            product=product,
            duration_type='daily',
            duration_value=1,
            price=100.00,
            is_active=True
        )
        print(f'  ✓ Added pricing for: {product.name}')
    
    print(f'\nDone! Added pricing for {products_without_pricing.count()} products')
else:
    print('\nAll products already have pricing!')

# Verify
all_published = Product.objects.filter(is_published=True, is_rentable=True)
print(f'\nTotal published products: {all_published.count()}')
for p in all_published:
    pricing_count = p.rental_prices.count()
    print(f'  - {p.name}: {pricing_count} pricing tier(s)')
