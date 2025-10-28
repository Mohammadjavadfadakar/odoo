=====================
Advanced operator help
=====================

The following guide complements the in-application tooltips and alerts with
step-by-step advice for configuring and maintaining OmniSync.

Systems
=======

* Navigate to :menuselection:`OmniSync --> Configuration --> Systems` and open
  the target integration.
* Provide a descriptive **Name**, select the appropriate **Connector Type**, and
  link an **Auth Profile** so credentials are applied automatically.
* Populate the **Connector Settings** tab with connector-specific options such
  as database parameters or queue topics.
* Use the :guilabel:`Test Connection` button after every change to verify the
  remote platform can be reached.

Flows
=====

* Go to :menuselection:`OmniSync --> Operations --> Flows` and create or edit a
  record.
* Select the **System** that should execute the connector logic and the **Odoo
  Model** that receives data.
* Define scheduling with **Schedule Mode** (manual, scheduled, or event driven)
  and optionally link a cron for recurring runs.
* Configure inbound/outbound endpoints, payload templates, and delta fields in
  the dedicated notebook tabs.
* Generate a :guilabel:`Preview` to collect sample payloads before submitting
  the flow for approval.

Mappings and lines
==================

* From :menuselection:`OmniSync --> Configuration --> Mappings` align external
  payload structures with Odoo fields.
* The **Lines** tab lets you specify individual field mappings, default values,
  transform chains, and whether a line represents the external identifier.
* Access :menuselection:`OmniSync --> Configuration --> Advanced Records -->
  Mapping Lines` for a consolidated view of all lines across flows. Use the
  form view to document complex formulas and relation resolution strategies.

Bindings
========

* Open :menuselection:`OmniSync --> Operations --> Bindings` to review how
  Odoo records relate to external identifiers.
* Use :guilabel:`Open Record` to jump to the affected record when diagnosing
  synchronization problems.
* The **Payload Snapshot** field retains the raw data that produced the binding,
  making it easier to replay issues.

Runbooks and lines
==================

* Manage orchestration playbooks in :menuselection:`OmniSync --> Configuration
  --> Runbooks`.
* Each runbook line queues a specific flow and can toggle preview mode for dry
  runs. Use :menuselection:`OmniSync --> Configuration --> Advanced Records -->
  Runbook Lines` for a global list of steps.
* Configure the :guilabel:`Notify User` to alert operators when execution fails.

Health checks and logs
======================

* Configure automated supervision in :menuselection:`OmniSync -->
  Configuration --> Health Checks`.
* Choose a **Check Type** to verify connector reachability, execute flow
  previews, or inspect mapping coverage.
* Use :menuselection:`OmniSync --> Configuration --> Advanced Records -->
  Health Logs` to audit historic executions and refine thresholds.

Validation rules and logs
=========================

* Validation rules live under :menuselection:`OmniSync --> Configuration -->
  Validation Rules`. Author Python expressions that return truthy values when
  the payload is acceptable.
* The :menuselection:`OmniSync --> Operations --> Validation Logs` menu surfaces
  violations. Inspect the payload snapshot and mark entries as handled after
  remediation.

Conflicts
=========

* Review detected conflicts in :menuselection:`OmniSync --> Operations -->
  Conflicts`.
* Compare the differences between remote payloads and Odoo, then use the
  resolution wizard to apply the correct outcome (remote wins, Odoo wins, or
  dismiss).
