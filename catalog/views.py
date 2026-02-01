from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, Prefetch, Min, Max
from datetime import datetime, timedelta
from django.utils import timezone

from catalog.models import Product, ProductCategory, RentalPricing, ProductVariant
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
    
    # Check if user is the vendor owner (can view draft products)
    if request.user.is_authenticated and request.user.role == 'vendor':
        # Vendor can see their own products (including drafts)
        product = get_object_or_404(
            Product.objects.filter(
                Q(is_published=True) | Q(vendor=request.user)
            ).filter(is_rentable=True).prefetch_related(
                'variants__rental_prices',
                'rental_prices',
                'category',
                'vendor'
            ),
            pk=pk
        )
    else:
        # Public can only see published products
        product = get_object_or_404(
            Product.objects.filter(is_published=True, is_rentable=True).prefetch_related(
                'variants__rental_prices',
                'rental_prices',
                'category',
                'vendor'
            ),
            pk=pk
        )
    
    # Get rental prices grouped by duration
    daily_prices = product.rental_prices.filter(
        duration_type='daily'
    ).order_by('duration_value')
    
    weekly_prices = product.rental_prices.filter(
        duration_type='weekly'
    ).order_by('duration_value')
    
    monthly_prices = product.rental_prices.filter(
        duration_type='monthly'
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


# Vendor Product Management Views
@require_http_methods(["GET", "POST"])
def vendor_add_product(request):
    """
    Add new rental product by vendor.
    Only approved vendors can add products.
    """
    from django.contrib.auth.decorators import login_required
    from django.http import HttpResponseForbidden
    from django.contrib import messages
    from django.utils.text import slugify
    
    # Check if user is an approved vendor
    if request.user.role != 'vendor':
        return HttpResponseForbidden('Only vendors can add products.')
    
    if not hasattr(request.user, 'vendorprofile') or not request.user.vendorprofile.is_approved:
        return HttpResponseForbidden('Your vendor account must be approved before adding products.')
    
    # Get all active categories
    categories = ProductCategory.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.POST.get('name')
            category_id = request.POST.get('category')
            description = request.POST.get('description')
            daily_price = request.POST.get('daily_price')
            quantity = request.POST.get('quantity')
            
            # Get attributes data
            attr_names = request.POST.getlist('attr_name[]')
            attr_values = request.POST.getlist('attr_value[]')
            
            # Build attributes dictionary
            attributes = {}
            for i in range(len(attr_names)):
                if attr_names[i] and attr_values[i]:  # Only add non-empty attributes
                    attributes[attr_names[i].strip()] = attr_values[i].strip()
            
            # Get variants data
            variant_names = request.POST.getlist('variant_name[]')
            variant_quantities = request.POST.getlist('variant_quantity[]')
            variant_prices = request.POST.getlist('variant_price[]')
            
            # Calculate cost price (use 70% of daily rental price as default)
            daily_price_val = float(daily_price)
            cost_price = daily_price_val * 0.7
            
            # Generate unique slug
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            
            # Check if slug exists and make it unique
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Create the product
            product = Product.objects.create(
                vendor=request.user,
                name=name,
                slug=slug,
                category_id=category_id,
                description=description,
                short_description=description[:200] if len(description) > 200 else description,
                quantity_on_hand=int(quantity),
                cost_price=cost_price,
                is_rentable=True,
                is_published=False,  # Draft by default, admin can publish
                attributes=attributes  # Save attributes as JSON
            )
            
            # Create rental pricing
            RentalPricing.objects.create(
                product=product,
                duration_type='daily',
                duration_value=1,
                price=float(daily_price)
            )
            
            # Create product variants if provided
            if variant_names and len(variant_names) > 0:
                for i in range(len(variant_names)):
                    if variant_names[i] and variant_quantities[i] and variant_prices[i]:
                        # Generate unique SKU for variant
                        sku = f"{slug}-VAR-{i+1}"
                        sku_counter = 1
                        while ProductVariant.objects.filter(sku=sku).exists():
                            sku = f"{slug}-VAR-{i+1}-{sku_counter}"
                            sku_counter += 1
                        
                        # Calculate variant cost price
                        variant_price_val = float(variant_prices[i])
                        variant_cost = variant_price_val * 0.7
                        
                        # Create variant
                        variant = ProductVariant.objects.create(
                            product=product,
                            variant_name=variant_names[i].strip(),
                            sku=sku,
                            quantity_on_hand=int(variant_quantities[i]),
                            cost_price=variant_cost,
                            is_active=True
                        )
                        
                        # Create rental pricing for variant
                        RentalPricing.objects.create(
                            product_variant=variant,
                            duration_type='daily',
                            duration_value=1,
                            price=variant_price_val
                        )
            
            # Log creation
            from audit.models import AuditLog
            AuditLog.log_action(
                user=request.user,
                action_type='create',
                model_instance=product,
                description=f'Product created by vendor: {product.name}',
                request=request
            )
            
            return render(request, 'catalog/add_product.html', {
                'success': True,
                'product': product,
                'categories': categories,
                'vendor': request.user.vendorprofile
            })
            
        except Exception as e:
            return render(request, 'catalog/add_product.html', {
                'error': str(e),
                'categories': categories,
                'vendor': request.user.vendorprofile
            })
    
    return render(request, 'catalog/add_product.html', {
        'vendor': request.user.vendorprofile,
        'categories': categories
    })


@require_http_methods(["GET"])
def vendor_manage_products(request):
    """
    View and manage vendor's products.
    Only approved vendors can manage products.
    """
    from django.http import HttpResponseForbidden
    
    # Check if user is an approved vendor
    if request.user.role != 'vendor':
        return HttpResponseForbidden('Only vendors can manage products.')
    
    if not hasattr(request.user, 'vendorprofile') or not request.user.vendorprofile.is_approved:
        return HttpResponseForbidden('Your vendor account must be approved before managing products.')
    
    # Get vendor's products
    products = Product.objects.filter(vendor=request.user).order_by('-created_at')
    
    context = {
        'products': products,
        'vendor': request.user.vendorprofile
    }
    return render(request, 'catalog/manage_products.html', context)


@require_http_methods(["GET", "POST"])
def vendor_edit_product(request, product_id):
    """
    Edit vendor's product.
    Only the product owner can edit their products.
    """
    from django.http import HttpResponseForbidden
    from django.shortcuts import redirect
    from django.utils.text import slugify
    
    # Check if user is vendor
    if request.user.role != 'vendor':
        return HttpResponseForbidden('Only vendors can edit products.')
    
    # Get product and verify ownership
    product = get_object_or_404(Product, id=product_id, vendor=request.user)
    categories = ProductCategory.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        try:
            # Update product fields
            product.name = request.POST.get('name')
            product.description = request.POST.get('description')
            product.short_description = product.description[:200] if len(product.description) > 200 else product.description
            product.category_id = request.POST.get('category')
            product.quantity_on_hand = int(request.POST.get('quantity'))
            
            # Update slug if name changed
            new_slug = slugify(product.name)
            if new_slug != product.slug:
                slug = new_slug
                counter = 1
                while Product.objects.filter(slug=slug).exclude(id=product.id).exists():
                    slug = f"{new_slug}-{counter}"
                    counter += 1
                product.slug = slug
            
            product.save()
            
            # Update pricing
            daily_price = float(request.POST.get('daily_price'))
            pricing = product.rental_prices.filter(duration_type='daily').first()
            if pricing:
                pricing.price = daily_price
                pricing.save()
            
            # Log edit
            from audit.models import AuditLog
            AuditLog.log_action(
                user=request.user,
                action_type='update',
                model_instance=product,
                description=f'Product updated by vendor: {product.name}',
                request=request
            )
            
            return redirect('catalog:vendor_manage_products')
            
        except Exception as e:
            context = {
                'product': product,
                'categories': categories,
                'error': str(e)
            }
            return render(request, 'catalog/edit_product.html', context)
    
    context = {
        'product': product,
        'categories': categories,
        'vendor': request.user.vendorprofile
    }
    return render(request, 'catalog/edit_product.html', context)


@require_http_methods(["POST"])
def vendor_delete_product(request, product_id):
    """
    Delete vendor's product.
    Only the product owner can delete their products.
    """
    from django.http import HttpResponseForbidden
    from django.shortcuts import redirect
    
    # Check if user is vendor
    if request.user.role != 'vendor':
        return HttpResponseForbidden('Only vendors can delete products.')
    
    # Get product and verify ownership
    product = get_object_or_404(Product, id=product_id, vendor=request.user)
    
    # Soft delete: de-list and make un-rentable instead of hard delete
    product.is_published = False
    product.is_rentable = False
    product.save()
    
    # Log deletion
    from audit.models import AuditLog
    AuditLog.log_action(
        user=request.user,
        action_type='delete',
        model_instance=product,
        description=f'Product de-listed (soft deleted) by vendor: {product.name}',
        request=request
    )
    
    return redirect('catalog:vendor_manage_products')


@require_http_methods(["GET"])
def vendor_view_orders(request):
    """
    View orders for vendor's products.
    Shows rental orders that customers placed for this vendor's products.
    """
    from django.http import HttpResponseForbidden
    from rentals.models import RentalOrder
    
    # Check if user is an approved vendor
    if request.user.role != 'vendor':
        return HttpResponseForbidden('Only vendors can view orders.')
    
    if not hasattr(request.user, 'vendorprofile'):
        return HttpResponseForbidden('Only vendors can view orders.')
    
    # Get orders for vendor's products
    from django.db.models import Q
    vendor_products = Product.objects.filter(vendor=request.user).values_list('id', flat=True)
    
    orders = RentalOrder.objects.filter(
        order_lines__product_id__in=vendor_products
    ).distinct().order_by('-created_at')
    
    context = {
        'orders': orders,
        'vendor': request.user.vendorprofile,
        'total_orders': orders.count()
    }
    return render(request, 'catalog/vendor_orders.html', context)
