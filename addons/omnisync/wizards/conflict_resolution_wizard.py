# -*- coding: utf-8 -*-
"""Conflict resolution wizard."""

from odoo import _, fields, models


class OmniSyncConflictResolutionWizard(models.TransientModel):
    """Wizard allowing admins to resolve conflicts interactively."""

    _name = "omnisync.conflict.resolution.wizard"
    _description = "OmniSync Conflict Resolution Wizard"

    conflict_id = fields.Many2one("omnisync.conflict", required=True)
    decision = fields.Selection(
        [
            ("remote", "Remote wins"),
            ("odoo", "Odoo wins"),
            ("dismiss", "Dismiss"),
        ],
        required=True,
        default="remote",
    )
    preview = fields.Json(related="conflict_id.differences_json", readonly=True)

    def action_resolve(self):
        """Apply the chosen resolution to the conflict."""
        self.ensure_one()
        conflict = self.conflict_id
        if self.decision == "remote":
            conflict.action_apply_remote()
        elif self.decision == "odoo":
            conflict.action_keep_odoo()
        else:
            conflict.action_dismiss()
        return {"type": "ir.actions.act_window_close"}
