=======================
Custom Connector Hub
=======================

Overview
========
The Custom Connector Hub provides a configurable framework for integrating
third-party platforms with Odoo 18.0. It delivers:

* Connector profiles with flexible authentication payloads and reusable headers.
* Endpoint definitions supporting multiple HTTP methods and pagination schemes.
* Declarative mapping rules to translate payload fields into Odoo model values.
* Execution logs and dashboards to monitor synchronization health.

Usage Highlights
================
1. Create a *Connector Profile* describing the remote system and base headers.
2. Configure one or more *Endpoints* that define routes, parameters, and
   pagination behavior.
3. Add *Mappings* to transform inbound or outbound payloads into Odoo fields
   with optional default values and transforms.
4. Launch synchronizations (via custom code or scheduled jobs) and monitor
   their results in the dashboard.

Testing
=======
The module ships with automated tests that validate the request builder,
mapping engine, and command-line installation command. Execute the Odoo test
suite with:

.. code-block:: bash

   python3 odoo-bin -d <database> --test-tags custom_connector_hub
