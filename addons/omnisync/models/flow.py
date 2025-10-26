# -*- coding: utf-8 -*-
"""Synchronization flow definitions."""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..tools import DEFAULT_QUEUE_CHANNEL, QueueJobMixin
from .system import ConnectorResponse

_logger = logging.getLogger(__name__)


class OmniSyncFlow(models.Model, QueueJobMixin):
    """Represents a synchronization flow between Odoo and an external system."""

    _name = "omnisync.flow"
    _description = "OmniSync Flow"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    system_id = fields.Many2one("omnisync.system", required=True)
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound")],
        default="inbound",
        required=True,
    )
    model_id = fields.Many2one("ir.model", required=True)
    mapping_ids = fields.One2many("omnisync.mapping", "flow_id")
    validation_rule_ids = fields.One2many(
        "omnisync.validation.rule",
        "flow_id",
        string="Validation Rules",
    )
    escalation_policy_ids = fields.One2many(
        "omnisync.escalation.policy",
        "flow_id",
        string="Escalation Policies",
    )
    schedule_mode = fields.Selection(
        [
            ("manual", "Manual"),
            ("scheduled", "Scheduled"),
            ("event", "Event Driven"),
        ],
        default="manual",
    )
    cron_id = fields.Many2one("ir.cron")
    inbound_endpoint = fields.Char(help="Endpoint for inbound operations")
    outbound_endpoint = fields.Char(help="Endpoint for outbound operations")
    payload_template = fields.Text(
        help="Optional JSON template applied when pushing data to external systems."
    )
    last_run = fields.Datetime(readonly=True)
    last_status = fields.Selection(
        [("idle", "Idle"), ("success", "Success"), ("failed", "Failed")],
        default="idle",
    )
    queue_channel = fields.Char(default=DEFAULT_QUEUE_CHANNEL)
    sandbox_mode = fields.Boolean(
        related="system_id.sandbox_mode",
        readonly=True,
    )
    description = fields.Text()
    delta_field = fields.Char(
        help="Field name used for delta synchronization."
    )
    graphql_query = fields.Text(
        string="GraphQL Query",
        help="Query executed for GraphQL connectors when inbound data is fetched.",
    )
    graphql_variables = fields.Text(
        string="GraphQL Variables",
        help="JSON encoded variables passed to the GraphQL query.",
    )
    db_inbound_query = fields.Text(
        string="Inbound SQL",
        help="SQL query executed when pulling data from a database connector.",
    )
    db_outbound_query = fields.Text(
        string="Outbound SQL",
        help="SQL statement executed when exporting records to a database connector.",
    )
    file_inbound_path = fields.Char(
        string="Inbound Path",
        help="Relative path used for inbound file synchronization.",
    )
    file_outbound_path = fields.Char(
        string="Outbound Path",
        help="Relative path used for outbound file synchronization.",
    )
    webhook_event_code = fields.Char(
        string="Webhook Event",
        help="Event identifier used when consuming webhook payloads.",
    )
    queue_topic = fields.Char(
        string="Queue Topic",
        help="Topic or routing key used for queue connectors.",
    )
    sandbox_preview_data = fields.Json(
        string="Last Preview",
        readonly=True,
        copy=False,
        help="Stores the most recent sandbox preview payload.",
    )
    last_preview_at = fields.Datetime(readonly=True, copy=False)
    approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("awaiting", "Awaiting Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
    )
    version_ids = fields.One2many("omnisync.flow.version", "flow_id", string="Versions")
    current_version_id = fields.Many2one(
        "omnisync.flow.version",
        string="Active Version",
        readonly=True,
    )
    failure_threshold = fields.Integer(
        string="Failure Threshold",
        default=3,
        help="Number of consecutive failures before alerts are triggered.",
    )
    consecutive_failures = fields.Integer(readonly=True, default=0)
    validation_failure_streak = fields.Integer(
        string="Validation Failure Streak",
        readonly=True,
        default=0,
    )
    alert_partner_ids = fields.Many2many(
        "res.partner",
        string="Alert Recipients",
        domain=[("share", "=", False)],
        help="Partners notified when the failure threshold is exceeded.",
    )
    pending_conflict_count = fields.Integer(
        string="Pending Conflicts",
        compute="_compute_conflict_metrics",
    )

    @api.onchange("system_id")
    def _onchange_system_id(self):
        if self.system_id:
            self.company_id = self.system_id.company_id

    def _compute_conflict_metrics(self):
        """Compute the number of pending conflicts linked to the flow."""
        if not self.ids:
            for flow in self:
                flow.pending_conflict_count = 0
            return
        grouped = self.env["omnisync.conflict"].read_group(
            [("flow_id", "in", self.ids), ("state", "=", "pending")],
            ["flow_id"],
            ["flow_id"],
        )
        counts = {item["flow_id"][0]: item["flow_id_count"] for item in grouped}
        for flow in self:
            flow.pending_conflict_count = counts.get(flow.id, 0)

    def action_sync_now(self):
        """Queue an immediate synchronization job."""
        for flow in self:
            flow.with_delay(
                channel=flow.queue_channel or DEFAULT_QUEUE_CHANNEL
            )._execute_sync()
        return True

    def _execute_sync(self, checkpoint: Dict[str, Any] | None = None):
        """Queue job that runs the synchronization."""
        self.ensure_one()
        job_log = self.env["omnisync.job.log"].create(
            {
                "flow_id": self.id,
                "status": "pending",
                "company_id": self.company_id.id,
            }
        )
        start = time.time()
        processed = 0
        preview_mode = bool(self.sandbox_mode or self.env.context.get("omnisync_preview"))
        preview_collector: List[Dict[str, Any]] = []
        try:
            if self.direction == "inbound":
                processed = self._run_inbound_sync(
                    checkpoint=checkpoint or {},
                    collector=preview_collector,
                )
            else:
                processed = self._run_outbound_sync(
                    checkpoint=checkpoint or {},
                    collector=preview_collector,
                )
            self.last_status = "success"
            self.consecutive_failures = 0
            job_log.mark_success(
                {
                    "duration": time.time() - start,
                    "latency": 0.0,
                    "records_processed": processed,
                }
            )
            if preview_mode:
                self.write(
                    {
                        "sandbox_preview_data": preview_collector,
                        "last_preview_at": fields.Datetime.now(),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            _logger.exception("Flow %s failed: %s", self.name, exc)
            self.last_status = "failed"
            job_log.mark_failure(str(exc))
            self._handle_failure_alert(job_log)
            raise
        finally:
            self.last_run = fields.Datetime.now()

    def _run_inbound_sync(
        self,
        checkpoint: Dict[str, Any],
        collector: List[Dict[str, Any]] | None = None,
    ):
        """Handle inbound synchronization."""
        endpoint = self.inbound_endpoint or ""
        params = self._build_inbound_params(checkpoint)
        response = self._execute_inbound_connector(endpoint, params)
        records = self._normalize_payload(response)
        processed = 0
        for record in records:
            mapped_values, per_mapping = self._apply_mappings(record)
            if not self._enforce_validation_rules("inbound", record, mapped_values):
                continue
            if collector is not None:
                collector.append({"source": record, "mapped": mapped_values})
            identifier = self._extract_identifier(record, mapped_values, per_mapping)
            if self.sandbox_mode or self.env.context.get("omnisync_preview"):
                _logger.info(
                    "Sandbox mode active for flow %s. Simulated write: %s",
                    self.name,
                    mapped_values,
                )
                continue
            target_record, conflict_detected = self._write_inbound_record(mapped_values, record)
            if target_record and identifier:
                state = "pending" if conflict_detected else "synced"
                self._update_binding(
                    target_record,
                    identifier,
                    direction="inbound",
                    source_payload=record,
                    mapped_values=mapped_values,
                    state=state,
                )
            if not conflict_detected:
                processed += 1
        return processed

    def _run_outbound_sync(
        self,
        checkpoint: Dict[str, Any],
        collector: List[Dict[str, Any]] | None = None,
    ):
        """Handle outbound synchronization by exporting records to external system."""
        model = self.env[self.model_id.model]
        domain = self._build_outbound_domain(checkpoint)
        records = model.search(domain, limit=100)
        payload_template = {}
        if self.payload_template:
            try:
                payload_template = json.loads(self.payload_template)
            except ValueError:
                payload_template = {}
        processed = 0
        outbound_payloads: List[Dict[str, Any]] = []
        pending_bindings: List[Dict[str, Any]] = []
        preview_mode = bool(self.sandbox_mode or self.env.context.get("omnisync_preview"))
        for record in records:
            payload, mapping_details = self._render_payload_template(record, payload_template)
            identifier = self._extract_identifier(None, payload, mapping_details)
            if not self._enforce_validation_rules("outbound", payload, payload, record=record):
                continue
            if collector is not None:
                collector.append({"record_id": record.id, "payload": payload})
            if preview_mode:
                continue
            if self.system_id.connector_type == "file":
                outbound_payloads.append(payload)
                pending_bindings.append(
                    {
                        "record": record,
                        "identifier": identifier,
                        "payload": payload,
                    }
                )
                continue
            try:
                self._execute_outbound_connector(payload)
            except Exception as exc:  # noqa: BLE001
                if identifier:
                    self._update_binding(
                        record,
                        identifier,
                        direction="outbound",
                        source_payload=payload,
                        mapped_values=payload,
                        state="failed",
                        error_message=str(exc),
                    )
                raise
            else:
                if identifier:
                    self._update_binding(
                        record,
                        identifier,
                        direction="outbound",
                        source_payload=payload,
                        mapped_values=payload,
                    )
                processed += 1
        if (
            not preview_mode
            and collector is None
            and outbound_payloads
            and self.system_id.connector_type == "file"
        ):
            self._execute_outbound_connector(outbound_payloads, bulk=True)
            for entry in pending_bindings:
                identifier = entry.get("identifier")
                record = entry.get("record")
                if identifier and record:
                    self._update_binding(
                        record,
                        identifier,
                        direction="outbound",
                        source_payload=entry.get("payload"),
                        mapped_values=entry.get("payload"),
                    )
                    processed += 1
        return processed

    def _write_inbound_record(self, values: Dict[str, Any], source_payload: Dict[str, Any]):
        model = self.env[self.model_id.model].with_company(self.company_id)
        delta_field = self.delta_field
        domain = []
        if delta_field and values.get(delta_field):
            domain = [(delta_field, "=", values[delta_field])]
        if domain:
            existing = model.search(domain, limit=1)
            if existing:
                conflicts = self._detect_conflicts(existing, values, source_payload)
                if conflicts:
                    self._register_conflict(existing, values, source_payload, conflicts)
                    return existing, True
                existing.write(values)
                return existing, False
        record = model.create(values)
        return record, False

    def _execute_inbound_connector(self, endpoint: str, params: Dict[str, Any]):
        """Execute the inbound request based on the connector type."""
        connector_type = self.system_id.connector_type
        if connector_type == "graphql":
            variables = self._get_graphql_variables()
            if params:
                variables.update(params)
            return self.system_id.execute(
                endpoint=endpoint,
                query=self.graphql_query,
                variables=variables,
            )
        if connector_type == "database":
            query = self.db_inbound_query or endpoint
            if not query:
                raise UserError(
                    _("Inbound SQL query is required for database flow %s") % self.name
                )
            return self.system_id.execute(
                endpoint=query,
                query=query,
                parameters=params,
                operation="read",
            )
        if connector_type == "file":
            path = self.file_inbound_path or endpoint
            return self.system_id.execute(endpoint=path or "", operation="read")
        if connector_type == "webhook":
            return self.system_id.execute(
                endpoint=endpoint or "",
                operation="consume",
                event_code=self.webhook_event_code,
            )
        if connector_type == "queue":
            topic = self.queue_topic or endpoint
            return self.system_id.execute(endpoint=topic or "", operation="consume")
        return self.system_id.execute(endpoint=endpoint, payload=None, params=params)

    def _execute_outbound_connector(self, payload: Any, bulk: bool = False):
        """Dispatch outbound payloads according to the connector."""
        connector_type = self.system_id.connector_type
        if connector_type == "database":
            query = self.db_outbound_query or self.outbound_endpoint
            if not query:
                raise UserError(
                    _("Outbound SQL query is required for database flow %s") % self.name
                )
            rows = payload if bulk and isinstance(payload, list) else [payload]
            for row in rows:
                self.system_id.execute(
                    endpoint=query,
                    query=query,
                    parameters=row,
                    operation="write",
                )
            return
        if connector_type == "file":
            if not bulk:
                return
            path = self.file_outbound_path or self.outbound_endpoint or ""
            self.system_id.execute(
                endpoint=path,
                operation="write",
                payload={"content": payload},
                content=payload,
            )
            return
        if connector_type == "webhook":
            self.system_id.execute(endpoint=self.outbound_endpoint or "", payload=payload)
            return
        if connector_type == "queue":
            topic = self.queue_topic or self.outbound_endpoint or self.system_id.queue_topic_prefix
            self.system_id.execute(
                endpoint=topic or "",
                payload=payload,
                operation="publish",
            )
            return
        if connector_type == "graphql":
            query = payload.get("query") if isinstance(payload, dict) else None
            variables = None
            if isinstance(payload, dict):
                variables = payload.get("variables") or {k: v for k, v in payload.items() if k not in {"query", "variables"}}
            self.system_id.execute(
                endpoint=self.outbound_endpoint or "",
                query=query or self.graphql_query,
                variables=variables or self._get_graphql_variables(),
            )
            return
        method = "POST"
        body = payload
        if isinstance(payload, dict) and payload.get("_method"):
            payload = dict(payload)
            method = payload.pop("_method")
            body = payload
        self.system_id.execute(
            endpoint=self.outbound_endpoint or "",
            payload=body,
            method=method,
        )

    def _normalize_payload(self, response: ConnectorResponse) -> List[Dict[str, Any]]:
        """Normalize any connector response into a list of payload dictionaries."""
        payload = response.data
        if not payload:
            return []
        if isinstance(payload, dict):
            if self.system_id.connector_type == "graphql" and payload.get("data"):
                payload = payload.get("data")
            elif "results" in payload:
                payload = payload["results"]
            elif "data" in payload:
                payload = payload["data"]
        if isinstance(payload, list):
            return payload
        return [payload]

    def _get_graphql_variables(self) -> Dict[str, Any]:
        """Return parsed GraphQL variables from the configuration."""
        if not self.graphql_variables:
            return {}
        try:
            return json.loads(self.graphql_variables)
        except ValueError:
            raise UserError(
                _("GraphQL variables must be valid JSON for flow %s") % self.name
            ) from None

    def _detect_conflicts(
        self,
        record: models.Model,
        new_values: Dict[str, Any],
        source_payload: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """Compare incoming values with existing data to highlight conflicts."""
        diffs: Dict[str, Dict[str, Any]] = {}
        for field_name, new_value in new_values.items():
            if field_name not in record._fields:
                continue
            current_value = record[field_name]
            if isinstance(current_value, models.BaseModel):
                current_value = current_value.id
            if current_value != new_value:
                diffs[field_name] = {
                    "odoo": current_value,
                    "remote": new_value,
                }
        return diffs

    def _register_conflict(
        self,
        record: models.Model,
        values: Dict[str, Any],
        source_payload: Dict[str, Any],
        diffs: Dict[str, Dict[str, Any]],
    ):
        """Create a conflict entry for manual resolution."""
        self.env["omnisync.conflict"].create(
            {
                "flow_id": self.id,
                "model_name": self.model_id.model,
                "record_id": record.id,
                "external_payload": source_payload,
                "candidate_values": values,
                "differences_json": diffs,
            }
        )

    def _handle_failure_alert(self, job_log):
        """Increment failure counters and notify administrators if needed."""
        self.consecutive_failures += 1
        if self.failure_threshold and self.consecutive_failures < self.failure_threshold:
            return
        partners = self.alert_partner_ids
        if not partners:
            admin_group = self.env.ref("omnisync.group_omnisync_admin", raise_if_not_found=False)
            if admin_group:
                partners = admin_group.users.mapped("partner_id")
        if partners:
            body = _(
                "Flow %(flow)s has failed %(count)s times consecutively. Last job: %(job)s"
            ) % {
                "flow": self.name,
                "count": self.consecutive_failures,
                "job": job_log.name,
            }
            self.message_post(body=body, partner_ids=partners.ids)
        self._apply_escalation(
            "job_failure",
            {
                "message": job_log.error_message or body,
                "job": job_log.name,
                "streak": self.consecutive_failures,
            },
        )

    def _enforce_validation_rules(
        self,
        direction: str,
        source_payload: Optional[Dict[str, Any]],
        mapped_values: Optional[Dict[str, Any]],
        record: Optional[models.Model] = None,
    ) -> bool:
        """Return True when the record passes validation rules."""
        preview_mode = bool(self.sandbox_mode or self.env.context.get("omnisync_preview"))
        if not self.validation_rule_ids:
            if not preview_mode and self.validation_failure_streak:
                self.validation_failure_streak = 0
            return True
        blocked = False
        messages: List[str] = []
        for rule in self.validation_rule_ids:
            if not rule.active or not rule.matches_direction(direction):
                continue
            passed, message = rule.evaluate(source_payload, mapped_values, record)
            if passed:
                continue
            messages.append(message)
            if not preview_mode:
                rule.log_violation(
                    flow=self,
                    direction=direction,
                    payload=source_payload,
                    values=mapped_values,
                    record=record,
                    message=message,
                )
            if rule.severity == "error":
                blocked = True
        if blocked:
            if preview_mode:
                _logger.info(
                    "Validation failure detected in preview for flow %s: %s",
                    self.name,
                    "; ".join(messages),
                )
                return False
            self.validation_failure_streak += 1
            context = {
                "message": "; ".join(messages) if messages else _("Validation failed"),
                "payload": source_payload,
                "values": mapped_values,
                "streak": self.validation_failure_streak,
            }
            self._apply_escalation("validation_failure", context)
            return False
        if not preview_mode and self.validation_failure_streak:
            self.validation_failure_streak = 0
        return True

    def _apply_escalation(self, event_type: str, context: Dict[str, Any]):
        """Evaluate escalation policies for the provided event."""
        policies = self.escalation_policy_ids.filtered(lambda p: p.event_type == event_type and p.active)
        if not policies:
            return
        streak = context.get("streak")
        if streak is None:
            if event_type == "validation_failure":
                streak = self.validation_failure_streak
            else:
                streak = self.consecutive_failures
        for policy in policies:
            if not policy.should_trigger(streak=streak):
                continue
            payload = dict(context)
            payload.setdefault("event", event_type)
            payload["streak"] = streak
            policy.execute_policy(self, payload)

    def _apply_mappings(self, payload: Dict[str, Any]):
        """Apply mapping definitions and return aggregated and per-mapping values."""
        values: Dict[str, Any] = {}
        per_mapping: List[Dict[str, Any]] = []
        for mapping in self.mapping_ids:
            mapping_values = mapping.apply(payload)
            per_mapping.append({
                "mapping": mapping,
                "source": payload,
                "values": mapping_values,
            })
            values.update(mapping_values)
        return values, per_mapping

    def _extract_identifier(
        self,
        source_payload: Optional[Dict[str, Any]],
        aggregated_values: Dict[str, Any],
        per_mapping: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[str]:
        """Determine the external identifier based on mapping metadata."""
        mapping_entries = per_mapping or []
        if not mapping_entries:
            mapping_entries = [
                {
                    "mapping": mapping,
                    "source": source_payload or {},
                    "values": aggregated_values,
                }
                for mapping in self.mapping_ids
            ]
        for entry in mapping_entries:
            mapping = entry.get("mapping")
            if not mapping:
                continue
            identifier = mapping.extract_external_identifier(
                entry.get("source") or source_payload or {},
                entry.get("values"),
            )
            if identifier not in (None, ""):
                return str(identifier)
        return None

    def _update_binding(
        self,
        record: models.Model,
        identifier: str,
        *,
        direction: str,
        source_payload: Optional[Dict[str, Any]] = None,
        mapped_values: Optional[Dict[str, Any]] = None,
        state: str = "synced",
        error_message: Optional[str] = None,
    ) -> None:
        """Create or update the binding record for a synchronized item."""
        if not record or not identifier:
            return
        snapshot: Dict[str, Any] = {}
        if source_payload is not None:
            snapshot["source"] = source_payload
        if mapped_values is not None:
            snapshot["mapped"] = mapped_values
        binding_model = self.env["omnisync.binding"].sudo()
        safe_snapshot = self._sanitize_payload_snapshot(snapshot) if snapshot else None
        binding_model.register_binding(
            flow=self,
            record=record,
            identifier=str(identifier),
            direction=direction,
            state=state,
            snapshot=safe_snapshot,
            error_message=error_message,
        )

    def _sanitize_payload_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure payload snapshots are JSON serializable for storage."""
        try:
            return json.loads(json.dumps(snapshot, default=str))
        except TypeError:
            return {"raw": str(snapshot)}

    def _build_inbound_params(self, checkpoint: Dict[str, Any]):
        params = dict(self.system_id.default_params or {})
        if self.delta_field and checkpoint.get("last_sync"):
            params[self.delta_field] = checkpoint["last_sync"]
        return params

    def _build_outbound_domain(self, checkpoint: Dict[str, Any]):
        domain = []
        if self.delta_field and checkpoint.get("last_sync"):
            domain.append((self.delta_field, ">", checkpoint["last_sync"]))
        return domain

    def _render_payload_template(self, record: models.Model, template: Dict[str, Any]):
        payload = json.loads(json.dumps(template)) if template else {}
        per_mapping: List[Dict[str, Any]] = []
        for mapping in self.mapping_ids:
            read_fields = [
                line.source_field
                for line in mapping.line_ids
                if line.source_field and line.source_field not in ("id",)
            ]
            record_payload = {}
            if read_fields:
                data = record.read(read_fields)[0]
                record_payload.update(data)
            record_payload["id"] = record.id
            values = mapping.apply(record_payload)
            per_mapping.append(
                {
                    "mapping": mapping,
                    "source": record_payload,
                    "values": values,
                }
            )
            payload.update(values)
        return payload, per_mapping

    def export_configuration(self) -> Dict[str, Any]:
        self.ensure_one()
        return {
            "name": self.name,
            "direction": self.direction,
            "model": self.model_id.model,
            "schedule_mode": self.schedule_mode,
            "endpoints": {
                "inbound": self.inbound_endpoint,
                "outbound": self.outbound_endpoint,
            },
            "graphql": {
                "query": self.graphql_query,
                "variables": self.graphql_variables,
            },
            "database": {
                "inbound": self.db_inbound_query,
                "outbound": self.db_outbound_query,
            },
            "file": {
                "inbound": self.file_inbound_path,
                "outbound": self.file_outbound_path,
            },
            "queue_topic": self.queue_topic,
            "webhook_event": self.webhook_event_code,
            "failure_threshold": self.failure_threshold,
            "mappings": [mapping.export_configuration() for mapping in self.mapping_ids],
        }

    def action_submit_for_approval(self):
        """Create a new version snapshot and submit it."""
        for flow in self:
            version = flow._create_version_snapshot(name=f"{flow.name} - {datetime.utcnow():%Y%m%d%H%M}")
            version.action_submit()
        return True

    def action_open_version_wizard(self):
        """Open the version promotion wizard."""
        self.ensure_one()
        wizard = self.env["omnisync.version.promote.wizard"].create({"flow_id": self.id})
        return wizard.action_open()

    def action_generate_preview(self):
        """Trigger the sandbox preview wizard for administrators."""
        self.ensure_one()
        wizard = self.env["omnisync.sandbox.preview.wizard"].create({"flow_id": self.id})
        return wizard.action_preview()

    def run_preview(self) -> List[Dict[str, Any]]:
        """Execute the flow in preview mode and return mapped payloads."""
        preview_flow = self.with_context(omnisync_preview=True)
        collector: List[Dict[str, Any]] = []
        if preview_flow.direction == "inbound":
            preview_flow._run_inbound_sync(checkpoint={}, collector=collector)
        else:
            preview_flow._run_outbound_sync(checkpoint={}, collector=collector)
        self.write(
            {
                "sandbox_preview_data": collector,
                "last_preview_at": fields.Datetime.now(),
            }
        )
        return collector

    def _create_version_snapshot(self, name: str):
        """Create a version record containing the current configuration."""
        data = json.dumps(self.export_configuration(), indent=2)
        version = self.env["omnisync.flow.version"].create(
            {
                "name": name,
                "flow_id": self.id,
                "data_blob": data,
                "company_id": self.company_id.id,
            }
        )
        return version

    def _apply_version(self, version):
        """Apply the configuration from a version to the flow."""
        self.ensure_one()
        config = version.get_configuration()
        if not config:
            raise UserError(_("Version %s does not contain configuration data.") % version.name)
        endpoints = config.get("endpoints", {})
        updates = {
            "name": config.get("name", self.name),
            "direction": config.get("direction", self.direction),
            "inbound_endpoint": endpoints.get("inbound"),
            "outbound_endpoint": endpoints.get("outbound"),
            "graphql_query": (config.get("graphql") or {}).get("query"),
            "graphql_variables": (config.get("graphql") or {}).get("variables"),
            "db_inbound_query": (config.get("database") or {}).get("inbound"),
            "db_outbound_query": (config.get("database") or {}).get("outbound"),
            "file_inbound_path": (config.get("file") or {}).get("inbound"),
            "file_outbound_path": (config.get("file") or {}).get("outbound"),
            "queue_topic": config.get("queue_topic"),
            "webhook_event_code": config.get("webhook_event"),
            "failure_threshold": config.get("failure_threshold", self.failure_threshold),
        }
        self.write(updates)
        mappings = config.get("mappings", [])
        if mappings:
            commands = [(5, 0, 0)]
            for mapping_conf in mappings:
                commands.append(self._prepare_mapping_from_config(mapping_conf))
            self.write({"mapping_ids": commands})
        self.current_version_id = version.id

    def _prepare_mapping_from_config(self, mapping_conf: Dict[str, Any]):
        """Build ORM command to recreate a mapping from exported data."""
        model = self.env["ir.model"].search([("model", "=", mapping_conf.get("target_model"))], limit=1)
        if not model:
            raise UserError(
                _("Target model %(model)s was not found during version apply.")
                % {"model": mapping_conf.get("target_model")}
            )
        lines = []
        for line_conf in mapping_conf.get("lines", []):
            lines.append(
                        (
                            0,
                            0,
                            {
                                "source_field": line_conf.get("source_field"),
                                "target_field_name": line_conf.get("target_field_name"),
                                "default_value": line_conf.get("default_value"),
                                "formula": line_conf.get("formula"),
                                "transform_chain": line_conf.get("transforms"),
                                "is_external_identifier": line_conf.get("is_external_identifier", False),
                                "relation_resolution": line_conf.get("relation_resolution", "none"),
                            },
                        )
                    )
        return (
            0,
            0,
            {
                "name": mapping_conf.get("name"),
                "mode": mapping_conf.get("mode", "simple"),
                "target_model_id": model.id,
                "line_ids": lines,
            },
        )
