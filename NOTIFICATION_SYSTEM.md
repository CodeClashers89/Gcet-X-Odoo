# Rental Workflow Notification System

## Overview

The notification system sends automated email notifications at each stage of the rental workflow to keep both customers and vendors informed about their rental transactions.

## Architecture

### Components

1. **NotificationService** (`rentals/notifications.py`)
   - Core service handling email delivery
   - Renders HTML email templates
   - Logs all notification attempts

2. **RentalWorkflowNotifications** (`rentals/notifications.py`)
   - Workflow-specific notification methods
   - One method per stage or action
   - Handles context preparation

3. **Email Templates** (`templates/rentals/emails/`)
   - HTML email templates for each notification type
   - Styled with inline CSS for compatibility
   - Dynamic content injection via Django templates

4. **Management Command** (`rentals/management/commands/send_rental_reminders.py`)
   - Scheduled task for sending reminders
   - Sends pickup and return reminders 24 hours before
   - Can be integrated with Celery for periodic execution

## Notification Stages

### Stage 1: Inquiry Submission
- **Customer Receives**: Inquiry confirmation with reference number
- **Vendor Receives**: New inquiry notification with details
- **Templates**:
  - `inquiry_submitted.html` - Confirms customer's inquiry submission
  - `vendor_inquiry_received.html` - Alerts vendor of new inquiry

**Code Example**:
```python
from rentals.notifications import RentalWorkflowNotifications

inquiry = RentalInquiry.objects.get(id=inquiry_id)
RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)
RentalWorkflowNotifications.notify_vendor_inquiry_received(inquiry)
```

### Stage 2: Inquiry Response
- **Vendor Accepts**: Customer notified inquiry is accepted and quotation coming
- **Vendor Rejects**: Customer notified with optional reason
- **Templates**:
  - `inquiry_accepted.html` - Vendor accepted, quotation coming soon
  - `inquiry_rejected.html` - Vendor rejected with optional reason

**Code Example**:
```python
inquiry.status = 'accepted'  # or 'rejected'
inquiry.save()

if inquiry.status == 'accepted':
    RentalWorkflowNotifications.notify_customer_inquiry_accepted(inquiry)
else:
    RentalWorkflowNotifications.notify_customer_inquiry_rejected(
        inquiry, 
        reason="Product not available for requested dates"
    )
```

### Stage 3: Quotation Sent
- **Customer Receives**: Quotation details with amount and validity period
- **Template**: `quotation_sent.html`

**Code Example**:
```python
from rentals.notifications import RentalWorkflowNotifications

quotation = Quotation.objects.get(id=quotation_id)
RentalWorkflowNotifications.notify_customer_quotation_sent(quotation)
```

### Stage 4: Quotation Acceptance
- **Vendor Receives**: Customer accepted quotation
- **Template**: `vendor_quotation_accepted.html`

**Code Example**:
```python
quotation.status = 'accepted'
quotation.save()

RentalWorkflowNotifications.notify_vendor_quotation_accepted(quotation)
```

### Stage 5: Order Confirmation
- **Customer Receives**: Rental order confirmation with full details
- **Vendor Receives**: (Optional) Order details if needed
- **Templates**:
  - `order_confirmed.html` - Order confirmed with rental period and location
  - `order_rejected.html` - Order could not be confirmed (if rejected)

**Code Example**:
```python
rental_order = RentalOrder.objects.get(id=order_id)
RentalWorkflowNotifications.notify_customer_order_confirmed(rental_order)
# OR if rejected:
RentalWorkflowNotifications.notify_customer_order_rejected(
    rental_order,
    reason="Payment failed"
)
```

### Stage 6: Payment Received
- **Customer Receives**: Payment confirmation with transaction details
- **Vendor Receives**: Payment received notification
- **Templates**:
  - `payment_received.html` - Customer payment confirmation
  - `vendor_payment_received.html` - Vendor payment notification

**Code Example**:
```python
payment = Payment.objects.get(id=payment_id)
payment.status = 'completed'
payment.save()

from rentals.notifications import notify_payment_stage
notify_payment_stage(payment)
```

### Stage 7: Invoice Generation
- **Customer Receives**: Invoice with billing details
- **Template**: `invoice_generated.html`

**Code Example**:
```python
from rentals.notifications import notify_invoice_stage

invoice = Invoice.objects.get(id=invoice_id)
notify_invoice_stage(invoice)
```

### Stage 8: Pickup Reminder
- **Customer Receives**: Reminder 24 hours before scheduled pickup
- **Template**: `pickup_reminder.html`

**Automatic Scheduling**:
```bash
# Run this command daily via cron or Celery Beat
python manage.py send_rental_reminders
```

**Manual Code**:
```python
RentalWorkflowNotifications.notify_customer_pickup_reminder(rental_order, days_until_pickup=1)
```

### Stage 9: Return Reminder
- **Customer Receives**: Reminder 24 hours before return date
- **Template**: `return_reminder.html`

**Automatic Scheduling**: Same as pickup reminders via management command

**Manual Code**:
```python
RentalWorkflowNotifications.notify_customer_return_reminder(rental_order, days_until_return=1)
```

### Stage 10: Return Initiated
- **Vendor Receives**: Notification that customer is returning the item
- **Template**: `vendor_return_initiated.html`

**Code Example**:
```python
rental_return = RentalReturn.objects.get(id=return_id)
RentalWorkflowNotifications.notify_vendor_return_initiated(rental_return)
```

### Stage 11: Rental Settlement
- **Customer Receives**: Refund processed with settlement details
- **Vendor Receives**: Settlement summary with damage charges
- **Templates**:
  - `rental_settled.html` - Customer refund notification
  - `vendor_rental_settled.html` - Vendor settlement notification

**Code Example**:
```python
from rentals.notifications import notify_return_stage

rental_return = RentalReturn.objects.get(id=return_id)
rental_return.status = 'settled'
rental_return.save()

notify_return_stage(rental_return, 'settled')
```

## Implementation Guide

### 1. Basic Usage in Views

```python
from django.shortcuts import render, redirect
from rentals.models import RentalInquiry
from rentals.notifications import notify_inquiry_stage

def customer_submit_inquiry(request):
    """Handle customer submitting an inquiry"""
    if request.method == 'POST':
        # Create inquiry from form data
        inquiry = RentalInquiry.objects.create(
            customer=request.user,
            product=product,
            vendor=selected_vendor,
            quantity=int(request.POST['quantity']),
            rental_start_date=start_date,
            rental_end_date=end_date,
            status='pending'
        )
        
        # Send notifications
        notify_inquiry_stage(inquiry, 'submitted')
        
        return redirect('rentals:inquiry_confirmation', inquiry_id=inquiry.id)
```

### 2. Integration with Payment Gateway

```python
def payment_success_callback(request):
    """Handle successful payment from payment gateway"""
    payment_id = request.POST['payment_id']
    payment = Payment.objects.get(id=payment_id)
    
    # Update payment status
    payment.status = 'completed'
    payment.transaction_id = request.POST['transaction_id']
    payment.save()
    
    # Send notifications
    from rentals.notifications import notify_payment_stage
    notify_payment_stage(payment)
    
    # Create invoice
    invoice = Invoice.objects.create(
        rental_order=payment.rental_order,
        invoice_number=f"INV-{payment.rental_order.order_number}",
        amount=payment.amount
    )
    
    # Send invoice notification
    from rentals.notifications import notify_invoice_stage
    notify_invoice_stage(invoice)
    
    return redirect('rentals:payment_success')
```

### 3. Scheduled Reminders via Celery

If you have Celery configured, add to `rentals/tasks.py`:

```python
from celery import shared_task
from rentals.notifications import RentalWorkflowNotifications
from django.utils import timezone
from datetime import timedelta
from rentals.models import RentalOrder

@shared_task
def send_rental_reminders():
    """Send pickup and return reminders"""
    now = timezone.now()
    tomorrow = now + timedelta(hours=24)
    tomorrow_end = now + timedelta(hours=25)
    
    # Pickup reminders
    orders = RentalOrder.objects.filter(
        pickup_date__gte=tomorrow,
        pickup_date__lte=tomorrow_end,
        status='confirmed'
    )
    for order in orders:
        RentalWorkflowNotifications.notify_customer_pickup_reminder(order)
    
    # Return reminders
    orders = RentalOrder.objects.filter(
        rental_end_date__gte=tomorrow,
        rental_end_date__lte=tomorrow_end,
        status='active'
    )
    for order in orders:
        RentalWorkflowNotifications.notify_customer_return_reminder(order)
```

Add to `rental_erp/celery.py`:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'send-rental-reminders': {
        'task': 'rentals.tasks.send_rental_reminders',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9 AM
    },
}
```

### 4. Running Manual Reminders

```bash
# Send all pending reminders
python manage.py send_rental_reminders
```

## Email Configuration

All emails are sent using Django's email backend configured in [rental_erp/settings.py](rental_erp/settings.py):

```python
# Email configuration (Brevo SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp-relay.brevo.com'
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'noreply@rentalerp.com'
```

**Required environment variables in `.env`**:
```
EMAIL_HOST_USER=your-brevo-email@example.com
EMAIL_HOST_PASSWORD=your-brevo-smtp-password
```

## Template Customization

Email templates are located in `templates/rentals/emails/`. Each template uses Django template syntax for dynamic content:

```html
<p>Hi {{ customer_name }},</p>
<p>Your order {{ order_number }} has been confirmed.</p>
```

**Common template variables:**
- `customer_name` - Full name of customer
- `vendor_name` - Full name of vendor
- `product_name` - Product name
- `amount` / `total_amount` - Financial amounts
- `order_number` / `invoice_number` / `quotation_number` - Reference numbers
- `rental_start` / `rental_end` - Dates
- `status` - Current status

## Troubleshooting

### Emails not sending
1. Check Brevo credentials in `.env`
2. Verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
3. Test with: `python test_django_email.py`
4. Check Django logs for SMTP errors

### Template not found
1. Ensure template path matches: `rentals/emails/template_name.html`
2. Check `TEMPLATES` in settings.py for correct `DIRS`
3. Run `python manage.py collectstatic` if in production

### Dynamic content missing
1. Verify context dictionary contains required variables
2. Check template variable names match context keys (case-sensitive)
3. Use Django template debugging: `{{ variable|default:"missing" }}`

## Future Enhancements

1. **SMS Integration**: Add SMS notifications via Twilio/AWS SNS
2. **In-App Notifications**: Push notifications to user dashboard
3. **Email Analytics**: Track opens and clicks
4. **Multi-language Support**: Translate email templates
5. **Custom Templates**: Allow vendors to customize email templates
6. **Notification Preferences**: Let users choose notification frequency
7. **WhatsApp Integration**: Send status updates via WhatsApp

## Best Practices

1. **Always include order/reference numbers** for customer reference
2. **Keep emails concise** with clear call-to-action buttons
3. **Use meaningful subject lines** for quick scanning
4. **Include relevant dates** (rental period, payment due, etc.)
5. **Provide direct action links** to relevant pages
6. **Test templates** with sample data before production
7. **Monitor delivery rates** and adjust as needed
8. **Keep sender email** consistent for brand recognition

