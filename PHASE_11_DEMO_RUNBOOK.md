# Phase 11 Demo Runbook & Checklist

**Date:** January 31, 2026  
**Objective:** Deliver a polished end-to-end demo of the Rental ERP with security & compliance highlights.

---

## ✅ Pre‑Demo Checklist (15–20 minutes)

1. **Migrations & Data**
   - Ensure DB is migrated.
   - Seed demo data with the built‑in command.

2. **Verify Demo Users**
   - Admin: admin@demo.local / Admin@123
   - Vendor: vendor@demo.local / Vendor@123
   - Customer: customer@demo.local / Customer@123

3. **Verify Security Features**
   - 2FA setup works (TOTP QR generation and verification).
   - Rate limiting triggers on repeated login attempts.
   - API keys can be created and revoked.
   - GDPR data access and deletion request pages render.

4. **Confirm UI Pages**
   - Profile page shows 2FA + API key links.
   - GDPR My Data page renders for logged-in user.

---

## 🎯 Live Demo Flow (10–15 minutes)

### 1) Admin Login & System Overview (2 min)
- Login as Admin.
- Briefly show admin dashboard and user roles.
- Emphasize security controls (rate limiting, audit logging, compliance middleware).

### 2) Vendor Workflow (3–4 min)
- Login as Vendor.
- Show product listings and sample products (Camera Equipment, Office Furniture).
- Highlight vendor approval + profile security fields.
- Show API key management page and create a demo API key.

**Key page:** [templates/accounts/api_keys.html](templates/accounts/api_keys.html)

### 3) Customer Workflow (3–4 min)
- Login as Customer.
- Show profile and personal data access (GDPR “My Data”).
- Export data and display consent history.
- Optional: demonstrate request for data deletion.

**Key page:** [templates/accounts/my_data.html](templates/accounts/my_data.html)

### 4) Security & Compliance Highlights (3–4 min)
- Open 2FA setup page and show QR code workflow.
- Demonstrate 2FA verification.
- Show API key rate limiting concept (headers in API responses).
- Show GDPR deletion request page.

**Key pages:**
- [templates/accounts/setup_2fa.html](templates/accounts/setup_2fa.html)
- [templates/accounts/verify_2fa.html](templates/accounts/verify_2fa.html)
- [templates/accounts/request_data_deletion.html](templates/accounts/request_data_deletion.html)

---

## 🎤 5‑Minute Demo Script (Talk Track)

**00:00–00:30 — Intro**
“This is a full Rental ERP built for real‑world compliance. We’ll show secure login, vendor operations, customer GDPR rights, and API access.”

**00:30–01:30 — Admin**
“Admin has full oversight. We enforce rate limiting and audit trails for all critical actions.”

**01:30–02:30 — Vendor**
“Vendors manage products and get approved before publishing. API keys enable integrations securely.”

**02:30–03:30 — Customer + GDPR**
“Customers can view/export personal data and request deletion — GDPR Articles 15, 17, 20.”

**03:30–04:30 — 2FA + Security**
“We add TOTP 2FA with QR setup and backup codes. This prevents account takeover.”

**04:30–05:00 — Wrap**
“This system is audit‑ready, secure by design, and demo‑ready for production use.”

---

## ✅ Demo Validation Checklist

- [ ] Admin login succeeds
- [ ] Vendor login succeeds
- [ ] Customer login succeeds
- [ ] API key creation works
- [ ] API key revocation works
- [ ] 2FA QR code loads
- [ ] 2FA verification succeeds
- [ ] GDPR “My Data” page loads
- [ ] GDPR export triggers download
- [ ] GDPR deletion request submits

---

## 🔐 Security Proof Points (Talking Points)

- **Rate limiting** on authentication endpoints
- **Field-level encryption** for GSTIN, bank details, UPI, etc.
- **2FA (TOTP)** to prevent account takeover
- **API key management** with hashing + usage tracking
- **GDPR compliance**: access, portability, erasure
- **ISO 27001 logging** with audit trail

---

## 🧭 Quick Navigation

- 2FA: /accounts/2fa/setup/
- API Keys: /accounts/api-keys/
- GDPR My Data: /accounts/my-data/
- Deletion Request: /accounts/request-data-deletion/

---

**Status:** Phase 11 Demo Prep complete ✅

---

## ✅ Phase 11 Completion Checklist

- [x] Demo runbook prepared
- [x] Demo data seeding command ready
- [x] Demo user credentials verified
- [x] Security highlights ready (2FA, API keys, GDPR)
- [x] UI pages verified for demo flow
- [x] 5‑minute talk track prepared
