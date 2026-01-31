# Rental Process Workflow Documentation

## Overview
This document outlines the complete rental process flow from customer inquiry to payment and invoice generation.

## Workflow Stages

### Stage 1: Customer Inquiry/Query
**Actor:** Customer
**Action:** 
- Customer browses products on the platform
- Finds desired product with specific variant and quantity
- Submits a rental inquiry/query

**Data Captured:**
- Product ID
- Product Variant (if applicable)
- Quantity needed
- Preferred rental duration
- Pickup/delivery preferences

**Status:** `INQUIRY_PENDING`

---

### Stage 2: Query Sent to Vendor
**Actor:** System
**Action:**
- System routes the inquiry to the product vendor
- Vendor receives notification of new inquiry
- Vendor can view inquiry details

**Data Updated:**
- Inquiry status: `SENT_TO_VENDOR`
- Timestamp of transmission

---

### Stage 3: Vendor Reviews & Responds to Inquiry
**Actor:** Vendor
**Options:**

#### Option A: Vendor Accepts Inquiry
- Reviews customer request
- Confirms product availability
- Checks variant and quantity
- Accepts the inquiry
- Status: `QUOTATION_IN_PROGRESS`

#### Option B: Vendor Rejects Inquiry
- Cannot fulfill the request
- Provides reason for rejection
- Status: `INQUIRY_REJECTED`
- Notification sent to customer

---

### Stage 4: Vendor Creates & Sends Quotation
**Actor:** Vendor
**Action (if accepted):**
- Vendor creates detailed quotation including:
  - Itemized pricing for requested products/variants
  - Rental duration and terms
  - Deposit amount (if required)
  - Late return fees
  - Damage policy
  - Insurance options (if available)
  - Payment terms and due date

**Data Created:**
- Quotation document
- Quotation ID
- Quotation validity period

**Status:** `QUOTATION_SENT`
- Notification sent to customer

---

### Stage 5: Customer Reviews & Responds to Quotation
**Actor:** Customer
**Options:**

#### Option A: Customer Accepts Quotation
- Reviews pricing and terms
- Agrees to rental conditions
- Accepts the quotation
- Status: `RENTAL_ORDER_PENDING_VENDOR_APPROVAL`

#### Option B: Customer Rejects/Negotiates
- Requests modification
- Status: `QUOTATION_NEGOTIATION` OR `QUOTATION_REJECTED`
- Vendor notified for re-negotiation or process ends

---

### Stage 6: Vendor Reviews & Confirms Rental Order
**Actor:** Vendor
**Action (if customer accepted):**
- Vendor receives rental order confirmation request
- Verifies inventory is still available
- Confirms they can fulfill the order

**Options:**

#### Option A: Vendor Confirms Order
- Marks order as confirmed
- Status: `RENTAL_ORDER_CONFIRMED`
- Sets pickup/delivery schedule
- Notification sent to customer with:
  - Confirmation details
  - Pickup/delivery date & time
  - Location details
  - Contact information
  - Final amount due

#### Option B: Vendor Rejects Order
- Inventory issue or other reason
- Status: `RENTAL_ORDER_REJECTED`
- Notification sent to customer
- Process may restart with modified terms

---

### Stage 7: Payment Processing
**Actor:** Customer
**Based on Payment Terms:**
- `Advance Payment`: Full amount due before pickup
- `Partial Advance`: Deposit due now, rest on pickup
- `Payment on Pickup`: Full payment at pickup
- `Post-Rental`: Payment after return

**Actions:**
- Customer initiates payment
- Payment gateway processes transaction
- Payment confirmation received
- Status: `PAYMENT_RECEIVED` or `PAYMENT_PENDING`

---

### Stage 8: Invoice Generation
**Actor:** System
**Action (if payment received):**
- Generate rental invoice including:
  - Invoice number and date
  - Customer details
  - Rental items and quantities
  - Rental period
  - Daily/weekly/monthly rates
  - Total rental cost
  - Taxes (GST)
  - Deposit amount (if applicable)
  - Payment method and amount
  - Payment date
  - Due date for return
  - Cancellation/return policy
  - Vendor details and contact

**Documents Generated:**
- Invoice PDF
- Invoice Email to customer
- Invoice copy for vendor

**Status:** `RENTAL_ACTIVE` or `SCHEDULED_FOR_PICKUP`

---

### Stage 9: Pickup/Delivery & Rental Activation
**Actor:** Vendor/Customer
**Action:**
- Pickup scheduled or delivery arranged
- Physical handover of products
- Condition check and documentation
- Pickup/delivery receipt signed
- Status: `RENTAL_IN_PROGRESS`
- Rental period begins

---

### Stage 10: Rental Period
**During Rental:**
- Customer uses rented products
- Vendor can track rental period
- Automatic reminders for return date
- Status: `RENTAL_IN_PROGRESS`

---

### Stage 11: Return & Invoice Settlement
**Actor:** Customer/Vendor
**Action:**
- Return products as per agreed date
- Condition inspection
- Calculate return fees (if any, for damages/late return)
- Generate return invoice
- Process refund of deposit (if applicable)
- Status: `RENTAL_COMPLETED`

---

## Status Flow Diagram

```
INQUIRY_PENDING
    ↓
SENT_TO_VENDOR
    ↓
    ├─→ INQUIRY_REJECTED (Vendor rejects)
    │
    └─→ QUOTATION_IN_PROGRESS (Vendor accepts)
        ↓
        QUOTATION_SENT
        ↓
        ├─→ QUOTATION_REJECTED (Customer rejects)
        │
        ├─→ QUOTATION_NEGOTIATION (Customer counters)
        │
        └─→ RENTAL_ORDER_PENDING_VENDOR_APPROVAL (Customer accepts)
            ↓
            ├─→ RENTAL_ORDER_REJECTED (Vendor rejects)
            │
            └─→ RENTAL_ORDER_CONFIRMED (Vendor confirms)
                ↓
                PAYMENT_PENDING
                ↓
                ├─→ PAYMENT_RECEIVED
                │   ↓
                │   INVOICE_GENERATED
                │   ↓
                │   SCHEDULED_FOR_PICKUP
                │   ↓
                │   RENTAL_IN_PROGRESS
                │   ↓
                │   RETURN_INITIATED
                │   ↓
                │   RENTAL_COMPLETED
                │   ↓
                │   SETTLED
                │
                └─→ PAYMENT_FAILED (Retry or cancel)
```

---

## Key Entities & Models

### 1. RentalInquiry
- inquiry_id (unique)
- customer_id (FK to User)
- vendor_id (FK to User)
- product_id
- variant_id (optional)
- quantity
- rental_start_date
- rental_end_date
- inquiry_date
- status (INQUIRY_PENDING, SENT_TO_VENDOR, INQUIRY_ACCEPTED, INQUIRY_REJECTED)
- notes

### 2. Quotation
- quotation_id
- inquiry_id (FK)
- vendor_id
- customer_id
- items (product, variant, quantity, unit_price)
- total_amount
- deposit_amount
- payment_terms
- rental_period
- valid_until
- status (QUOTATION_SENT, ACCEPTED, REJECTED, NEGOTIATION)
- created_date
- updated_date

### 3. RentalOrder
- order_id
- quotation_id (FK)
- customer_id
- vendor_id
- status (RENTAL_ORDER_PENDING, RENTAL_ORDER_CONFIRMED, RENTAL_REJECTED)
- rental_start_date
- rental_end_date
- pickup_location
- delivery_location
- pickup_date
- return_date
- total_amount

### 4. Payment
- payment_id
- rental_order_id (FK)
- amount
- payment_method
- payment_date
- status (PENDING, COMPLETED, FAILED, REFUNDED)

### 5. Invoice
- invoice_id
- rental_order_id (FK)
- invoice_date
- amount
- tax
- status
- payment_status

### 6. RentalReturn
- return_id
- rental_order_id (FK)
- return_date
- condition_report
- damages (if any)
- refund_amount
- status (INITIATED, COMPLETED, SETTLED)

---

## API Endpoints Needed

```
POST /api/rentals/inquiry/create/
  Create new rental inquiry

GET /api/rentals/inquiry/<inquiry_id>/
  Get inquiry details

POST /api/rentals/inquiry/<inquiry_id>/accept/
  Vendor accepts inquiry

POST /api/rentals/inquiry/<inquiry_id>/reject/
  Vendor rejects inquiry

POST /api/rentals/quotation/create/
  Vendor creates quotation

POST /api/rentals/quotation/<quotation_id>/accept/
  Customer accepts quotation

POST /api/rentals/quotation/<quotation_id>/reject/
  Customer rejects quotation

POST /api/rentals/order/<order_id>/confirm/
  Vendor confirms rental order

POST /api/rentals/order/<order_id>/reject/
  Vendor rejects rental order

POST /api/rentals/payment/process/
  Process payment

POST /api/rentals/invoice/<order_id>/generate/
  Generate invoice

POST /api/rentals/return/<order_id>/initiate/
  Initiate return process
```

---

## Notifications Required

1. **Customer Notifications:**
   - Inquiry submitted
   - Vendor accepted/rejected inquiry
   - Quotation received
   - Quotation accepted/rejected by vendor
   - Payment reminder
   - Pickup/delivery scheduled
   - Return reminder
   - Refund processed

2. **Vendor Notifications:**
   - New inquiry received
   - Customer accepted/rejected quotation
   - Rental order confirmed
   - Payment received
   - Return initiated
   - Rental period reminder

---

## Business Rules

1. Once quotation expires (valid_until date), it cannot be accepted
2. Vendor can reject order only within 24 hours of order placement
3. Payment must be completed before pickup
4. Late return fees apply after rental_end_date
5. Damage assessment happens during return
6. Refund processed within 7 business days of return acceptance
