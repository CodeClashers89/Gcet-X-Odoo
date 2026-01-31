# Rental Management ERP - Quick Reference Guide

## Current Project Status
✅ **Phase 4 Complete**: Authentication & Role-Based Access Control
- Database models: 40+ models across 6 apps
- Admin panel: Fully configured with business logic
- Authentication: Complete signup/login/password reset flow
- Dashboards: Role-based landing pages
- UI: Clean CSS3 templates with no frameworks
- Server: Running on http://127.0.0.1:8000/

## Directory Structure
```
d:\GCETxOdoo/
├── db.sqlite3                          # SQLite database (auto-generated)
├── manage.py                           # Django CLI
├── requirements.txt                    # (Optional) dependencies list
├── PHASE_4_COMPLETION.md              # Phase 4 summary
├── rental_erp/                        # Project settings & main URLs
│   ├── settings.py                    # Django configuration
│   ├── urls.py                        # Main URL routing
│   └── wsgi.py/asgi.py
│
├── accounts/                          # User authentication & profiles
│   ├── models.py                      # User, CustomerProfile, VendorProfile (283 lines)
│   ├── forms.py                       # All signup/login/password forms (650 lines)
│   ├── views.py                       # Authentication views (780 lines)
│   ├── urls.py                        # Authentication routes
│   ├── admin.py                       # Admin panel configuration
│   └── migrations/
│
├── catalog/                           # Product catalog & attributes
│   ├── models.py                      # Product, Variant, Pricing (424 lines)
│   ├── admin.py                       # Admin management
│   └── migrations/
│
├── rentals/                           # Rental workflow
│   ├── models.py                      # Quotation, Order, Reservation, Pickup, Return (625 lines)
│   ├── admin.py                       # Admin management
│   └── migrations/
│
├── billing/                           # Invoicing & payments
│   ├── models.py                      # Invoice, InvoiceLine, Payment (419 lines)
│   ├── admin.py                       # Admin management
│   └── migrations/
│
├── system_settings/                   # Global configuration
│   ├── models.py                      # SystemConfiguration, LateFeePolicy, GSTConfiguration (357 lines)
│   ├── admin.py                       # Admin management
│   └── migrations/
│
├── audit/                             # Change tracking
│   ├── models.py                      # AuditLog model (253 lines)
│   ├── admin.py                       # Read-only audit trail
│   └── migrations/
│
├── dashboards/                        # Dashboard views
│   ├── views.py                       # Role-based dashboard router
│   ├── urls.py                        # Dashboard routes
│   └── migrations/
│
├── templates/                         # HTML templates
│   ├── base.html                      # Base template with navigation
│   ├── accounts/
│   │   ├── login.html                 # Login form
│   │   ├── signup_customer.html       # Customer registration with GSTIN validation
│   │   ├── signup_vendor.html         # Vendor registration with banking info
│   │   ├── profile.html               # User profile editor
│   │   └── change_password.html       # Password change form
│   └── dashboards/
│       ├── customer_dashboard.html    # Customer stats & quick actions
│       ├── vendor_dashboard.html      # Vendor stats & inventory management
│       └── admin_dashboard.html       # Admin quick links
│
└── static/                            # (For future) CSS/JS files
```

## Key Models & Relationships

### Authentication & Users
```
User (custom, extends AbstractUser)
├── role: customer | vendor | admin
├── is_verified: email verification flag
├── phone: contact number
├── OneToOne: CustomerProfile (if customer)
└── OneToOne: VendorProfile (if vendor)

CustomerProfile
├── user: OneToOne User
├── company_name: Legal entity name
├── gstin: GST ID (validated)
├── state: For GST calculation
├── billing_address: Invoice address
├── total_orders, total_spent: Stats

VendorProfile
├── user: OneToOne User
├── company_name, gstin, state
├── bank_account_number, bank_ifsc_code
├── is_approved: Admin approval flag
├── total_products, total_rentals, total_revenue: Stats
└── approved_at: Timestamp
```

### Quotation to Invoice Flow
```
Quotation
├── customer: FK User
├── status: draft → sent → confirmed → cancelled
├── quotation_lines: FK QuotationLine
├── valid_until: Expiration date
└── calculate_totals(): Recalculate from lines

QuotationLine
├── quotation: FK Quotation
├── product: FK Product
├── product_variant: FK ProductVariant
├── rental_start_date, rental_end_date
├── quantity, unit_price, line_total

RentalOrder (created from confirmed Quotation)
├── quotation: OneToOne Quotation
├── customer, vendor: FK Users
├── status: draft → confirmed → in_progress → completed
├── delivery_address, billing_address
├── subtotal, discount, tax, late_fee, total
├── deposit_amount, paid_amount, balance_due
└── rental_order_lines: FK RentalOrderLine

RentalOrderLine
├── rental_order: FK RentalOrder
├── actual_pickup_date, actual_return_date
├── is_late_return: Boolean
├── late_days, late_fee_charged
└── calculate_late_fee(): Queries LateFeePolicy
```

### Inventory & Reservations
```
Product
├── vendor: FK User
├── is_rentable: Boolean
├── quantity_on_hand: Integer
├── cost_price, rental_pricing: Relationships
├── product_variants: FK ProductVariant
├── get_available_quantity(): on_hand - reserved

ProductVariant
├── product: FK Product
├── variant_name, SKU
├── quantity_on_hand
└── get_available_quantity(): Variant-specific availability

Reservation (blocks inventory for rental period)
├── rental_order_line: FK RentalOrderLine
├── product, product_variant: FK
├── rental_start_date, rental_end_date
├── status: confirmed → active → completed
└── Indexes: (product, status, dates) for fast availability queries
```

### Billing & Payments
```
Invoice
├── rental_order: FK RentalOrder
├── customer, vendor: FK Users
├── billing_gstin, vendor_gstin: For GST
├── is_intrastate: CGST+SGST or IGST
├── cgst_rate, sgst_rate, igst_rate, amounts
├── subtotal, tax_amount, total
├── paid_amount, balance_due, deposit_collected
├── calculate_gst(): Intra vs inter-state logic
└── invoice_lines: FK InvoiceLine

Payment
├── invoice: FK Invoice
├── customer: FK User
├── amount, payment_method: cash|card|upi|razorpay
├── transaction_id, gateway_response: JSON
├── is_refund: Boolean
├── original_payment: Self FK (for refund chains)
└── process_payment(): Updates invoice status
```

### Configuration & Policies
```
SystemConfiguration (singleton, pk=1)
├── Company details: name, GSTIN, address
├── Tax rates: default_cgst, default_sgst, default_igst
├── API keys: brevo_api_key, appyflow_api_key, razorpay_key
├── Rental settings: min_hours, quotation_validity_days
├── Notification flags: send_emails, reminder_hours
└── get_config(): Static getter

LateFeePolicy
├── name, description
├── grace_period_hours
├── penalty_calculation: per_day | per_hour | percentage
├── penalty_rate_*, max_penalty_cap
├── product_categories: M2M
└── effective_from, effective_until

GSTConfiguration
├── category: FK ProductCategory
├── hsn_code: For tax classification
├── cgst_rate, sgst_rate, igst_rate
└── effective_from, effective_until
```

### Audit Tracking
```
AuditLog (read-only in admin)
├── user: FK User (nullable for system actions)
├── action_type: create | update | delete | state_change | payment
├── model_name, object_id, field_name
├── old_value, new_value, description
├── ip_address, user_agent, session_key
├── timestamp: auto_indexed
└── log_action(): Classmethod for convenience
```

## Admin Interface
- All 6 apps fully registered with comprehensive management UIs
- Color-coded status badges (HTML formatting)
- Bulk actions (approve vendors, publish products, process payments)
- Inline management (ProductVariant, RentalPricing, InvoiceLine)
- Read-only fields for calculated values
- Queryset filtering by role (vendors see only own products)
- Dynamic inlines (show customer profile for customers, vendor for vendors)

## Authentication Flow
1. **Signup**: Choose customer or vendor
   - Customer: Basic info + company/GSTIN
   - Vendor: Basic info + company/bank details + pending approval
2. **Email Verification**: Click link to activate account
3. **Login**: Email + password
   - Vendor check: Can only login if is_approved=True
4. **Dashboard**: Role-specific landing page
   - Customers: Browse products, manage orders
   - Vendors: Manage inventory (if approved)
   - Admins: System settings, approvals

## API Endpoints (AJAX)
- `GET /accounts/api/verify-gstin/?gstin=<15-chars>`
  - Returns: `{valid: bool, company_name: str, message: str}`
  - Used for real-time GSTIN validation during signup

## Current Technology Stack
- **Framework**: Django 6.0.1 (or 5.1.5)
- **Database**: SQLite (dev), ready for PostgreSQL/MySQL
- **ORM**: Django ORM (no raw SQL)
- **Templates**: Django Templates (server-side)
- **Styling**: Custom CSS3 (no Bootstrap/Tailwind)
- **JavaScript**: Vanilla JS (no jQuery/libraries)
- **Frontend**: Clean, professional ERP UI

## URL Structure
```
/ → Login page (redirect)
/admin/ → Django admin panel
/accounts/login/ → Login form
/accounts/signup/customer/ → Customer registration
/accounts/signup/vendor/ → Vendor registration
/accounts/verify-email/<token>/ → Email verification
/accounts/forgot-password/ → Password reset request
/accounts/reset-password/<token>/ → Password reset form
/accounts/profile/ → Profile editing
/accounts/change-password/ → Password change
/accounts/api/verify-gstin/ → AJAX GSTIN check
/dashboard/ → Role-based dashboard
```

## Development Server
```bash
cd d:\GCETxOdoo
python manage.py runserver
# Access: http://127.0.0.1:8000/

# Admin access:
# Email: admin@rentalerp.com
# Password: admin123
```

## Remaining Phases (5-11)
- **Phase 5**: Quotation & Order Management (views, state machine)
- **Phase 6**: Inventory & Reservation (product browsing, availability)
- **Phase 7**: Invoicing & Payment (GST, Razorpay, late fees)
- **Phase 8**: Vendor Approval Workflow (admin actions, notifications)
- **Phase 9**: Reports & Dashboards (analytics, PDF export)
- **Phase 10**: Security & Validation (input validation, rate limiting)
- **Phase 11**: Hackathon Demo (demo data, walkthrough, presentation)

## Quick Tips for Continuation
1. **Adding new views**: Update app/urls.py, create template, inherit from base.html
2. **Database changes**: Edit models.py → `makemigrations` → `migrate`
3. **Admin improvements**: Edit app/admin.py (no restart needed)
4. **Template changes**: Refresh browser (auto-reloading in dev server)
5. **Static files**: Add to static/ folder, use `{% static 'file.css' %}` in templates
6. **Audit logging**: Use `AuditLog.log_action(user=..., action_type=..., ...)`
7. **Config values**: Get from `SystemConfiguration.get_config()`
