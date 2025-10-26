# -*- coding: utf-8 -*-
"""Sandbox preview wizard."""

from odoo import fields, models


class OmniSyncSandboxPreviewWizard(models.TransientModel):
    """Wizard to execute flows in preview mode and show the output."""

    _name = "omnisync.sandbox.preview.wizard"
    _description = "OmniSync Sandbox Preview"

    flow_id = fields.Many2one("omnisync.flow", required=True)
    preview_payload = fields.Json(readonly=True)

    def action_preview(self):
        """Run the flow in preview mode and refresh the wizard."""
        self.ensure_one()
        preview = self.flow_id.run_preview()
        self.preview_payload = preview
        return {
            "type": "ir.actions.act_window",
            "res_model": "omnisync.sandbox.preview.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
