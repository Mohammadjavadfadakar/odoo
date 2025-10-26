Managing Synchronization Flows
==============================

Flow Types
----------
* **Inbound (Pull)** – Fetch records from external systems into Odoo models.
* **Outbound (Push)** – Send Odoo records to remote targets.
* **Bidirectional** – Combine inbound and outbound definitions with shared bindings.

Creating a Flow
---------------
1. Open **OmniSync ▸ Configuration ▸ Flows** and create a new flow.
2. Select the system, direction, and target Odoo model.
3. Attach the relevant mapping(s) and choose the orchestrator (batch, incremental, real-time).
4. Configure triggers:

   * **Scheduled** – Cron intervals, delta field, checkpoint keys.
   * **Event-driven** – Record rules (create/update/delete) with queue job creation.
   * **Manual** – Display "Sync Now" button for on-demand runs.

5. Tune concurrency, batch size, retry policy, and rate limits per flow.
6. Enable **Sandbox Mode** for dry-runs before promotion.

Sandbox & Preview
-----------------
* Launch **Preview Run** to process sample payloads without writing to Odoo.
* Inspect the generated diff summary, binding impact, and validation results.
* Approve or reject the sandbox execution; approvals are logged in the audit trail.

Conflict Resolution
-------------------
* OmniSync captures record diffs when both Odoo and the remote system change the same record.
* Use the **Conflict Resolution** wizard to review side-by-side comparisons and choose "Odoo wins" or "Remote wins".
* Resolved conflicts update bindings and optionally notify stakeholders.

Runbooks
--------
* Group flows into runbooks for orchestrated execution. Runbooks can run sequentially or in parallel waves.
* Attach pre-checks (health, validation coverage) and post-checks (record counts, alerting).
* Trigger runbooks manually or via cron to align with business schedules.

Escalation Policies
-------------------
* Define thresholds for consecutive failures or SLA breaches.
* Select automated responses: pause flow, send Discuss alerts, create activities, or call external webhooks.
* Policies integrate with health checks so repeated outages escalate quickly.

Delta & Idempotency
-------------------
* Configure checkpoints (timestamp, incremental ID, cursor token) to avoid reprocessing data.
* Use idempotency keys (usually external IDs) to ensure retries do not duplicate records.
* When consuming message queues, rely on acknowledgement hooks to mark messages processed.

Promotion Workflow
------------------
* Flow versions can be promoted after review. Request approval, collect reviewer notes, and record sign-off.
* Failed approval attempts retain sandbox history for auditing.

Next, explore :doc:`monitoring` to keep flows healthy after deployment.
