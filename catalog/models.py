from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings


class ProductCategory(models.Model):
    """
    Hierarchical categorization for rental products.
    
    Business Use: Helps customers find products faster through filters.
    Examples: "Camera Equipment" → "DSLR Cameras", "Construction Equipment" → "Power Tools"
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name (e.g., 'Camera Equipment', 'Furniture')"
    )
    
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-friendly identifier"
    )
    
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='subcategories',
        help_text="Parent category for hierarchical structure"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Category description for SEO and customer guidance"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Show/hide category on website"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_categories'
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ProductAttribute(models.Model):
    """
    Configurable product attributes (e.g., Brand, Color, Size, Model).
    
    Business Use: Different rental products need different specifications.
    Admin can define what attributes apply to which product categories.
    Examples: 
    - Camera: Brand, Sensor Type, Megapixels
    - Furniture: Material, Color, Dimensions
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Attribute name (e.g., 'Brand', 'Color', 'Size')"
    )
    
    display_name = models.CharField(
        max_length=100,
        help_text="User-friendly display name"
    )
    
    input_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('select', 'Dropdown'),
            ('multiselect', 'Multiple Selection'),
            ('number', 'Number'),
        ],
        default='text',
        help_text="How this attribute is entered/selected"
    )
    
    is_required = models.BooleanField(
        default=False,
        help_text="Must be specified for product creation"
    )
    
    is_variant_attribute = models.BooleanField(
        default=False,
        help_text="If True, creates product variants (e.g., 'Canon EOS R5 Body' vs 'Canon EOS R5 Kit')"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_attributes'
        verbose_name = 'Product Attribute'
        verbose_name_plural = 'Product Attributes'
        ordering = ['name']
    
    def __str__(self):
        return self.display_name


class AttributeValue(models.Model):
    """
    Predefined values for dropdown-based attributes.
    
    Business Use: Ensures consistency in product data entry.
    Example: Brand attribute can have values: Canon, Nikon, Sony (not random text)
    """
    
    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name='values',
        help_text="Which attribute this value belongs to"
    )
    
    value = models.CharField(
        max_length=100,
        help_text="The actual value (e.g., 'Canon', 'Red', 'Large')"
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Sort order in dropdown lists"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Available for selection"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'attribute_values'
        verbose_name = 'Attribute Value'
        verbose_name_plural = 'Attribute Values'
        ordering = ['attribute', 'display_order', 'value']
        unique_together = ['attribute', 'value']
    
    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class Product(models.Model):
    """
    Master product definition for rentable items.
    
    Business Use: Core inventory entity. Tracks what can be rented, pricing, availability.
    Each product can have multiple variants (e.g., different lens kits for same camera body).
    """
    
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products',
        limit_choices_to={'role': 'vendor'},
        help_text="Vendor who owns this product"
    )
    
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='products',
        help_text="Product classification for filtering"
    )
    
    # Basic product information
    name = models.CharField(
        max_length=255,
        help_text="Product name (e.g., 'Canon EOS R5 Mirrorless Camera')"
    )
    
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="URL-friendly identifier"
    )
    
    description = models.TextField(
        help_text="Detailed product description for customer decision-making"
    )
    
    short_description = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Brief summary for product listings"
    )
    
    # Product images
    image_main = models.ImageField(
        upload_to='products/images/',
        blank=True,
        null=True,
        help_text="Primary product image"
    )
    
    # Rental-specific flags
    is_rentable = models.BooleanField(
        default=True,
        help_text="Can this product be rented? (vs purchase-only)"
    )
    
    is_published = models.BooleanField(
        default=False,
        help_text="Visible on website. Vendors can unpublish temporarily."
    )
    
    # Inventory tracking
    quantity_on_hand = models.PositiveIntegerField(
        default=0,
        help_text="Total physical inventory owned by vendor"
    )
    
    # Pricing
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Vendor's acquisition cost (for margin calculation)"
    )
    
    # Rental attributes (stored as JSON for flexibility)
    attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dynamic attributes like Brand, Model, Color (JSON: {'brand': 'Canon', 'model': 'EOS R5'})"
    )
    
    # SEO and metadata
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="SEO page title"
    )
    
    meta_description = models.TextField(
        blank=True,
        null=True,
        help_text="SEO meta description"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'is_published']),
            models.Index(fields=['category', 'is_published']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.vendor.company_name if hasattr(self.vendor, 'vendor_profile') else self.vendor.email})"
    
    def get_available_quantity(self):
        """
        Calculate real-time available quantity.
        Business Logic: Quantity on hand - Currently reserved quantity = Available for new rentals
        """
        from rentals.models import Reservation
        from django.utils import timezone
        
        # Sum of quantities reserved for active/future rentals
        reserved = Reservation.objects.filter(
            product=self,
            status__in=['confirmed', 'active'],
            rental_end_date__gte=timezone.now()
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        return max(0, self.quantity_on_hand - reserved)


class ProductVariant(models.Model):
    """
    Product variations with different pricing.
    
    Business Use: Same product with different configurations (e.g., camera body only vs kit with lenses).
    Each variant has unique SKU and pricing but shares the parent product's description.
    """
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        help_text="Parent product this variant belongs to"
    )
    
    variant_name = models.CharField(
        max_length=255,
        help_text="Variant identifier (e.g., 'Body Only', '24-70mm Kit', 'Pro Bundle')"
    )
    
    sku = models.CharField(
        max_length=100,
        unique=True,
        help_text="Stock Keeping Unit for inventory tracking"
    )
    
    # Variant-specific inventory
    quantity_on_hand = models.PositiveIntegerField(
        default=0,
        help_text="Inventory for this specific variant"
    )
    
    # Variant attributes (what makes it different from other variants)
    variant_attributes = models.JSONField(
        default=dict,
        help_text="Attributes that differentiate this variant (JSON: {'lens': '24-70mm', 'accessories': 'Battery Grip'})"
    )
    
    # Variant-specific pricing
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Cost price for this variant"
    )
    
    # Additional images specific to this variant
    image = models.ImageField(
        upload_to='products/variants/',
        blank=True,
        null=True,
        help_text="Variant-specific image"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Is this variant available for rental?"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_variants'
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'
        ordering = ['product', 'variant_name']
        unique_together = ['product', 'variant_name']
    
    def __str__(self):
        return f"{self.product.name} - {self.variant_name}"
    
    def get_available_quantity(self):
        """Calculate available quantity for this specific variant"""
        from rentals.models import Reservation
        from django.utils import timezone
        
        reserved = Reservation.objects.filter(
            product_variant=self,
            status__in=['confirmed', 'active'],
            rental_end_date__gte=timezone.now()
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        return max(0, self.quantity_on_hand - reserved)


class RentalPricing(models.Model):
    """
    Time-based rental pricing configuration.
    
    Business Use: Rental rates vary by duration (hourly, daily, weekly).
    Longer rentals get better per-day rates (business incentive).
    Example: $50/day, but $300/week (saves $50 vs 7 daily rentals).
    """
    
    DURATION_CHOICES = [
        ('hourly', 'Per Hour'),
        ('daily', 'Per Day'),
        ('weekly', 'Per Week'),
        ('monthly', 'Per Month'),
        ('custom', 'Custom Duration'),
    ]
    
    # Link to either Product or ProductVariant
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='rental_prices',
        help_text="Applies to all variants if set at product level"
    )
    
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='rental_prices',
        help_text="Variant-specific pricing overrides product pricing"
    )
    
    duration_type = models.CharField(
        max_length=20,
        choices=DURATION_CHOICES,
        help_text="Rental period unit"
    )
    
    duration_value = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of units (e.g., 2 for '2 days', 3 for '3 hours')"
    )
    
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Rental price for this duration"
    )
    
    # Discounting logic
    is_discounted = models.BooleanField(
        default=False,
        help_text="Promotional pricing active"
    )
    
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MinValueValidator(100)],
        help_text="Discount % if promotional pricing is active"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Enable/disable this pricing tier"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rental_pricing'
        verbose_name = 'Rental Pricing'
        verbose_name_plural = 'Rental Pricing'
        ordering = ['product', 'duration_type', 'duration_value']
    
    def __str__(self):
        item = self.product_variant if self.product_variant else self.product
        return f"{item} - {self.duration_value} {self.duration_type}: ₹{self.price}"
    
    def get_effective_price(self):
        """Calculate final price after discount"""
        if self.is_discounted and self.discount_percentage > 0:
            discount_amount = (self.price * self.discount_percentage) / 100
            return self.price - discount_amount
        return self.price
