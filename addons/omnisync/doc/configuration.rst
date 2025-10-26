Configuring External Systems
============================

Authentication Profiles
-----------------------
Authentication profiles centralize credential management for every connector.

1. Navigate to **OmniSync ▸ Configuration ▸ Authentication Profiles**.
2. Choose the appropriate auth type:

   * **API Key** – supply header or query parameter names and values.
   * **Basic Auth** – store username/password securely; OmniSync encodes the header per request.
   * **OAuth2** – support client credentials and PKCE flows with token refresh tracking.
   * **Custom Sequence** – define ordered steps that call endpoints, extract variables via JSONPath/XPath/regex, and store them for later use.

3. Use the **Test Connection** button to simulate a call with redacted logging.
4. Set rotation reminders and expiry thresholds to receive alerts before secrets lapse.

Systems & Connectors
--------------------
An OmniSync system record represents a remote platform with a connector backend.

*REST Connector*
  - Provide the base URL, default headers, pagination strategy, and rate limit.
  - Configure payload serializers (JSON, XML, form-encoded) and error handlers.

*SOAP Connector*
  - Link the WSDL location, authentication profile, and namespace overrides.
  - Use operation templates to pass complex SOAP bodies with placeholders.

*GraphQL Connector*
  - Store queries or mutations with variables rendered from mappings.
  - Enable introspection caching for schema-aware field suggestions.

*Database Connector*
  - Define DSNs for PostgreSQL or MySQL, optional SSH tunnels, and result paging.
  - Map columns to fields using the mapping engine or SQL views.

*File Connector*
  - Configure FTP/SFTP/local paths, file naming patterns, and delimiters.
  - Optionally enable automatic archive or deletion after processing.

*Webhook Connector*
  - Generates inbound endpoints in ``/omnisync/webhook/<uuid>`` with secret validation.
  - Outbound webhooks can call external URLs with templated bodies when flows fire.

*Queue Connector*
  - Publish or consume messages from RabbitMQ or Kafka topics with JSON schema validation.

Connection Health
-----------------
Each system exposes health checks. Configure them under the **Health** tab to run HTTP pings, SQL validation queries, or file existence probes. Health failures can pause flows or trigger escalations defined in policies.

Variables & Secrets
-------------------
The **Variables** tab lets you declare environment-specific placeholders (e.g., ``{{company_code}}``) reused in mappings or flows. Secrets are AES-encrypted at rest; only administrators can reveal them after an explicit confirmation.

Template Packs
--------------
OmniSync ships starter templates for WordPress, Hesabfa, and Mahak.

1. Open **OmniSync ▸ Templates ▸ Packs** and review the descriptions.
2. Use **Apply Template** to create systems, flows, mappings, and runbooks tailored for the target platform.
3. Adjust company assignments, endpoints, and credentials to match your environment.

Configuration Export/Import
---------------------------
* Export configurations using the **Export Bundle** wizard available on systems and runbooks. The generated JSON/YAML excludes secrets but includes placeholders.
* Import bundles into another database via **Apply Bundle**, review the diff, and confirm creation. Version metadata ensures compatibility and prevents accidental downgrades.

Continue with :doc:`mappings` to learn how to transform data between remote payloads and Odoo models.
