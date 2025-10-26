Reference Guide
===============

REST & JSON-RPC Endpoints
-------------------------
OmniSync exposes a minimal API surface so administrators can trigger operations programmatically.

* ``POST /omnisync/api/run_flow`` – Dispatches a flow by external identifier. Requires ``flow_xmlid`` and optional payload overrides.
* ``POST /omnisync/api/run_runbook`` – Launches a runbook; supports ``simulate`` flag for dry-runs.
* ``GET /omnisync/api/job/<uuid>`` – Returns job status, log summary, and binding identifiers.
* All endpoints require API keys linked to authentication profiles with the ``allow_api_control`` flag.

Security Roles
--------------
* **OmniSync Administrator** – Full create/write access to all OmniSync models, ability to reveal secrets and approve promotions.
* **OmniSync Dashboard User** – Read access to dashboards, logs, health checks, and ability to retry jobs or acknowledge alerts.
* **Regular Users** – Limited read access to binding status on linked business records.

Data Models
-----------
Key models and their responsibilities:

* ``omnisync.system`` – Connector configuration, credentials, health checks, variables.
* ``omnisync.auth.profile`` – Authentication storage and token lifecycle management.
* ``omnisync.mapping`` / ``omnisync.mapping.line`` – Field mappings, transforms, validation hooks.
* ``omnisync.flow`` – Synchronization flows, triggers, scheduling, sandbox history.
* ``omnisync.runbook`` – Orchestrated flow collections with stages and dependencies.
* ``omnisync.validation.policy`` – Validation definitions and evaluation results.
* ``omnisync.job`` – Queue job metadata, payload snapshots, audit references.
* ``omnisync.health.check`` – Connectivity checks and outcomes.
* ``omnisync.binding`` – External identifier registry and linkage metadata.

Record Rules
------------
OmniSync enforces company isolation with record rules:

* Administrators can view all records across their allowed companies.
* Dashboard users see only records tied to companies they follow.
* Webhook processing uses sudoed, company-specific service users to avoid cross-company leakage.

Extensibility Points
--------------------
Developers can extend OmniSync without modifying core files:

* Extend the provided connector classes to support new transports (e.g., proprietary APIs).
* Override mapping transforms by registering new transform functions via the ``omnisync.transform`` registry.
* Use ``with_delay`` hooks or queue job listeners to react to flow events (pre/post execution).
* Provide additional template packs by creating data files under ``data/`` with ``omnisync.template.pack`` records.

Testing
-------
Automated tests live in ``addons/omnisync/tests``:

* ``test_mapping_engine.py`` – Verifies transform chains and validation hooks.
* ``test_health_checks.py`` – Covers health check execution and escalation integration.
* ``test_runbook_orchestration.py`` – Ensures runbook sequencing and simulations behave as expected.

Change Management
-----------------
Follow these practices when deploying changes:

* Use staging databases to test new configurations with sandbox flows and runbook simulations.
* Export bundles as part of release pipelines and store them in version control.
* Update documentation (this folder) alongside configuration changes to keep operators informed.

For how-to guidance, refer back to :doc:`installation`, :doc:`configuration`, and related sections.
