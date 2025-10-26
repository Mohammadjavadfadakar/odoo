Automation, Validation & Runbooks
=================================

Validation Policies
-------------------
Validation policies ensure data quality before records enter Odoo or leave for external systems.

* Define policies under **OmniSync ▸ Governance ▸ Validation Policies**.
* Choose evaluation mode: expression, Python hook (sandboxed), or external call.
* Attach policies to mappings or flows to enforce business rules.
* Inspect validation results via the **Validation Center** dashboard to resolve failures.

Health Checks
-------------
Health check definitions reside on system records and support:

* HTTP/S reachability tests with custom headers.
* Database queries with threshold comparisons.
* File existence checks and queue depth monitoring.

Results feed into dashboards, escalation policies, and runbook pre-checks.

Runbooks
--------
Runbooks orchestrate multiple flows with sequencing, dependencies, and conditional execution.

* Create runbooks under **OmniSync ▸ Automation ▸ Runbooks**.
* Add stages that reference flows or run other runbooks.
* Configure pre-checks (health, validation coverage) and post-actions (notifications, bundle export).
* Execute runbooks manually, via cron, or through API calls.
* Use the **Simulation** feature to preview the execution plan without dispatching jobs.

Escalation Policies
-------------------
Escalation policies automate incident response.

* Define them under **OmniSync ▸ Governance ▸ Escalation Policies**.
* Choose triggers (health failure streaks, validation backlog, job retries).
* Configure actions: pause flow, notify Discuss channel, create activity, call webhook, trigger runbook.
* Attach policies to systems, flows, or runbooks to inherit behavior.

Notifications
-------------
OmniSync integrates with Odoo Discuss and Automation:

* Subscribe administrators and dashboard users to the **OmniSync Alerts** channel.
* Enable email or push notifications for high severity alerts.
* Configure automation actions to post to external services (Slack, Teams, Telegram) using webhooks.

Scripting & API Access
----------------------
Advanced administrators can leverage the JSON-RPC or REST controllers shipped with OmniSync to trigger flows, query job status, or submit payloads. Refer to :doc:`reference` for endpoint details.

Automation Best Practices
-------------------------
* Keep runbooks modular and reusable; avoid duplicating flow logic.
* Combine validation, health, and escalation policies for layered defenses.
* Document runbooks in bundles so operators know the expected outcomes.

Continue to :doc:`troubleshooting` for diagnostic guidance.
