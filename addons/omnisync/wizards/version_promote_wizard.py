# -*- coding: utf-8 -*-
"""Version promotion wizard."""

from odoo import _, fields, models
from odoo.exceptions import UserError


class OmniSyncVersionPromoteWizard(models.TransientModel):
    """Wizard to promote or rollback flow versions."""

    _name = "omnisync.version.promote.wizard"
    _description = "OmniSync Version Promotion"

    flow_id = fields.Many2one("omnisync.flow", required=True)
    version_id = fields.Many2one(
        "omnisync.flow.version",
        required=True,
        domain="[('flow_id', '=', flow_id)]",
    )
    operation = fields.Selection(
        [
            ("approve", "Approve"),
            ("rollback", "Rollback"),
        ],
        required=True,
        default="approve",
    )

    def action_open(self):
        """Return the wizard action."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "omnisync.version.promote.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_apply(self):
        """Apply the selected operation to the version."""
        self.ensure_one()
        if self.operation == "approve":
            if self.version_id.state not in {"draft", "awaiting"}:
                raise UserError(_("Only draft or awaiting versions can be approved."))
            if self.version_id.state == "draft":
                self.version_id.action_submit()
            self.version_id.action_approve()
        else:
            if self.version_id.state != "approved":
                raise UserError(_("Only approved versions can be rolled back."))
            self.version_id.action_rollback()
        return {"type": "ir.actions.act_window_close"}
