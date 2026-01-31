from django import forms
from django.forms import inlineformset_factory
from catalog.models import Product, ProductVariant, RentalPricing
from rentals.models import Quotation, QuotationLine, RentalOrder, RentalOrderLine, Pickup, Return


class QuotationLineForm(forms.ModelForm):
    """
    Form for individual quotation line items.
    Business Use: Add/edit products and rental dates in a quotation.
    
    Fields:
    - product: Product being rented
    - product_variant: Specific variant (optional)
    - rental_start_date: When rental begins
    - rental_end_date: When rental ends
    - quantity: Number of units
    """
    
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_rentable=True, is_published=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Product'
    )
    
    product_variant = forms.ModelChoiceField(
        queryset=ProductVariant.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Variant (Optional)'
    )
    
    rental_start_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label='Rental Start'
    )
    
    rental_end_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label='Rental End'
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '1'
        }),
        label='Quantity'
    )
    
    class Meta:
        model = QuotationLine
        fields = ('product', 'product_variant', 'rental_start_date', 'rental_end_date', 'quantity')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter variants based on selected product
        if self.instance.product_id:
            self.fields['product_variant'].queryset = ProductVariant.objects.filter(
                product_id=self.instance.product_id
            )
    
    def clean(self):
        """Validate rental dates"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('rental_start_date')
        end_date = cleaned_data.get('rental_end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError('Rental end date must be after start date.')
        
        return cleaned_data


# Create inline formset for quotation lines
QuotationLineFormSet = inlineformset_factory(
    Quotation,
    QuotationLine,
    form=QuotationLineForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class CreateQuotationForm(forms.ModelForm):
    """
    Form for creating a new quotation.
    Business Use: Customer initiates rental inquiry.
    
    Fields:
    - notes: Special requirements or notes
    - coupon_code: Optional promotional code (for future implementation)
    """
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Any special requirements or notes?'
        }),
        label='Special Requirements'
    )
    
    coupon_code = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Promo code (if applicable)'
        }),
        label='Coupon Code'
    )
    
    class Meta:
        model = Quotation
        fields = ('notes',)
    
    def save(self, commit=True):
        """Add timestamp when creating quotation"""
        quotation = super().save(commit=False)
        if commit:
            quotation.save()
        return quotation


class SendQuotationForm(forms.Form):
    """
    Form to send quotation to customer.
    Business Use: Vendor review before sending final quotation.
    """
    
    subject = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'value': 'Your Rental Quotation'
        }),
        label='Email Subject'
    )
    
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Optional message to include with quotation'
        }),
        label='Message'
    )


class ConfirmQuotationForm(forms.Form):
    """
    Form for customer to confirm/accept quotation.
    Business Use: Convert quotation to rental order.
    """
    
    deposit_amount = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        }),
        label='Deposit Amount (if applicable)'
    )
    
    delivery_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Where should items be delivered?'
        }),
        label='Delivery Address'
    )
    
    billing_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Billing address (same as delivery if no difference)'
        }),
        label='Billing Address'
    )
    
    agree_terms = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='I agree to the rental terms and conditions'
    )


class RentalOrderStatusForm(forms.ModelForm):
    """
    Form to update rental order status.
    Business Use: Vendor tracks order through fulfillment.
    
    Status progression:
    - draft → confirmed → in_progress → completed
    """
    
    status = forms.ChoiceField(
        choices=RentalOrder.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Order Status'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Status update notes'
        }),
        label='Notes'
    )
    
    class Meta:
        model = RentalOrder
        fields = ('status',)


class PickupScheduleForm(forms.ModelForm):
    """
    Form to schedule pickup of rental items.
    Business Use: Coordinate delivery logistics.
    """
    
    scheduled_pickup_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label='Scheduled Pickup Date/Time'
    )
    
    pickup_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Special pickup instructions'
        }),
        label='Pickup Notes'
    )
    
    class Meta:
        model = Pickup
        fields = ('scheduled_pickup_date', 'pickup_notes')


class PickupCompletionForm(forms.ModelForm):
    """
    Form to record pickup completion.
    Business Use: Confirm items handed over to customer.
    """
    
    actual_pickup_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label='Actual Pickup Date/Time'
    )
    
    items_checked = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='All items physically checked'
    )
    
    customer_id_verified = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Customer ID verified'
    )
    
    pickup_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Condition of items, customer notes, etc.'
        }),
        label='Pickup Notes'
    )
    
    class Meta:
        model = Pickup
        fields = ('actual_pickup_date', 'items_checked', 'customer_id_verified', 'pickup_notes')


class ReturnScheduleForm(forms.ModelForm):
    """
    Form to schedule return of rental items.
    Business Use: Plan item collection after rental period.
    """
    
    scheduled_return_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label='Scheduled Return Date/Time'
    )
    
    class Meta:
        model = Return
        fields = ('scheduled_return_date',)


class ReturnCompletionForm(forms.ModelForm):
    """
    Form to record return completion and damage assessment.
    Business Use: Process items coming back, assess late fees and damage.
    """
    
    actual_return_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label='Actual Return Date/Time'
    )
    
    all_items_returned = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='All items returned'
    )
    
    items_damaged = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Items damaged/missing'
    )
    
    damage_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Description of damage or missing items'
        }),
        label='Damage Description'
    )
    
    damage_cost = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        }),
        label='Estimated Damage Cost'
    )
    
    class Meta:
        model = Return
        fields = ('actual_return_date', 'all_items_returned', 'items_damaged', 
                 'damage_description', 'damage_cost')
    
    def clean(self):
        """Validate damage info if items damaged"""
        cleaned_data = super().clean()
        items_damaged = cleaned_data.get('items_damaged')
        damage_description = cleaned_data.get('damage_description')
        
        if items_damaged and not damage_description:
            raise forms.ValidationError('Please describe the damage if items are damaged.')
        
        return cleaned_data
