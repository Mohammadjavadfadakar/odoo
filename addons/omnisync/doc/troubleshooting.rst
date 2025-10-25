Troubleshooting & FAQs
======================

Common Issues
-------------

Jobs remain in ``pending`` status
  - Verify that queue workers are running and subscribed to the ``root.omnisync`` channel.
  - Check worker logs for authentication errors or missing Python dependencies.

Frequent validation failures
  - Review validation policy expressions; use the **Preview** button to inspect failing records.
  - Confirm recent mapping changes were approved and promoted correctly.

Health checks reporting false positives
  - Adjust thresholds or request timeouts on the health tab of the system record.
  - Ensure the external system allows the source IP of your Odoo servers.

Webhook calls not triggering flows
  - Confirm the webhook secret matches the sender configuration.
  - Check the webhook log entries under **OmniSync ▸ Monitoring ▸ Webhooks** for error details.

File imports skipping records
  - Validate delimiter settings and column headers in the file connector configuration.
  - Use sandbox mode with a sample file to identify parsing issues.

Debugging Tools
---------------
* **Job Detail View** – Inspect structured logs, payloads, and retry history.
* **Runbook Simulation** – Generate execution plans and highlight missing dependencies.
* **Health Check Logs** – View historical results and export to CSV for analysis.
* **Audit Trail** – Track configuration changes and approvals to correlate with incidents.

Support Workflow
----------------
1. Identify the impacted flow or system using dashboard filters.
2. Review health checks and queue status to isolate infrastructure issues.
3. Examine recent configuration changes (versions, approvals, template applications).
4. Reproduce the problem in sandbox mode before applying fixes to live flows.
5. Communicate status via Discuss alerts or linked activities.

Frequently Asked Questions
--------------------------
* *Can OmniSync handle custom Studio models?* – Yes, select the Studio-created model in mappings and flows.
* *How do I roll back a template application?* – Use the version history on generated records or restore from a previously exported bundle.
* *Can I script OmniSync outside the UI?* – Use the documented JSON-RPC/REST endpoints described in :doc:`reference`.

Next, review :doc:`reference` for endpoint catalogs, record models, and permission matrices.
