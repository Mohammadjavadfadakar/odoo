# -*- coding: utf-8 -*-
"""Template apply wizard."""

import json

from odoo import _, fields, models


class OmniSyncTemplateApplyWizard(models.TransientModel):
    """Wizard that applies template packs to the current company."""

    _name = "omnisync.template.apply.wizard"
    _description = "OmniSync Template Apply"

    template_id = fields.Many2one("omnisync.template.pack", required=True)
    dry_run = fields.Boolean(default=True)
    result_message = fields.Text(readonly=True)

    def action_apply(self):
        """Apply the template creating systems and flows."""
        self.ensure_one()
        template = self.template_id
        payload = template.payload or "{}"
        try:
            data = json.loads(payload)
        except ValueError:
            try:
                import yaml  # type: ignore  # noqa: WPS433
            except ImportError as exc:  # noqa: BLE001
                raise ValueError("PyYAML is required to load this template") from exc
            data = yaml.safe_load(payload) or {}
        systems_map = {}
        created = {"systems": 0, "flows": 0}
        if not self.dry_run:
            for system_conf in data.get("systems", []):
                vals = {
                    "name": system_conf.get("name"),
                    "connector_type": system_conf.get("connector_type", "rest"),
                    "base_url": system_conf.get("base_url"),
                    "company_id": self.env.company.id,
                    "file_backend": system_conf.get("file_backend", "local"),
                    "file_base_path": system_conf.get("file_base_path"),
                    "graphql_default_query": system_conf.get("graphql_query"),
                    "queue_topic_prefix": system_conf.get("queue_topic"),
                }
                system = self.env["omnisync.system"].create(vals)
                systems_map[system_conf.get("key", system.name)] = system
                created["systems"] += 1
            for flow_conf in data.get("flows", []):
                system_key = flow_conf.get("system_key")
                system = systems_map.get(system_key)
                if not system:
                    continue
                model = self.env["ir.model"].search([("model", "=", flow_conf.get("model"))], limit=1)
                if not model:
                    continue
                flow_vals = {
                    "name": flow_conf.get("name"),
                    "direction": flow_conf.get("direction", "inbound"),
                    "system_id": system.id,
                    "model_id": model.id,
                    "company_id": self.env.company.id,
                    "inbound_endpoint": flow_conf.get("endpoints", {}).get("inbound"),
                    "outbound_endpoint": flow_conf.get("endpoints", {}).get("outbound"),
                }
                if flow_conf.get("queue_topic"):
                    flow_vals["queue_topic"] = flow_conf.get("queue_topic")
                if flow_conf.get("file_inbound_path"):
                    flow_vals["file_inbound_path"] = flow_conf.get("file_inbound_path")
                if flow_conf.get("file_outbound_path"):
                    flow_vals["file_outbound_path"] = flow_conf.get("file_outbound_path")
                flow = self.env["omnisync.flow"].create(flow_vals)
                created["flows"] += 1
        message = _(
            "Template %(template)s processed. Systems: %(systems)s, flows: %(flows)s (dry_run=%(dry)s)"
        ) % {
            "template": template.name,
            "systems": created["systems"],
            "flows": created["flows"],
            "dry": self.dry_run,
        }
        self.result_message = message
        return {
            "type": "ir.actions.act_window",
            "res_model": "omnisync.template.apply.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
