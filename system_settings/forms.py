from django import forms
from .models import SystemConfiguration, EmailTemplate, GSTConfiguration, LateFeePolicy

class SystemConfigurationForm(forms.ModelForm):
    """Form to manage global system configuration singleton."""
    class Meta:
        model = SystemConfiguration
        fields = '__all__'
        exclude = ('id',)
        widgets = {
            field.name: forms.TextInput(attrs={'class': 'form-control'}) 
            for field in SystemConfiguration._meta.fields 
            if isinstance(field, (forms.CharField, forms.CharField))
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply form-control class to all fields
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                existing_class = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f"{existing_class} form-control".strip()


class EmailTemplateForm(forms.ModelForm):
    """Form to customize automated email templates."""
    class Meta:
        model = EmailTemplate
        fields = ('subject', 'body_html', 'body_text', 'is_active')
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'body_html': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'style': 'font-family: monospace;'}),
            'body_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'style': 'font-family: monospace;'}),
        }


class GSTConfigurationForm(forms.ModelForm):
    """Form to manage category-specific GST rates and HSN codes."""
    class Meta:
        model = GSTConfiguration
        fields = ('category', 'hsn_code', 'cgst_rate', 'sgst_rate', 'igst_rate', 'effective_from', 'effective_until', 'is_active')
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'hsn_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 8471'}),
            'cgst_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sgst_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'igst_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'effective_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'effective_until': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
