from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ProductCategory, ProductAttribute, AttributeValue,
    Product, ProductVariant, RentalPricing
)


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    """
    Admin for product categories with hierarchical display.
    Business Use: Organize products into browsable categories for customer filtering.
    """
    
    list_display = ('name', 'parent', 'is_active', 'get_product_count', 'created_at')
    list_filter = ('is_active', 'parent', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'slug', 'parent', 'description')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
    )
    
    def get_product_count(self, obj):
        """Show number of products in this category"""
        return obj.products.count()
    get_product_count.short_description = 'Products'


class AttributeValueInline(admin.TabularInline):
    """
    Inline admin for attribute values.
    Allows managing dropdown values directly within attribute admin.
    """
    model = AttributeValue
    extra = 1
    fields = ('value', 'display_order', 'is_active')


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    """
    Admin for configurable product attributes.
    Business Use: Define what specifications apply to products (Brand, Color, Size, etc.)
    """
    
    list_display = (
        'display_name', 'name', 'input_type', 'is_required',
        'is_variant_attribute', 'get_value_count'
    )
    list_filter = ('input_type', 'is_required', 'is_variant_attribute')
    search_fields = ('name', 'display_name')
    inlines = [AttributeValueInline]
    
    fieldsets = (
        ('Attribute Definition', {
            'fields': ('name', 'display_name', 'input_type')
        }),
        ('Configuration', {
            'fields': ('is_required', 'is_variant_attribute')
        }),
    )
    
    def get_value_count(self, obj):
        """Show number of predefined values for this attribute"""
        return obj.values.count()
    get_value_count.short_description = 'Values'


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    """
    Standalone admin for attribute values.
    Business Use: Manage predefined values for dropdown attributes.
    """
    
    list_display = ('value', 'attribute', 'display_order', 'is_active', 'created_at')
    list_filter = ('attribute', 'is_active')
    search_fields = ('value', 'attribute__name')
    ordering = ('attribute', 'display_order', 'value')


class ProductVariantInline(admin.TabularInline):
    """
    Inline admin for product variants.
    Allows managing variants directly within product admin.
    """
    model = ProductVariant
    extra = 0
    fields = ('variant_name', 'sku', 'quantity_on_hand', 'cost_price', 'is_active')
    readonly_fields = ('sku',)


class RentalPricingInline(admin.TabularInline):
    """
    Inline admin for rental pricing.
    Allows configuring time-based pricing directly within product admin.
    """
    model = RentalPricing
    extra = 1
    fields = (
        'duration_type', 'duration_value', 'price',
        'is_discounted', 'discount_percentage', 'is_active'
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Main product admin with comprehensive management features.
    Business Use: Vendors manage their rental inventory here.
    """
    
    list_display = (
        'name', 'vendor', 'category', 'is_rentable', 'is_published',
        'quantity_on_hand', 'get_available_qty', 'cost_price', 'created_at'
    )
    
    list_filter = (
        'is_rentable', 'is_published', 'category',
        'vendor', 'created_at'
    )
    
    search_fields = ('name', 'slug', 'description', 'vendor__email')
    
    prepopulated_fields = {'slug': ('name',)}
    
    readonly_fields = ('get_available_qty', 'created_at', 'updated_at')
    
    inlines = [ProductVariantInline, RentalPricingInline]
    
    fieldsets = (
        ('Product Information', {
            'fields': ('vendor', 'category', 'name', 'slug')
        }),
        ('Description', {
            'fields': ('short_description', 'description')
        }),
        ('Images', {
            'fields': ('image_main',)
        }),
        ('Inventory & Pricing', {
            'fields': ('quantity_on_hand', 'get_available_qty', 'cost_price')
        }),
        ('Rental Settings', {
            'fields': ('is_rentable', 'is_published')
        }),
        ('Attributes (JSON)', {
            'fields': ('attributes',),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['publish_products', 'unpublish_products', 'mark_as_rentable']
    
    def get_available_qty(self, obj):
        """Show real-time available quantity"""
        available = obj.get_available_quantity()
        if available == 0:
            return format_html('<span style="color: red;">0</span>')
        elif available <= 2:
            return format_html('<span style="color: orange;">{}</span>', available)
        else:
            return format_html('<span style="color: green;">{}</span>', available)
    get_available_qty.short_description = 'Available'
    
    def publish_products(self, request, queryset):
        """Bulk publish products"""
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} product(s) published successfully.')
    publish_products.short_description = 'Publish selected products'
    
    def unpublish_products(self, request, queryset):
        """Bulk unpublish products"""
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} product(s) unpublished.')
    unpublish_products.short_description = 'Unpublish selected products'
    
    def mark_as_rentable(self, request, queryset):
        """Mark products as rentable"""
        updated = queryset.update(is_rentable=True)
        self.message_user(request, f'{updated} product(s) marked as rentable.')
    mark_as_rentable.short_description = 'Mark as rentable'
    
    def get_queryset(self, request):
        """
        Filter products based on user role.
        Business Logic: Vendors only see their own products.
        """
        qs = super().get_queryset(request)
        
        if request.user.is_superuser or request.user.is_admin_role():
            return qs
        
        if request.user.is_vendor():
            return qs.filter(vendor=request.user)
        
        return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Auto-set vendor to current user for vendor role.
        Business Logic: Vendors can only create products for themselves.
        """
        if db_field.name == 'vendor' and request.user.is_vendor():
            kwargs['queryset'] = db_field.related_model.objects.filter(pk=request.user.pk)
            kwargs['initial'] = request.user
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    Standalone admin for product variants.
    Business Use: Manage product variations with different specifications.
    """
    
    list_display = (
        'product', 'variant_name', 'sku', 'quantity_on_hand',
        'get_available_qty', 'cost_price', 'is_active'
    )
    
    list_filter = ('is_active', 'product__category', 'created_at')
    
    search_fields = ('variant_name', 'sku', 'product__name')
    
    readonly_fields = ('get_available_qty', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Variant Information', {
            'fields': ('product', 'variant_name', 'sku')
        }),
        ('Inventory & Pricing', {
            'fields': ('quantity_on_hand', 'get_available_qty', 'cost_price')
        }),
        ('Variant Details', {
            'fields': ('variant_attributes', 'image')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_available_qty(self, obj):
        """Show real-time available quantity for variant"""
        available = obj.get_available_quantity()
        if available == 0:
            return format_html('<span style="color: red;">0</span>')
        elif available <= 2:
            return format_html('<span style="color: orange;">{}</span>', available)
        else:
            return format_html('<span style="color: green;">{}</span>', available)
    get_available_qty.short_description = 'Available'


@admin.register(RentalPricing)
class RentalPricingAdmin(admin.ModelAdmin):
    """
    Standalone admin for rental pricing.
    Business Use: Configure time-based rental rates.
    """
    
    list_display = (
        'get_product_name', 'duration_type', 'duration_value',
        'price', 'get_effective_price', 'is_discounted', 'created_at'
    )
    
    list_filter = ('duration_type', 'is_discounted', 'created_at')
    
    search_fields = ('product__name', 'product_variant__variant_name')
    
    fieldsets = (
        ('Product Link', {
            'fields': ('product', 'product_variant')
        }),
        ('Pricing Configuration', {
            'fields': ('duration_type', 'duration_value', 'price')
        }),
        ('Discount Settings', {
            'fields': ('is_discounted', 'discount_percentage')
        }),
    )
    
    def get_product_name(self, obj):
        """Display product or variant name"""
        if obj.product_variant:
            return f"{obj.product_variant.product.name} - {obj.product_variant.variant_name}"
        return obj.product.name
    get_product_name.short_description = 'Product'
