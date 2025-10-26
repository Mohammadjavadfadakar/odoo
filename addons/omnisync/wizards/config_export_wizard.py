# -*- coding: utf-8 -*-
"""Configuration export wizard."""

import base64
import json

from odoo import _, fields, models


class OmniSyncConfigExportWizard(models.TransientModel):
    """Wizard allowing administrators to export OmniSync configuration."""

    _name = "omnisync.config.export.wizard"
    _description = "OmniSync Config Export Wizard"

    flow_ids = fields.Many2many("omnisync.flow", string="Flows")
    export_format = fields.Selection(
        [("json", "JSON"), ("yaml", "YAML")],
        default="json",
        required=True,
    )
    data_file = fields.Binary(readonly=True)
    filename = fields.Char(readonly=True)

    def action_export(self):
        flows = self.flow_ids or self.env["omnisync.flow"].search([])
        payload = {
            "meta": {
                "version": "1.0",
                "exported_by": self.env.user.name,
            },
            "flows": [flow.export_configuration() for flow in flows],
            "systems": [flow.system_id.export_configuration() for flow in flows],
        }
        if self.export_format == "json":
            data = json.dumps(payload, indent=2).encode()
            filename = "omnisync_config.json"
        else:
            try:
                import yaml
            except Exception as exc:  # noqa: BLE001
                raise ValueError("PyYAML is required for YAML export") from exc
            data = yaml.safe_dump(payload).encode()
            filename = "omnisync_config.yaml"
        self.write(
            {
                "data_file": base64.b64encode(data),
                "filename": filename,
            }
        )
        action = {
            "type": "ir.actions.act_window",
            "res_model": "omnisync.config.export.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
        return action
