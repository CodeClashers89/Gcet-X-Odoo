# Testing Guide - Notification System

## Testing Overview

The notification system is production-ready and can be tested at multiple levels:
1. **Unit Testing** - Individual notification methods
2. **Integration Testing** - Full workflow with notifications
3. **Email Delivery Testing** - Verify emails are actually sent
4. **Template Testing** - Validate HTML rendering

---

## Unit Testing

### Test Setup

```python
# rentals/test_notifications.py

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.core.mail import outbox

from accounts.models import User
from rentals.models import (
    Product, RentalInquiry, Quotation, RentalOrder, 
    Payment, Invoice, RentalReturn
)
from rentals.notifications import RentalWorkflowNotifications


class NotificationTestCase(TestCase):
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='testpass123',
            role='customer',
            first_name='John',
            last_name='Doe'
        )
        
        self.vendor = User.objects.create_user(
            username='vendor',
            email='vendor@test.com',
            password='testpass123',
            role='vendor',
            first_name='Jane',
            last_name='Smith'
        )
        
        # Create product
        self.product = Product.objects.create(
            name='Test Equipment',
            description='Test Description',
            vendor=self.vendor,
            slug='test-equipment',
            is_published=True
        )
```

### Test Individual Notifications

#### Test Inquiry Submitted Notification
```python
def test_inquiry_submitted_notification(self):
    """Test customer inquiry submission notification"""
    # Create inquiry
    inquiry = RentalInquiry.objects.create(
        customer=self.customer,
        vendor=self.vendor,
        product=self.product,
        quantity=5,
        rental_start_date=timezone.now() + timedelta(days=1),
        rental_end_date=timezone.now() + timedelta(days=3),
        status='pending'
    )
    
    # Clear any previous emails
    outbox.clear()
    
    # Send notification
    RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)
    
    # Assertions
    self.assertEqual(len(outbox), 1)
    email = outbox[0]
    self.assertEqual(email.to, [self.customer.email])
    self.assertIn('Inquiry Submitted', email.subject)
    self.assertIn(inquiry.inquiry_number, email.body)
```

#### Test Vendor Inquiry Received Notification
```python
def test_vendor_inquiry_received_notification(self):
    """Test vendor inquiry received notification"""
    inquiry = RentalInquiry.objects.create(
        customer=self.customer,
        vendor=self.vendor,
        product=self.product,
        quantity=3,
        rental_start_date=timezone.now() + timedelta(days=5),
        rental_end_date=timezone.now() + timedelta(days=7),
        status='pending'
    )
    
    outbox.clear()
    RentalWorkflowNotifications.notify_vendor_inquiry_received(inquiry)
    
    self.assertEqual(len(outbox), 1)
    email = outbox[0]
    self.assertEqual(email.to, [self.vendor.email])
    self.assertIn('New Rental Inquiry', email.subject)
```

#### Test Inquiry Accepted Notification
```python
def test_inquiry_accepted_notification(self):
    """Test inquiry accepted notification"""
    inquiry = RentalInquiry.objects.create(
        customer=self.customer,
        vendor=self.vendor,
        product=self.product,
        quantity=2,
        rental_start_date=timezone.now() + timedelta(days=2),
        rental_end_date=timezone.now() + timedelta(days=4),
        status='accepted'
    )
    
    outbox.clear()
    RentalWorkflowNotifications.notify_customer_inquiry_accepted(inquiry)
    
    self.assertEqual(len(outbox), 1)
    email = outbox[0]
    self.assertEqual(email.to, [self.customer.email])
    self.assertIn('Accepted', email.subject)
```

#### Test Inquiry Rejected with Reason
```python
def test_inquiry_rejected_notification(self):
    """Test inquiry rejected notification with reason"""
    inquiry = RentalInquiry.objects.create(
        customer=self.customer,
        vendor=self.vendor,
        product=self.product,
        quantity=1,
        rental_start_date=timezone.now() + timedelta(days=1),
        rental_end_date=timezone.now() + timedelta(days=2),
        status='rejected'
    )
    
    outbox.clear()
    reason = "Not available for requested dates"
    RentalWorkflowNotifications.notify_customer_inquiry_rejected(inquiry, reason)
    
    self.assertEqual(len(outbox), 1)
    email = outbox[0]
    self.assertIn(reason, email.body)
```

### Running Unit Tests

```bash
# Run all notification tests
python manage.py test rentals.test_notifications

# Run specific test
python manage.py test rentals.test_notifications.NotificationTestCase.test_inquiry_submitted_notification

# Run with verbose output
python manage.py test rentals.test_notifications -v 2

# Run and keep test database
python manage.py test rentals.test_notifications --keepdb
```

---

## Integration Testing

### Test Complete Workflow with Notifications

```python
# rentals/test_workflow_integration.py

from django.test import TestCase
from django.core.mail import outbox
from django.utils import timezone
from datetime import timedelta

class WorkflowIntegrationTestCase(TestCase):
    
    def test_complete_inquiry_to_quotation_workflow(self):
        """Test complete workflow with all notifications"""
        
        # Setup
        customer = User.objects.create_user(...)
        vendor = User.objects.create_user(...)
        product = Product.objects.create(...)
        
        # Stage 1: Customer submits inquiry
        inquiry = RentalInquiry.objects.create(
            customer=customer,
            vendor=vendor,
            product=product,
            quantity=5,
            status='pending'
        )
        notify_inquiry_stage(inquiry, 'submitted')
        
        # Should have sent 2 emails (customer + vendor)
        self.assertEqual(len(outbox), 2)
        self.assertEqual(outbox[0].to, [customer.email])
        self.assertEqual(outbox[1].to, [vendor.email])
        
        # Stage 2: Vendor accepts inquiry
        outbox.clear()
        inquiry.status = 'accepted'
        inquiry.save()
        notify_inquiry_stage(inquiry, 'accepted')
        
        # Should have sent 1 email (customer only)
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0].to, [customer.email])
        
        # Stage 3: Vendor creates quotation
        outbox.clear()
        quotation = Quotation.objects.create(
            inquiry=inquiry,
            quotation_number='QT-001',
            total_amount=5000
        )
        notify_quotation_stage(quotation, 'sent')
        
        # Should have sent 1 email (customer)
        self.assertEqual(len(outbox), 1)
        
        # Stage 4: Customer accepts quotation
        outbox.clear()
        quotation.status = 'accepted'
        quotation.save()
        notify_quotation_stage(quotation, 'accepted')
        
        # Should have sent 1 email (vendor)
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0].to, [vendor.email])
```

### Test Payment and Invoice Workflow

```python
def test_payment_and_invoice_workflow(self):
    """Test payment received and invoice generation"""
    
    # Setup
    rental_order = RentalOrder.objects.create(...)
    
    # Stage 1: Payment received
    payment = Payment.objects.create(
        rental_order=rental_order,
        amount=5000,
        status='completed'
    )
    
    outbox.clear()
    notify_payment_stage(payment)
    
    # Should have sent 2 emails (customer + vendor)
    self.assertEqual(len(outbox), 2)
    
    # Stage 2: Invoice generated
    invoice = Invoice.objects.create(
        rental_order=rental_order,
        amount=5000
    )
    
    outbox.clear()
    notify_invoice_stage(invoice)
    
    # Should have sent 1 email (customer)
    self.assertEqual(len(outbox), 1)
```

---

## Email Delivery Testing

### Manual Testing in Django Shell

```bash
python manage.py shell
```

```python
from rentals.models import RentalInquiry
from rentals.notifications import RentalWorkflowNotifications

# Get or create test inquiry
inquiry = RentalInquiry.objects.first()

# Send notification
RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)

# Check if email was sent
from django.core.mail import outbox
print(f"Emails in outbox: {len(outbox)}")
if outbox:
    email = outbox[-1]
    print(f"To: {email.to}")
    print(f"Subject: {email.subject}")
    print(f"Body preview: {email.body[:200]}")
```

### Test Email Configuration

```bash
# Test Brevo SMTP connection
python test_brevo_smtp.py

# Test Django email configuration
python test_django_email.py
```

### Verify Template Rendering

```python
# In Django shell
from django.template.loader import render_to_string
from rentals.models import RentalInquiry

inquiry = RentalInquiry.objects.first()
context = {
    'customer_name': inquiry.customer.get_full_name(),
    'product_name': inquiry.product.name,
    'quantity': inquiry.quantity,
    'inquiry_number': inquiry.inquiry_number,
    'rental_start': inquiry.rental_start_date,
    'rental_end': inquiry.rental_end_date,
}

# Render template
html_output = render_to_string('rentals/emails/inquiry_submitted.html', context)

# Check if rendered correctly
print("Template rendered successfully!")
print(f"HTML length: {len(html_output)} characters")
print(f"Contains customer name: {inquiry.customer.get_full_name() in html_output}")
```

---

## Template Testing

### Visual Testing

1. **Get Email HTML**:
```python
from django.core.mail import outbox
from django.utils.html import strip_tags

email = outbox[-1]
print(email.body)  # Plain text
print(email.alternatives[0][0])  # HTML version
```

2. **Save to File**:
```python
with open('test_email.html', 'w') as f:
    f.write(email.alternatives[0][0])
```

3. **Open in Browser**:
   - Open `test_email.html` in a web browser to view rendering

### Test Template Variables

```python
def test_template_variables(self):
    """Test that all required variables are in template context"""
    
    inquiry = RentalInquiry.objects.create(...)
    
    context = {
        'customer_name': inquiry.customer.get_full_name(),
        'product_name': inquiry.product.name,
        'quantity': inquiry.quantity,
        'inquiry_number': inquiry.inquiry_number,
        'rental_start': inquiry.rental_start_date,
        'rental_end': inquiry.rental_end_date,
    }
    
    html = render_to_string('rentals/emails/inquiry_submitted.html', context)
    
    # Check all variables are rendered
    self.assertIn(context['customer_name'], html)
    self.assertIn(context['product_name'], html)
    self.assertIn(context['inquiry_number'], html)
```

### Test Email Styling

```python
def test_email_styling(self):
    """Test that emails are properly styled"""
    
    inquiry = RentalInquiry.objects.create(...)
    
    context = {
        'customer_name': inquiry.customer.get_full_name(),
        'product_name': inquiry.product.name,
        'quantity': inquiry.quantity,
        'inquiry_number': inquiry.inquiry_number,
        'rental_start': inquiry.rental_start_date,
        'rental_end': inquiry.rental_end_date,
    }
    
    html = render_to_string('rentals/emails/inquiry_submitted.html', context)
    
    # Check for styling
    self.assertIn('<style>', html)
    self.assertIn('background-color', html)
    self.assertIn('color:', html)
```

---

## Performance Testing

### Test Notification Delivery Speed

```python
import time
from rentals.notifications import RentalWorkflowNotifications

def test_notification_performance(self):
    """Test notification delivery time"""
    
    inquiry = RentalInquiry.objects.create(...)
    
    start_time = time.time()
    RentalWorkflowNotifications.notify_customer_inquiry_submitted(inquiry)
    end_time = time.time()
    
    delivery_time = end_time - start_time
    print(f"Notification delivered in {delivery_time:.2f} seconds")
    
    # Assert it's reasonably fast (under 5 seconds)
    self.assertLess(delivery_time, 5.0)
```

### Test Bulk Notifications

```python
def test_bulk_reminder_notifications(self):
    """Test sending many reminders"""
    
    # Create multiple orders needing reminders
    orders = []
    for i in range(100):
        order = RentalOrder.objects.create(
            pickup_date=timezone.now() + timedelta(hours=25),
            ...
        )
        orders.append(order)
    
    # Time bulk notification
    start_time = time.time()
    for order in orders:
        RentalWorkflowNotifications.notify_customer_pickup_reminder(order)
    end_time = time.time()
    
    total_time = end_time - start_time
    print(f"Sent {len(orders)} reminders in {total_time:.2f} seconds")
    print(f"Average: {total_time/len(orders):.2f}s per notification")
```

---

## Testing Reminders

### Test Management Command

```bash
# Run the reminder command
python manage.py send_rental_reminders

# Should output:
# ✓ Pickup reminder sent for order ORD-001
# ✓ Pickup reminder sent for order ORD-002
# ✓ Return reminder sent for order ORD-003
# Rental reminders sent successfully
```

### Test Reminder Logic

```python
def test_pickup_reminder_logic(self):
    """Test that pickup reminders are sent correctly"""
    
    now = timezone.now()
    
    # Create order with pickup in ~24 hours
    order1 = RentalOrder.objects.create(
        pickup_date=now + timedelta(hours=24, minutes=30),
        status='confirmed'
    )
    
    # Create order with pickup way in future
    order2 = RentalOrder.objects.create(
        pickup_date=now + timedelta(days=10),
        status='confirmed'
    )
    
    # Only order1 should get reminder
    tomorrow = now + timedelta(hours=24)
    tomorrow_end = now + timedelta(hours=25)
    
    pending_reminders = RentalOrder.objects.filter(
        pickup_date__gte=tomorrow,
        pickup_date__lte=tomorrow_end,
        status='confirmed'
    )
    
    self.assertEqual(pending_reminders.count(), 1)
    self.assertIn(order1, pending_reminders)
```

---

## Continuous Integration Testing

### GitHub Actions Example

```yaml
# .github/workflows/test-notifications.yml

name: Test Notifications

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run notification tests
        run: |
          python manage.py test rentals.test_notifications -v 2
      
      - name: Run integration tests
        run: |
          python manage.py test rentals.test_workflow_integration -v 2
```

---

## Troubleshooting Test Failures

### Email Not Sending in Tests

**Problem**: `outbox` is empty
**Solution**:
```python
# Ensure you're using correct email backend in test
# settings.py
if 'test' in sys.argv:
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
```

### Template Not Found

**Problem**: TemplateDoesNotExist error
**Solution**:
```python
# Verify TEMPLATES configuration
# Check that 'APP_DIRS': True is set
# Check that 'templates' directory exists
```

### Context Variable Missing

**Problem**: Variable shows as empty in template
**Solution**:
```python
# Debug context
from django.template.loader import render_to_string
html = render_to_string('template.html', context)
print(context)  # Print context to verify variables
```

---

## Test Coverage Target

Aim for >90% coverage of notification code:

```bash
# Generate coverage report
coverage run --source='rentals.notifications' manage.py test rentals
coverage report

# Generate HTML report
coverage html
# Open htmlcov/index.html in browser
```

---

## Best Practices

1. **Always clear outbox** before sending test notifications
2. **Use setUp()** to avoid repeating test data creation
3. **Test both success and failure** scenarios
4. **Verify email content**, not just delivery
5. **Test template rendering** independently
6. **Mock external services** if integrating SMS/payment gateways
7. **Test with realistic data** (long names, special characters)
8. **Verify email headers** (From, Subject, etc.)

---

**Last Updated**: January 31, 2025
**Status**: Ready for Testing

