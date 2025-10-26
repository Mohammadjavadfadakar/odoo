# OmniSync

OmniSync is a no-code/low-code integration engine for Odoo Enterprise. It enables administrators to configure REST, SOAP, GraphQL, database, file, webhook, and queue integrations, manage authentication profiles, design mapping rules, and schedule bi-directional synchronization jobs without custom development.

## Features

- Configurable REST, SOAP, GraphQL, database, file, webhook, and queue connectors with reusable authentication profiles.
- Mapping engine supporting transforms, formulas, and multi-company aware validations.
- Queue-based job orchestration with logging, KPIs, proactive alerts, validation governance, and conflict tracking.
- Conflict wizard with differential preview and approval-aware version control.
- Binding registry keeps per-record external identifiers for traceability and targeted recovery actions.
- Declarative validation rules with preview-safe evaluation, structured violation logs, and automated escalation policies.
- Automated health checks with historical logs and dashboard surfacing of critical failures.
- Runbook orchestration to bundle flows into reusable execution plans with preview-aware sequencing.
- Sandbox previews and template packs for WordPress, Hesabfa, and Mahak integrations.
- Configuration export wizard producing portable JSON/YAML packages.
- Sandbox mode for safe dry-runs and bilingual (EN/FA) interface scaffolding.

## Installation

1. Install the `queue_job` module from the OCA/queue repository and ensure its workers are running.
2. Add `omnisync` to your Odoo addons path and update the apps list.
3. Install OmniSync from the Apps menu (Developer mode required).

## Usage

1. Create authentication profiles describing how to authenticate against external platforms.
2. Define integration systems referencing the connectors and authentication profiles.
3. Configure flows (inbound/outbound), attach mappings, and schedule synchronization.
4. Configure health checks and runbooks to continuously supervise integrations and bundle operational tasks.
5. Monitor activity through the OmniSync dashboard, job logs, validation center, conflict center, and approval queues.
6. Export configurations to share setups across environments via the export wizard.

## Documentation

Comprehensive end-user and operator documentation is available under [`doc/`](doc/index.rst). The guide covers installation, configuration, mapping design, flow orchestration, monitoring, automation, templates, troubleshooting, and API references for programmatic control.

## Security

Sensitive credentials are encrypted using Odoo's secret storage and masked in the UI. Multi-company access rules are enforced automatically for all OmniSync records.
