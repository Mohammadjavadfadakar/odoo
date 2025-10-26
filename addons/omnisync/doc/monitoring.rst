Monitoring & Observability
==========================

Dashboard Overview
------------------
The OmniSync dashboard provides live KPIs and actionable insights:

* **Job Metrics** – Successful vs failed jobs, average duration, throughput trends.
* **Binding Health** – Count of records awaiting conflict resolution or manual review.
* **Validation Coverage** – Percentage of flows protected by validation rules.
* **Activity Feed** – Timeline of recent sync operations with links to related records.

Filtering & Actions
-------------------
* Filter by company, system, flow, connector type, or status.
* Use quick actions to retry jobs, open diff wizards, launch sandbox runs, or mute alerts.
* Dashboard users can access the view in read-only mode; administrators see additional configuration shortcuts.

Logs & Payloads
---------------
* Job records include structured logs, status codes, request/response excerpts, and redacted payload snapshots.
* Sensitive values (tokens, passwords) remain masked by default. Administrators can reveal them temporarily when troubleshooting.
* Export logs as JSON or CSV for offline auditing.

Health Checks
-------------
* Configure health checks per system (HTTP ping, SQL query, file probe, queue depth).
* Schedule checks to run via cron; results feed into the dashboard widgets.
* Automatic actions can pause flows or notify stakeholders when repeated failures occur.

Alerts & Notifications
----------------------
* OmniSync posts Discuss messages to the **OmniSync Alerts** channel when thresholds are breached.
* Optional automation hooks can forward alerts via email, webhook, or Telegram using Odoo Automations.
* Escalation policies define how many failures trigger each escalation tier.

Queue Oversight
---------------
* Monitor queue load, active workers, and retry counts under **OmniSync ▸ Monitoring ▸ Queue**.
* Identify bottlenecks early and adjust worker concurrency or job chunk sizes.

Audit Trail
-----------
* Every critical action (flow activation, approval, template application, secret reveal) is logged with user, timestamp, and context.
* Use the audit log views to demonstrate compliance and trace configuration changes.

Continue to :doc:`templates` for accelerator packs and reusable configurations.
