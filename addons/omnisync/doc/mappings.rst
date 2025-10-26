Designing Mappings
==================

Mapping Types
-------------
OmniSync offers **simple** and **advanced** modes:

* *Simple Mode* targets business users with dropdowns, autocomplete suggestions, and example payload previews.
* *Advanced Mode* exposes formula editing, relation resolution, chained transforms, and validation logic.

Creating a Mapping
------------------
1. Go to **OmniSync ▸ Configuration ▸ Mappings** and create a new record.
2. Choose the Odoo model and specify whether the mapping is inbound, outbound, or bidirectional.
3. Define key fields:

   * **Source Path / Expression** – JSONPath, XPath, SQL column, file column, or message key depending on the connector.
   * **Transforms** – Compose operations such as ``trim``, ``upper``, ``type_cast``, ``jalali_to_gregorian``, ``format``, or custom Python snippets (sandboxed).
   * **Default Value** – Provide fallback constants or formula results.
   * **Validation Rules** – Link to validation policies that run before records are written.

4. Flag mapping lines that carry external identifiers to maintain binding records automatically.
5. Use the **Preview** button with sample payloads to validate transformations and relation matching.

Relation Handling
-----------------
* **Many2one** – Configure search domains or specify matching fields (e.g., external SKU, email).
* **Many2many** – Map lists of identifiers, optionally auto-creating related records.
* **One2many** – Use child mapping tables to cascade creations/updates.

Computed Fields & Formulas
--------------------------
* OmniSync uses a whitelisted expression evaluator for formulas. Functions include arithmetic, string manipulation, date conversions, and lookups to declared variables.
* Combine with transforms to chain logic. Example: ``format('%s-%s', upper(trim(source['category'])), source['code'])``.

Validation Integration
----------------------
Mappings can enforce:

* Type checks (e.g., ensure numeric values before casting).
* Domain checks against Odoo models.
* Custom validation policies referencing Python expressions or record rules.

Version Control & Approval
--------------------------
Every mapping change is versioned. Administrators can stage modifications and request approvals before promotion. Use the **Compare Versions** action to inspect differences and roll back if needed.

Testing Strategies
------------------
* Leverage Sandbox mode (see :doc:`flows`) to run dry-runs against historical payloads.
* Maintain unit tests in ``tests/test_mapping_engine.py`` when customizing transforms.

Proceed to :doc:`flows` once your mappings cover the required fields.
