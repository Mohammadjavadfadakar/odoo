# External Integration Requirements

## Overview
This document captures the initial requirements for integrating external systems with Odoo.
It is intended to scope data synchronization, mappings, authentication, and operational
constraints for each integration.

## Systems and Integration Goals

### WordPress
**Goal:** Align WordPress user and order data with Odoo CRM and sales workflows.

**Data entities**

| Entity | Required fields | Direction | Frequency |
| --- | --- | --- | --- |
| Users | `ID`, `user_login`, `user_email`, `display_name`, `role`, `registered_at` | WordPress → Odoo | Hourly + on-demand |
| Orders (WooCommerce) | `order_id`, `status`, `customer_id`, `order_date`, `total`, `currency`, `line_items` | WordPress → Odoo | Every 15 min + webhook |
| Products (WooCommerce) | `product_id`, `sku`, `name`, `price`, `tax_status`, `stock_status` | Odoo → WordPress | Hourly |

**Mapping & transformations**
- `res.partner` ↔ WordPress users
  - Odoo `res.partner.email` ↔ WordPress `user_email` (case-insensitive match)
  - Odoo `res.partner.name` ↔ WordPress `display_name` (fallback to `user_login`)
  - Odoo `res.partner.customer_rank` set to `1` when WordPress user has completed order
- WooCommerce order line items map to Odoo `sale.order.line`
  - SKU is authoritative for product matching; if SKU missing, fall back to product name

**Authentication & constraints**
- OAuth 2.0 or Application Passwords (WordPress REST API)
- WooCommerce REST API keys for orders/products
- Webhooks for order status changes; retries must handle 30s timeout

---

### Xero
**Goal:** Sync customers and invoices between Odoo accounting and Xero to keep ledgers aligned.

**Data entities**

| Entity | Required fields | Direction | Frequency |
| --- | --- | --- | --- |
| Contacts | `ContactID`, `Name`, `EmailAddress`, `Phones`, `Addresses`, `IsCustomer` | Odoo ↔ Xero | Every 30 min |
| Invoices | `InvoiceID`, `Type`, `ContactID`, `Date`, `DueDate`, `LineItems`, `Total`, `Status`, `CurrencyCode` | Odoo → Xero | Every 15 min |
| Payments | `PaymentID`, `InvoiceID`, `Amount`, `Date`, `Status` | Xero → Odoo | Every 30 min |

**Mapping & transformations**
- `res.partner` ↔ Xero Contacts
  - Odoo `vat` maps to Xero `TaxNumber`
  - Phone normalization to E.164 for Xero `Phones`
- Odoo `account.move` (out_invoice) ↔ Xero Invoices (ACCREC)
  - Odoo taxes mapped to Xero `TaxType` by configured tax code mapping table

**Authentication & constraints**
- OAuth 2.0 (Xero)
- Tenant selection required per company
- API rate limits: 60 calls/minute; batch requests preferred

---

### QuickBooks Online
**Goal:** Keep accounting data consistent between Odoo and QuickBooks Online (QBO).

**Data entities**

| Entity | Required fields | Direction | Frequency |
| --- | --- | --- | --- |
| Customers | `Id`, `DisplayName`, `PrimaryEmailAddr`, `PrimaryPhone`, `Active` | Odoo ↔ QBO | Every 30 min |
| Items (Products/Services) | `Id`, `Name`, `Sku`, `Type`, `UnitPrice`, `Active` | Odoo → QBO | Hourly |
| Invoices | `Id`, `CustomerRef`, `TxnDate`, `DueDate`, `Line`, `TotalAmt`, `CurrencyRef`, `TxnStatus` | Odoo → QBO | Every 15 min |
| Payments | `Id`, `CustomerRef`, `TotalAmt`, `TxnDate`, `Line` | QBO → Odoo | Every 30 min |

**Mapping & transformations**
- `res.partner` ↔ QBO Customer
  - Odoo `res.partner.name` ↔ QBO `DisplayName`
  - Odoo `phone` normalized to QBO `PrimaryPhone`
- Odoo `product.product` ↔ QBO Item
  - Map Odoo `type` to QBO `Type` (`consu` → `NonInventory`, `service` → `Service`)

**Authentication & constraints**
- OAuth 2.0 (Intuit)
- Refresh token rotation required every 100 days
- Sandbox vs production environment separation

---

## Cross-System Requirements
- **Error handling:** failed syncs logged with entity IDs, payload snapshots, and retry status.
- **Data ownership:** define source of truth per entity to prevent update loops.
- **PII handling:** encrypt access tokens and ensure GDPR-compliant retention policies.

## Stakeholder Review
- **Support stakeholder review status:** Pending confirmation.
- **Requested input:** verify data scope, sync cadence, and support escalation paths.
- **Next step:** schedule review with support lead and update this document with approvals.
