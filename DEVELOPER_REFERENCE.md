# Developer Reference - Notification System API

## Quick Reference Card

### Import Statement
```python
from rentals.notifications import (
    NotificationService,
    RentalWorkflowNotifications,
    notify_inquiry_stage,
    notify_quotation_stage,
    notify_order_stage,
    notify_payment_stage,
    notify_invoice_stage,
    notify_return_stage,
)
```

## All Available Methods

### Inquiry Notifications (4 methods)

#### 1. `notify_customer_inquiry_submitted(inquiry)`
- **When**: Customer submits a rental inquiry
- **Recipient**: Customer
- **Context**: inquiry_number, product_name, quantity, rental dates
- **Template**: inquiry_submitted.html
```python
inquiry = RentalInquiry.objects.create(...)
RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)
```

#### 2. `notify_vendor_inquiry_received(inquiry)`
- **When**: Vendor receives a new inquiry
- **Recipient**: Vendor
- **Context**: inquiry details, customer name, inquiry_url
- **Template**: vendor_inquiry_received.html
```python
RentalWorkflowNotifications.notify_vendor_inquiry_received(inquiry)
```

#### 3. `notify_customer_inquiry_accepted(inquiry)`
- **When**: Vendor accepts customer's inquiry
- **Recipient**: Customer
- **Context**: inquiry_number, vendor_name, product_name
- **Template**: inquiry_accepted.html
```python
inquiry.status = 'accepted'
inquiry.save()
RentalWorkflowNotifications.notify_customer_inquiry_accepted(inquiry)
```

#### 4. `notify_customer_inquiry_rejected(inquiry, reason='')`
- **When**: Vendor rejects customer's inquiry
- **Recipient**: Customer
- **Context**: inquiry_number, vendor_name, product_name, reason (optional)
- **Template**: inquiry_rejected.html
```python
inquiry.status = 'rejected'
inquiry.save()
RentalWorkflowNotifications.notify_customer_inquiry_rejected(
    inquiry,
    reason="Product not available for selected dates"
)
```

### Quotation Notifications (2 methods)

#### 5. `notify_customer_quotation_sent(quotation)`
- **When**: Vendor sends quotation to customer
- **Recipient**: Customer
- **Context**: quotation_number, total_amount, valid_until, quotation_url
- **Template**: quotation_sent.html
```python
quotation = Quotation.objects.create(...)
RentalWorkflowNotifications.notify_customer_quotation_sent(quotation)
```

#### 6. `notify_vendor_quotation_accepted(quotation)`
- **When**: Customer accepts quotation
- **Recipient**: Vendor
- **Context**: quotation_number, total_amount, customer_name
- **Template**: vendor_quotation_accepted.html
```python
quotation.status = 'accepted'
quotation.save()
RentalWorkflowNotifications.notify_vendor_quotation_accepted(quotation)
```

### Order Notifications (2 methods)

#### 7. `notify_customer_order_confirmed(rental_order)`
- **When**: Rental order is confirmed
- **Recipient**: Customer
- **Context**: order_number, total_amount, rental dates, pickup_location, order_url
- **Template**: order_confirmed.html
```python
rental_order.status = 'confirmed'
rental_order.save()
RentalWorkflowNotifications.notify_customer_order_confirmed(rental_order)
```

#### 8. `notify_customer_order_rejected(rental_order, reason='')`
- **When**: Order could not be confirmed
- **Recipient**: Customer
- **Context**: order_number, reason (optional)
- **Template**: order_rejected.html
```python
RentalWorkflowNotifications.notify_customer_order_rejected(
    rental_order,
    reason="Payment failed"
)
```

### Payment Notifications (2 methods)

#### 9. `notify_customer_payment_received(payment)`
- **When**: Payment received from customer
- **Recipient**: Customer
- **Context**: order_number, payment_number, amount, payment_date, payment_method
- **Template**: payment_received.html
```python
payment.status = 'completed'
payment.save()
RentalWorkflowNotifications.notify_customer_payment_received(payment)
```

#### 10. `notify_vendor_payment_received(payment)`
- **When**: Payment received for vendor's product
- **Recipient**: Vendor
- **Context**: order_number, customer_name, amount
- **Template**: vendor_payment_received.html
```python
RentalWorkflowNotifications.notify_vendor_payment_received(payment)
```

### Invoice Notifications (1 method)

#### 11. `notify_customer_invoice_generated(invoice)`
- **When**: Invoice generated after payment
- **Recipient**: Customer
- **Context**: invoice_number, order_number, amount, due_date, invoice_url
- **Template**: invoice_generated.html
```python
invoice = Invoice.objects.create(...)
RentalWorkflowNotifications.notify_customer_invoice_generated(invoice)
```

### Reminder Notifications (2 methods)

#### 12. `notify_customer_pickup_reminder(rental_order, days_until_pickup=1)`
- **When**: 24 hours before scheduled pickup
- **Recipient**: Customer
- **Context**: order_number, pickup_date, pickup_location, days_until
- **Template**: pickup_reminder.html
```python
RentalWorkflowNotifications.notify_customer_pickup_reminder(
    rental_order,
    days_until_pickup=1
)
```

#### 13. `notify_customer_return_reminder(rental_order, days_until_return=1)`
- **When**: 24 hours before return date
- **Recipient**: Customer
- **Context**: order_number, return_date, days_until
- **Template**: return_reminder.html
```python
RentalWorkflowNotifications.notify_customer_return_reminder(
    rental_order,
    days_until_return=1
)
```

### Return & Settlement Notifications (3 methods)

#### 14. `notify_vendor_return_initiated(rental_return)`
- **When**: Customer initiates return process
- **Recipient**: Vendor
- **Context**: return_number, order_number, customer_name, return_expected_date
- **Template**: vendor_return_initiated.html
```python
rental_return = RentalReturn.objects.create(...)
RentalWorkflowNotifications.notify_vendor_return_initiated(rental_return)
```

#### 15. `notify_customer_rental_settled(rental_return)`
- **When**: Rental fully settled with refund
- **Recipient**: Customer
- **Context**: return_number, refund_amount, damage_cost, late_fees, settled_at
- **Template**: rental_settled.html
```python
rental_return.status = 'settled'
rental_return.save()
RentalWorkflowNotifications.notify_customer_rental_settled(rental_return)
```

#### 16. `notify_vendor_rental_settled(rental_return)`
- **When**: Rental fully settled
- **Recipient**: Vendor
- **Context**: return_number, customer_name, damage_cost, late_fees, settled_at
- **Template**: vendor_rental_settled.html
```python
RentalWorkflowNotifications.notify_vendor_rental_settled(rental_return)
```

## Convenience Functions

### `notify_inquiry_stage(inquiry, stage, reason='')`
Smart function that calls appropriate methods based on stage.

**Stages**:
- `'submitted'` → calls both customer and vendor notification
- `'accepted'` → calls customer accepted notification
- `'rejected'` → calls customer rejected notification with reason

```python
# Instead of:
RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)
RentalWorkflowNotifications.notify_vendor_inquiry_received(inquiry)

# Use:
notify_inquiry_stage(inquiry, 'submitted')
```

### `notify_quotation_stage(quotation, stage)`
**Stages**:
- `'sent'` → notify_customer_quotation_sent()
- `'accepted'` → notify_vendor_quotation_accepted()

```python
notify_quotation_stage(quotation, 'sent')
```

### `notify_order_stage(rental_order, stage, reason='')`
**Stages**:
- `'confirmed'` → notify_customer_order_confirmed()
- `'rejected'` → notify_customer_order_rejected()

```python
notify_order_stage(rental_order, 'confirmed')
```

### `notify_payment_stage(payment)`
Sends both customer and vendor notifications.

```python
notify_payment_stage(payment)
```

### `notify_invoice_stage(invoice)`
Sends invoice notification to customer.

```python
notify_invoice_stage(invoice)
```

### `notify_return_stage(rental_return, stage)`
**Stages**:
- `'initiated'` → notify_vendor_return_initiated()
- `'settled'` → sends both customer and vendor settled notifications

```python
notify_return_stage(rental_return, 'settled')
```

## Low-Level API

### `NotificationService.send_email(subject, recipient_email, template_name, context)`

Direct email sending (use for custom notifications).

```python
from rentals.notifications import NotificationService

NotificationService.send_email(
    subject="Custom Notification",
    recipient_email="customer@example.com",
    template_name="rentals/emails/custom_email.html",
    context={
        'customer_name': 'John Doe',
        'custom_variable': 'value',
    }
)
```

**Parameters**:
- `subject` (str): Email subject line
- `recipient_email` (str): Recipient email address
- `template_name` (str): Path to Django template
- `context` (dict): Template context variables

**Returns**: Boolean (True if successful, False if failed)

### `NotificationService.send_sms(phone_number, message)`

SMS sending placeholder (ready for SMS integration).

```python
from rentals.notifications import NotificationService

NotificationService.send_sms(
    phone_number="+919876543210",
    message="Your rental order is confirmed!"
)
```

**Parameters**:
- `phone_number` (str): Recipient phone number with country code
- `message` (str): SMS message text

**Returns**: Boolean (True if successful, False if failed)

## Usage Examples by Scenario

### Scenario 1: Complete Inquiry Workflow
```python
# 1. Customer submits inquiry
inquiry = RentalInquiry.objects.create(
    customer=request.user,
    product=product,
    vendor=vendor,
    quantity=5,
    rental_start_date=start_date,
    rental_end_date=end_date,
    status='pending'
)
notify_inquiry_stage(inquiry, 'submitted')  # Sends 2 emails

# 2. Vendor reviews and accepts
inquiry.status = 'accepted'
inquiry.save()
notify_inquiry_stage(inquiry, 'accepted')  # Sends 1 email

# 3. Vendor creates quotation
quotation = Quotation.objects.create(
    inquiry=inquiry,
    quotation_number='QT-001',
    total_amount=5000,
    valid_until=timezone.now() + timedelta(days=7)
)
notify_quotation_stage(quotation, 'sent')  # Sends 1 email

# 4. Customer accepts quotation
quotation.status = 'accepted'
quotation.save()
notify_quotation_stage(quotation, 'accepted')  # Sends 1 email
```

### Scenario 2: Complete Payment & Invoice Workflow
```python
# 1. Payment received
payment = Payment.objects.create(
    rental_order=rental_order,
    amount=5000,
    payment_method='card',
    status='completed',
    transaction_id='TXN-001'
)
notify_payment_stage(payment)  # Sends 2 emails

# 2. Generate invoice
invoice = Invoice.objects.create(
    rental_order=rental_order,
    invoice_number='INV-001',
    amount=5000,
    total_amount=5000
)
notify_invoice_stage(invoice)  # Sends 1 email
```

### Scenario 3: Return & Settlement Workflow
```python
# 1. Return initiated
rental_return = RentalReturn.objects.create(
    rental_order=rental_order,
    return_number='RET-001',
    return_expected_date=timezone.now() + timedelta(days=1),
    status='initiated'
)
notify_return_stage(rental_return, 'initiated')  # Sends 1 email

# 2. Return settled
rental_return.status = 'settled'
rental_return.settled_at = timezone.now()
rental_return.damage_cost = 500
rental_return.late_return_fees = 200
rental_return.refund_amount = 4300
rental_return.save()
notify_return_stage(rental_return, 'settled')  # Sends 2 emails
```

## Context Variable Reference

### Common Variables (all emails)
- `customer_name` - str: Full name of customer
- `vendor_name` - str: Full name of vendor
- `email` - str: Email address

### Inquiry Context
- `inquiry_number` - str: Unique inquiry reference
- `product_name` - str: Name of product
- `quantity` - int: Number of units
- `rental_start` - date: Rental start date
- `rental_end` - date: Rental end date
- `inquiry_url` - str: Link to inquiry page

### Quotation Context
- `quotation_number` - str: Unique quotation reference
- `total_amount` - decimal: Quotation amount
- `valid_until` - datetime: Quotation expiry
- `quotation_url` - str: Link to quotation page

### Order Context
- `order_number` - str: Unique order reference
- `total_amount` - decimal: Order amount
- `rental_start` - date: Rental start
- `rental_end` - date: Rental end
- `pickup_location` - str: Pickup address
- `order_url` - str: Link to order page

### Payment Context
- `payment_number` - str: Payment reference
- `amount` - decimal: Payment amount
- `payment_date` - datetime: When paid
- `payment_method` - str: Payment method (card, UPI, etc.)

### Invoice Context
- `invoice_number` - str: Invoice reference
- `due_date` - date: Payment due date
- `amount` - decimal: Invoice amount
- `invoice_url` - str: Link to invoice

### Return Context
- `return_number` - str: Return reference
- `return_date` - date: Return date
- `return_expected_date` - date: Expected return date
- `damage_cost` - decimal: Damage charges
- `late_fees` - decimal: Late return fees
- `refund_amount` - decimal: Refund to customer
- `settled_at` - datetime: Settlement date

## Template Customization

### Accessing Context in Templates
```html
<!-- Simple variable -->
<p>Hi {{ customer_name }},</p>

<!-- Date formatting -->
<p>Your rental starts on {{ rental_start|date:"d M Y" }}</p>

<!-- Currency formatting -->
<p>Total amount: ₹{{ total_amount }}</p>

<!-- Conditional display -->
{% if reason %}
  <p>Reason: {{ reason }}</p>
{% endif %}

<!-- Loops -->
{% for item in items %}
  <p>{{ item.name }} - ₹{{ item.price }}</p>
{% endfor %}
```

### Modifying Default Templates

1. Find template in `templates/rentals/emails/`
2. Edit HTML and text content
3. Keep Django template tags intact
4. Test with: `python manage.py shell`

```python
from rentals.models import RentalInquiry
from rentals.notifications import RentalWorkflowNotifications
inquiry = RentalInquiry.objects.first()
RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)
```

## Error Handling

All notification methods include try/catch blocks. Failures are logged but don't break workflow.

```python
# This won't crash even if email fails
RentalWorkflowNotifications.notify_customer_order_confirmed(order)
# Check logs for any delivery errors
```

To handle failures explicitly:

```python
result = NotificationService.send_email(
    subject="Order Confirmation",
    recipient_email=customer.email,
    template_name="rentals/emails/order_confirmed.html",
    context={'order_number': order.order_number}
)

if not result:
    # Email failed, implement fallback logic
    log_failed_notification(customer, 'order_confirmed')
```

## Testing

### Test in Django Shell
```python
python manage.py shell

from rentals.models import RentalInquiry
from rentals.notifications import RentalWorkflowNotifications

inquiry = RentalInquiry.objects.first()
RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)
```

### View Sent Emails (testing)
```python
from django.core.mail import outbox
print(f"Total emails: {len(outbox)}")
print(outbox[-1].subject)
print(outbox[-1].from_email)
print(outbox[-1].to)
```

### Test Email Configuration
```bash
python test_django_email.py
```

## Performance Considerations

- All notifications are sent synchronously
- For high-volume scenarios, consider Celery task queue
- Each email takes ~1-2 seconds

### Add Async Notifications with Celery

```python
# rentals/tasks.py
from celery import shared_task
from rentals.notifications import RentalWorkflowNotifications

@shared_task
def send_inquiry_notification(inquiry_id):
    inquiry = RentalInquiry.objects.get(id=inquiry_id)
    RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)

# In view
from rentals.tasks import send_inquiry_notification
inquiry = RentalInquiry.objects.create(...)
send_inquiry_notification.delay(inquiry.id)
```

---

**Last Updated**: January 31, 2025
**System Status**: ✅ Production Ready

