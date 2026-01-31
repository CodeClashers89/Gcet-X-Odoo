from django.core.management.base import BaseCommand
from catalog.models import Product, RentalPricing


class Command(BaseCommand):
    help = 'Add default pricing to products without any rental pricing'

    def handle(self, *args, **options):
        # Find products without pricing
        products_without_pricing = Product.objects.filter(
            is_published=True,
            is_rentable=True,
            rental_prices__isnull=True
        ).distinct()

        count = products_without_pricing.count()
        self.stdout.write(f'Found {count} products without pricing:')
        
        for p in products_without_pricing:
            self.stdout.write(f'  - {p.id}: {p.name}')

        if products_without_pricing.exists():
            self.stdout.write('\nAdding default pricing (₹100/day)...')
            for product in products_without_pricing:
                RentalPricing.objects.create(
                    product=product,
                    duration_type='daily',
                    duration_value=1,
                    price=100.00,
                    is_active=True
                )
                self.stdout.write(self.style.SUCCESS(f'  ✓ Added pricing for: {product.name}'))
            
            self.stdout.write(self.style.SUCCESS(f'\nDone! Added pricing for {count} products'))
        else:
            self.stdout.write(self.style.SUCCESS('\nAll products already have pricing!'))

        # Verify
        all_published = Product.objects.filter(is_published=True, is_rentable=True)
        self.stdout.write(f'\nTotal published products: {all_published.count()}')
        for p in all_published:
            pricing_count = p.rental_prices.count()
            self.stdout.write(f'  - {p.name}: {pricing_count} pricing tier(s)')
