# -*- coding: utf-8 -*-
"""Conflict resolution wizard."""

from odoo import _, api, fields, models

from ..tools import format_json_value


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
    preview_text = fields.Text(
        string="Differences (JSON)",
        compute="_compute_preview_text",
        readonly=True,
    )

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

    @api.depends("preview")
    def _compute_preview_text(self):
        for wizard in self:
            wizard.preview_text = format_json_value(wizard.preview)
