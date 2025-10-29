# Custom Connector Hub Roadmap

## Phase 1: Foundation (Current Sprint)
- [x] Scaffold module structure with models for profiles, endpoints, mappings, and runs.
- [x] Provide security access rules and menu structure.
- [x] Implement configurable request builder and mapping engine utilities.
- [x] Deliver UI forms and dashboard views for configuration and monitoring.
- [x] Add automated tests, including module installation smoke test.

## Phase 2: Connectivity Adapters (Next Sprint)
- [ ] Implement reusable authentication helpers for OAuth2 refresh flow and signed API requests.
- [ ] Add connector-specific Python mixins (e.g., Azure, QuickBooks) with sample endpoints.
- [ ] Support asynchronous job queues for large payload processing.

## Phase 3: Advanced Data Processing (Future)
- [ ] Visual mapping editor leveraging Odoo web assets (OWL components).
- [ ] Data validation rule builder with reusable templates and severity levels.
- [ ] Error triaging dashboard with retry and bulk action capabilities.

## Phase 4: Deployment Tooling (Future)
- [ ] CLI utilities for exporting/importing connector definitions across environments.
- [ ] Preconfigured tests for popular third-party systems.
- [ ] Documentation site with setup guides and API samples.
