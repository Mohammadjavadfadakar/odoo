Installation & Initial Setup
============================

Requirements
------------
* Odoo 18 Enterprise with the ``queue_job`` module installed (available from the `OCA/queue <https://github.com/OCA/queue>`_ repository).
* Python dependencies listed in ``requirements.txt`` for queue workers and OAuth flows.
* Access to outbound network services so connectors can reach external platforms.

Installing the Module
---------------------
1. Deploy OmniSync to your Odoo addons path (for packaged Enterprise deployments this usually means cloning the repository into ``addons/``).
2. Update the addons list from the Apps menu in Odoo and locate **OmniSync**.
3. Install the module. OmniSync automatically provisions the **OmniSync Administrator** and **OmniSync Dashboard User** security roles and seeds starter data for connectors, templates, KPIs, and scheduled actions.

Post-Installation Checklist
----------------------------
* Review the OmniSync settings menu under **OmniSync ▸ Configuration** to verify company defaults, time zones, and dashboard refresh intervals.
* Activate the planned queue workers and confirm they process the ``queue.job`` channel used by OmniSync.
* Ensure the automated cron jobs (health checks, runbook maintenance, flow schedulers) are enabled and running with appropriate intervals.
* Create Discuss channels or mailing lists for alerts if you plan to use proactive notifications.

Multi-Company Considerations
----------------------------
OmniSync is multi-company aware. All records (systems, flows, mappings, runbooks, validations) include company fields and respect company-specific security rules.

* Grant administrators access to the relevant companies before they configure integrations.
* Use the company switcher when configuring systems or viewing dashboards to avoid mixing configurations across legal entities.

Queue Worker Configuration
--------------------------
OmniSync relies on asynchronous job processing. Recommended settings:

* Run at least one dedicated worker per company or per heavy integration.
* Configure workers with ``--max-cron-threads=1`` to prevent overlapping cron executions for the same flow.
* Monitor the queue dashboard (OmniSync ▸ Monitoring ▸ Queue) for bottlenecks and adjust concurrency or retry policies accordingly.

Security Hardening
------------------
* Set a master password for the Odoo database so AES-encrypted secrets remain protected.
* Restrict OmniSync Administrator access to trusted staff; they can view and rotate secrets.
* Audit the ``ir.model.access`` records delivered with the module if you maintain custom company groups.
* Enable system logging to capture queue job telemetry and rest endpoints for compliance.

Next Steps
----------
Proceed to :doc:`configuration` to define authentication profiles, connectors, and external systems.
