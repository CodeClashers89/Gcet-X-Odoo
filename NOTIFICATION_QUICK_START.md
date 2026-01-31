# Quick Integration Guide - Notification System

## Fast Setup (5 minutes)

### 1. Verify Email Configuration
Email is already configured with Brevo SMTP in `settings.py`. Verify by running:

```bash
python test_django_email.py
```

Expected output:
```
✓ Email configuration is correct!
✓ Simple email sent successfully! Result: 1
✓ HTML email sent successfully! Result: 1
```

### 2. Import and Use in Views

**Step 1: Import the notification module**
```python
from rentals.notifications import RentalWorkflowNotifications, notify_inquiry_stage
```

**Step 2: Call notification method after creating model instance**
```python
# After creating RentalInquiry
inquiry = RentalInquiry.objects.create(...)
RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)
RentalWorkflowNotifications.notify_vendor_inquiry_received(inquiry)
```

**Step 3: Or use convenience functions**
```python
notify_inquiry_stage(inquiry, 'submitted')
```

### 3. Common Implementation Patterns

#### A. Customer Submits Inquiry
```python
# In rentals/views.py
def create_inquiry(request):
    inquiry = RentalInquiry.objects.create(
        customer=request.user,
        product=product,
        vendor=vendor,
        quantity=quantity,
        rental_start_date=start_date,
        rental_end_date=end_date,
        status='pending'
    )
    
    # Send notifications
    RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)
    RentalWorkflowNotifications.notify_vendor_inquiry_received(inquiry)
    
    return redirect('rentals:inquiry_success')
```

#### B. Vendor Responds to Inquiry
```python
def vendor_accept_inquiry(request, inquiry_id):
    inquiry = RentalInquiry.objects.get(id=inquiry_id)
    inquiry.status = 'accepted'
    inquiry.save()
    
    # Send notification
    RentalWorkflowNotifications.notify_customer_inquiry_accepted(inquiry)
    
    return redirect('rentals:create_quotation', inquiry_id=inquiry_id)
```

#### C. Payment Processing Complete
```python
def payment_webhook(request):
    payment = Payment.objects.get(id=request.data['payment_id'])
    payment.status = 'completed'
    payment.transaction_id = request.data['transaction_id']
    payment.save()
    
    # Send notifications
    RentalWorkflowNotifications.notify_customer_payment_received(payment)
    RentalWorkflowNotifications.notify_vendor_payment_received(payment)
    
    # Create invoice
    invoice = Invoice.objects.create(
        rental_order=payment.rental_order,
        invoice_number=f"INV-{payment.rental_order.id}",
        amount=payment.amount
    )
    RentalWorkflowNotifications.notify_customer_invoice_generated(invoice)
```

#### D. Return Process Complete
```python
def settle_return(request, return_id):
    rental_return = RentalReturn.objects.get(id=return_id)
    rental_return.status = 'settled'
    rental_return.settled_at = timezone.now()
    rental_return.save()
    
    # Send notifications
    RentalWorkflowNotifications.notify_customer_rental_settled(rental_return)
    RentalWorkflowNotifications.notify_vendor_rental_settled(rental_return)
```

### 4. Set Up Scheduled Reminders

**Option A: Manual (for testing)**
```bash
# Run once daily
python manage.py send_rental_reminders
```

**Option B: Cron Job (Linux/Mac)**
```bash
# Add to crontab (run at 9 AM daily)
0 9 * * * cd /path/to/GCETxOdoo && python manage.py send_rental_reminders
```

**Option C: Celery Beat (Recommended for production)**
See section 3 of [NOTIFICATION_SYSTEM.md](NOTIFICATION_SYSTEM.md)

### 5. Test a Notification

```python
# Run from Django shell
python manage.py shell

from rentals.models import RentalInquiry
from rentals.notifications import RentalWorkflowNotifications

# Get existing inquiry or create test one
inquiry = RentalInquiry.objects.first()

# Send test notification
RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)

# Check console/logs for success
```

## All Available Methods

### Notification Methods by Stage

| Stage | Customer Method | Vendor Method |
|-------|-----------------|---------------|
| Inquiry Submission | `notify_customer_inquiry_submitted()` | `notify_vendor_inquiry_received()` |
| Inquiry Accepted | `notify_customer_inquiry_accepted()` | - |
| Inquiry Rejected | `notify_customer_inquiry_rejected()` | - |
| Quotation Sent | `notify_customer_quotation_sent()` | - |
| Quotation Accepted | - | `notify_vendor_quotation_accepted()` |
| Order Confirmed | `notify_customer_order_confirmed()` | - |
| Order Rejected | `notify_customer_order_rejected()` | - |
| Payment Received | `notify_customer_payment_received()` | `notify_vendor_payment_received()` |
| Invoice Generated | `notify_customer_invoice_generated()` | - |
| Pickup Reminder | `notify_customer_pickup_reminder()` | - |
| Return Reminder | `notify_customer_return_reminder()` | - |
| Return Initiated | - | `notify_vendor_return_initiated()` |
| Rental Settled | `notify_customer_rental_settled()` | `notify_vendor_rental_settled()` |

### Convenience Functions

```python
# Use these instead of individual methods for common scenarios
from rentals.notifications import (
    notify_inquiry_stage,      # inquiry + stage
    notify_quotation_stage,    # quotation + stage
    notify_order_stage,        # order + stage
    notify_payment_stage,      # payment (auto sends both)
    notify_invoice_stage,      # invoice (auto sends customer)
    notify_return_stage,       # return + stage
)
```

## Email Template Files

All templates are in `templates/rentals/emails/`:

| Template File | Used For |
|---|---|
| `inquiry_submitted.html` | Customer inquiry confirmation |
| `vendor_inquiry_received.html` | Vendor new inquiry alert |
| `inquiry_accepted.html` | Customer - vendor accepted inquiry |
| `inquiry_rejected.html` | Customer - vendor rejected inquiry |
| `quotation_sent.html` | Customer - quotation ready |
| `vendor_quotation_accepted.html` | Vendor - customer accepted quote |
| `order_confirmed.html` | Customer - rental order confirmed |
| `order_rejected.html` | Customer - order could not be confirmed |
| `payment_received.html` | Customer - payment confirmation |
| `vendor_payment_received.html` | Vendor - payment received |
| `invoice_generated.html` | Customer - invoice ready |
| `pickup_reminder.html` | Customer - pickup in 24 hours |
| `return_reminder.html` | Customer - return in 24 hours |
| `vendor_return_initiated.html` | Vendor - return started |
| `rental_settled.html` | Customer - settlement with refund |
| `vendor_rental_settled.html` | Vendor - settlement summary |

## Customizing Templates

1. **Edit template** in `templates/rentals/emails/template_name.html`
2. **Available variables** - Check the notification method in `rentals/notifications.py` to see what context is provided
3. **Test** - Run the notification method again to verify changes

Example modification (add custom message):

```html
<!-- In templates/rentals/emails/quotation_sent.html -->
<p>Hi {{ customer_name }},</p>

<!-- Add custom section -->
<div class="special-offer">
    <p>Use code SPECIAL20 for 20% discount on your next rental!</p>
</div>

<p>{{ vendor_name }} has sent you a quotation...</p>
```

## Debugging

### Check if email was sent
```python
# In Django shell
from django.core.mail import outbox
print(f"Emails sent: {len(outbox)}")
for email in outbox:
    print(f"To: {email.to}")
    print(f"Subject: {email.subject}")
```

### View email content
```python
from django.core.mail import outbox
email = outbox[-1]  # Last email
print(email.body)  # Plain text version
print(email.alternatives)  # HTML version
```

### Check Brevo SMTP connectivity
```bash
python test_brevo_smtp.py
```

## Production Checklist

- [ ] Verify Brevo SMTP credentials in `.env`
- [ ] Set `DEFAULT_FROM_EMAIL` to your domain email
- [ ] Test all notification methods with real data
- [ ] Set up scheduled reminders (cron or Celery)
- [ ] Monitor email delivery via Brevo dashboard
- [ ] Set up error logging for failed notifications
- [ ] Train vendors on when notifications are sent
- [ ] Document notification schedule for support team

## Common Issues & Fixes

**Issue**: "SMTPAuthenticationError"
- Fix: Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in `.env`

**Issue**: "Template not found" error
- Fix: Ensure `templates/rentals/emails/` directory exists and template file is there

**Issue**: Emails have missing information
- Fix: Verify context dictionary in notification method matches template variables

**Issue**: Reminders not sent at scheduled time
- Fix: Confirm cron job is running: `crontab -l`
- Fix: Check cron logs: `grep CRON /var/log/syslog`

