from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, Prefetch, Min, Max
from datetime import datetime, timedelta
from django.utils import timezone

from catalog.models import Product, ProductCategory, RentalPricing
from rentals.models import Reservation
from accounts.models import VendorProfile


@require_http_methods(["GET"])
def product_list(request):
    """
    Browse rentable products with filtering and availability checking.
    
    Business Use: 
    - Customers browse available rental items
    - Filter by category, price range, vendor
    - See availability for selected dates
    
    Query Parameters:
    - category: Filter by product category (slug)
    - vendor: Filter by vendor
    - search: Search by product name or description
    - min_price: Minimum rental daily price
    - max_price: Maximum rental daily price
    - sort: Sort by (name, price_low_high, price_high_low, newest)
    """
    
    # Base queryset: only published, rentable products
    products = Product.objects.filter(
        is_published=True,
        is_rentable=True
    ).prefetch_related('category', 'vendor', 'rental_prices')
    
    # Category filter
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    # Vendor filter
    vendor_id = request.GET.get('vendor')
    if vendor_id:
        products = products.filter(vendor_id=vendor_id)
    
    # Search filter
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Price filtering (based on daily rental price)
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    if min_price or max_price:
        # Filter products by rental pricing
        price_filter = RentalPricing.objects.filter(
            duration_type='daily',
            is_active=True
        )
        
        if min_price:
            try:
                min_price_val = float(min_price)
                price_filter = price_filter.filter(price__gte=min_price_val)
            except ValueError:
                pass
        
        if max_price:
            try:
                max_price_val = float(max_price)
                price_filter = price_filter.filter(price__lte=max_price_val)
            except ValueError:
                pass
        
        # Get product IDs with matching prices
        product_ids = price_filter.values_list('product_id', flat=True).distinct()
        products = products.filter(id__in=product_ids)
    
    # Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == 'price_low_high':
        # Sort by minimum rental price
        products = products.order_by('rental_prices__price')
    elif sort_by == 'price_high_low':
        products = products.order_by('-rental_prices__price')
    else:  # newest (default)
        products = products.order_by('-created_at')
    
    # Remove duplicates (in case of multiple prices)
    products = products.distinct()
    
    # Get available categories for filter
    categories = ProductCategory.objects.filter(is_active=True)
    
    # Get available vendors for filter
    vendors = VendorProfile.objects.filter(user__is_active=True)
    
    # Get price range for price filter slider
    min_rental_price = 0
    max_rental_price = 10000
    try:
        price_range = RentalPricing.objects.filter(
            duration_type='daily',
            is_active=True
        ).aggregate(
            min_price=Min('price'),
            max_price=Max('price')
        )
        if price_range['min_price']:
            min_rental_price = float(price_range['min_price'])
        if price_range['max_price']:
            max_rental_price = float(price_range['max_price'])
    except Exception:
        pass
    
    return render(request, 'catalog/product_list.html', {
        'products': products,
        'categories': categories,
        'vendors': vendors,
        'selected_category': category_slug,
        'selected_vendor': vendor_id,
        'search_query': search_query,
        'min_price': min_price,
        'max_price': max_price,
        'min_rental_price': min_rental_price,
        'max_rental_price': max_rental_price,
        'sort_by': sort_by,
    })


@require_http_methods(["GET"])
def product_detail(request, pk):
    """
    View detailed product information with pricing and variants.
    
    Business Use:
    - Show product details, images, descriptions
    - Display rental pricing options
    - Show variants and their details
    - Quick add to quotation form
    """
    
    product = get_object_or_404(
        Product.objects.filter(is_published=True, is_rentable=True).prefetch_related(
            'variants',
            'rental_prices',
            'category',
            'vendor'
        ),
        pk=pk
    )
    
    # Get rental prices grouped by duration
    daily_prices = product.rental_prices.filter(
        duration_type='daily',
        is_active=True
    ).order_by('duration_value')
    
    weekly_prices = product.rental_prices.filter(
        duration_type='weekly',
        is_active=True
    ).order_by('duration_value')
    
    monthly_prices = product.rental_prices.filter(
        duration_type='monthly',
        is_active=True
    ).order_by('duration_value')
    
    # Get product reviews/ratings (if any)
    # TODO: Implement reviews in future phase
    
    return render(request, 'catalog/product_detail.html', {
        'product': product,
        'daily_prices': daily_prices,
        'weekly_prices': weekly_prices,
        'monthly_prices': monthly_prices,
    })


@require_http_methods(["GET"])
def check_availability_ajax(request):
    """
    AJAX endpoint to check product availability for specific dates.
    
    Business Use: When customer selects rental dates, show if item is available
    
    Query Parameters:
    - product_id: Product to check (required)
    - start_date: Rental start date (ISO format, required)
    - end_date: Rental end date (ISO format, required)
    - quantity: Number of units needed (default 1)
    
    Response:
    {
        "available": true/false,
        "available_quantity": 5,
        "required_quantity": 1,
        "message": "Available" or reason not available,
        "pricing": {
            "daily_price": 100.00,
            "duration_days": 5,
            "total_price": 500.00
        }
    }
    """
    
    try:
        product_id = request.GET.get('product_id')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        quantity = int(request.GET.get('quantity', 1))
        
        if not all([product_id, start_date_str, end_date_str]):
            return JsonResponse({
                'error': 'Missing required parameters',
                'available': False
            }, status=400)
        
        # Parse dates
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)
        
        # Validate dates
        if end_date <= start_date:
            return JsonResponse({
                'available': False,
                'message': 'End date must be after start date'
            }, status=400)
        
        # Get product
        product = get_object_or_404(Product, id=product_id, is_rentable=True)
        
        # Check reservations
        # A product is unavailable if the number of reservations >= available quantity
        reservations = Reservation.objects.filter(
            product=product,
            rental_start_date__lt=end_date,
            rental_end_date__gt=start_date,
            status__in=['confirmed', 'active']
        ).count()
        
        available_quantity = product.quantity_on_hand - reservations
        is_available = available_quantity >= quantity
        
        # Get pricing
        pricing_info = {}
        try:
            duration_days = (end_date - start_date).days
            daily_price = RentalPricing.objects.filter(
                product=product,
                duration_type='daily',
                is_active=True
            ).first()
            
            if daily_price:
                unit_price = float(daily_price.price)
                total_price = unit_price * duration_days
                pricing_info = {
                    'daily_price': unit_price,
                    'duration_days': duration_days,
                    'total_price': total_price
                }
        except Exception:
            pass
        
        return JsonResponse({
            'available': is_available,
            'available_quantity': max(0, available_quantity),
            'required_quantity': quantity,
            'message': 'Available' if is_available else f'Only {max(0, available_quantity)} available',
            'pricing': pricing_info
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'available': False
        }, status=400)


@require_http_methods(["GET"])
def get_pricing_options_ajax(request):
    """
    AJAX endpoint to get all pricing options for a product.
    
    Used in product detail page to show pricing grid.
    
    Query Parameters:
    - product_id: Product ID (required)
    
    Response:
    {
        "daily": [{"duration": 1, "price": 100}],
        "weekly": [{"duration": 1, "price": 600}],
        "monthly": [{"duration": 1, "price": 2000}]
    }
    """
    
    try:
        product_id = request.GET.get('product_id')
        if not product_id:
            return JsonResponse({'error': 'Missing product_id'}, status=400)
        
        product = get_object_or_404(Product, id=product_id)
        
        # Get all pricing tiers
        daily = list(
            product.rental_prices.filter(
                duration_type='daily',
                is_active=True
            ).values('duration_value', 'price').order_by('duration_value')
        )
        
        weekly = list(
            product.rental_prices.filter(
                duration_type='weekly',
                is_active=True
            ).values('duration_value', 'price').order_by('duration_value')
        )
        
        monthly = list(
            product.rental_prices.filter(
                duration_type='monthly',
                is_active=True
            ).values('duration_value', 'price').order_by('duration_value')
        )
        
        # Convert Decimal to float for JSON serialization
        for item in daily + weekly + monthly:
            item['price'] = float(item['price'])
        
        return JsonResponse({
            'daily': daily,
            'weekly': weekly,
            'monthly': monthly
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_product_variants_ajax(request):
    """
    AJAX endpoint to get all variants of a product.
    
    Query Parameters:
    - product_id: Product ID (required)
    
    Response: Array of variants with details
    """
    
    try:
        product_id = request.GET.get('product_id')
        if not product_id:
            return JsonResponse({'error': 'Missing product_id'}, status=400)
        
        product = get_object_or_404(Product, id=product_id)
        
        variants = list(
            product.variants.filter(is_active=True).values(
                'id',
                'variant_name',
                'sku',
                'quantity_on_hand'
            )
        )
        
        return JsonResponse(variants, safe=False)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
