"""
Script to create product categories for the rental system
"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rental_erp.settings')
django.setup()

from catalog.models import ProductCategory
from django.utils.text import slugify

# Define categories
categories_data = [
    {
        'name': 'Equipment Rental',
        'description': 'Construction equipment, power tools, and industrial machinery for rent'
    },
    {
        'name': 'Camera & Event Equipment',
        'description': 'Professional audio/visual equipment, cameras, lighting, and sound systems'
    },
    {
        'name': 'Furniture & Machinery',
        'description': 'Office furniture, event furniture, and industrial machinery rental'
    }
]

print("=" * 70)
print("CREATING PRODUCT CATEGORIES")
print("=" * 70)

created_count = 0
for category_data in categories_data:
    try:
        # Check if category already exists
        existing = ProductCategory.objects.filter(name=category_data['name']).exists()
        
        if existing:
            print(f"\n⚠ Category '{category_data['name']}' already exists")
            continue
        
        # Create the category
        category = ProductCategory.objects.create(
            name=category_data['name'],
            slug=slugify(category_data['name']),
            description=category_data['description'],
            is_active=True
        )
        
        print(f"\n✓ Created Category: {category.name}")
        print(f"  - Slug: {category.slug}")
        print(f"  - Description: {category.description[:60]}...")
        created_count += 1
        
    except Exception as e:
        print(f"\n✗ Error creating '{category_data['name']}': {str(e)}")

print("\n" + "=" * 70)
print(f"SUMMARY: {created_count} category/categories created successfully!")
print("=" * 70)

# Display all categories
print("\nAll Product Categories:")
print("-" * 70)
all_categories = ProductCategory.objects.all()
for idx, cat in enumerate(all_categories, 1):
    status = "✓ Active" if cat.is_active else "✗ Inactive"
    print(f"{idx}. {cat.name:<40} [{status}]")

print("-" * 70)
print(f"Total Categories: {all_categories.count()}")
