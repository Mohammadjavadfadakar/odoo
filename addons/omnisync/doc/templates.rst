Template Packs & Bundles
========================

Overview
--------
Template packs provide reusable integration blueprints. Applying a pack creates systems, mappings, flows, runbooks, and policies tailored to specific platforms.

Available Packs
---------------
* **WordPress Commerce** – Synchronizes WooCommerce products, categories, customers, and orders.
* **Hesabfa Accounting** – Integrates contacts, invoices, and payments with Hesabfa endpoints.
* **Mahak Retail** – Exchanges inventory, customers, and sales documents with Mahak.

Applying a Template Pack
------------------------
1. Navigate to **OmniSync ▸ Templates ▸ Packs**.
2. Select a pack and click **Apply**.
3. Choose the target company and review the configuration summary.
4. Confirm to instantiate the template. OmniSync generates draft records so you can adjust before activation.

Customizing Pack Outputs
------------------------
* Update endpoints, credentials, and company assignments immediately after creation.
* Review generated mappings and tailor transforms to your data conventions.
* Adjust flow schedules and escalation policies to align with your operating hours.

Bundle Export/Import
--------------------
Use bundles to move configurations between environments (e.g., staging → production).

* **Export** – From the system or runbook form view, click **Export Bundle**. Choose JSON or YAML and optionally sign the artifact.
* **Import** – Open **OmniSync ▸ Templates ▸ Bundles** and load the file. OmniSync displays a diff showing new, updated, or skipped records.
* **Secrets** – Bundles use placeholders instead of real secrets. Update the corresponding authentication profiles post-import.

Version Metadata
----------------
Each template and bundle stores version metadata (module version, pack revision, checksum). During import OmniSync verifies compatibility to prevent applying outdated artifacts.

Best Practices
--------------
* Maintain a library of organization-specific bundles in version control.
* Include runbook documentation (see :doc:`automation`) with each bundle to explain execution order.
* Use the approval workflow before promoting templates to production environments.

Continue with :doc:`automation` to orchestrate validations, runbooks, and escalations.
