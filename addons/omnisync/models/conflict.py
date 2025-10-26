# -*- coding: utf-8 -*-
"""Conflict management models for OmniSync."""

from odoo import _, fields, models

from ..tools import format_json_value


class OmniSyncConflict(models.Model):
    """Store detected conflicts between remote payloads and Odoo records."""

    _name = "omnisync.conflict"
    _description = "OmniSync Conflict"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        default=lambda self: self.env["ir.sequence"].next_by_code("omnisync.conflict")
        or "Conflict",
        readonly=True,
    )
    flow_id = fields.Many2one("omnisync.flow", required=True)
    model_name = fields.Char(required=True)
    record_id = fields.Integer(string="Record ID")
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("resolved", "Resolved"),
            ("dismissed", "Dismissed"),
        ],
        default="pending",
        tracking=True,
    )
    resolution = fields.Selection(
        [
            ("remote", "Remote wins"),
            ("odoo", "Odoo wins"),
            ("dismissed", "Dismissed"),
        ],
        tracking=True,
    )
    external_payload = fields.Json(string="Remote Payload", readonly=True)
    candidate_values = fields.Json(string="Mapped Values", readonly=True)
    differences_json = fields.Json(string="Differences", readonly=True)
    external_payload_display = fields.Text(
        string="Remote Payload (JSON)",
        compute="_compute_display_payloads",
        readonly=True,
    )
    candidate_values_display = fields.Text(
        string="Mapped Values (JSON)",
        compute="_compute_display_payloads",
        readonly=True,
    )
    differences_display = fields.Text(
        string="Differences (JSON)",
        compute="_compute_display_payloads",
        readonly=True,
    )
    resolved_by = fields.Many2one("res.users", readonly=True)
    resolved_on = fields.Datetime(readonly=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    def _get_target_record(self):
        """Return the target Odoo record if still available."""
        self.ensure_one()
        if not self.model_name or not self.record_id:
            return None
        return self.env[self.model_name].browse(self.record_id)

    def action_apply_remote(self):
        """Apply remote values to the target record."""
        for conflict in self.filtered(lambda c: c.state == "pending"):
            record = conflict._get_target_record()
            if not record:
                continue
            record.write(conflict.candidate_values or {})
            conflict._mark_resolved("remote")
        return True

    def action_keep_odoo(self):
        """Mark the conflict as resolved keeping the Odoo version."""
        for conflict in self.filtered(lambda c: c.state == "pending"):
            conflict._mark_resolved("odoo")
        return True

    def action_dismiss(self):
        """Dismiss the conflict without taking any action."""
        for conflict in self.filtered(lambda c: c.state == "pending"):
            conflict.state = "dismissed"
            conflict.resolution = "dismissed"
            conflict.resolved_by = self.env.user
            conflict.resolved_on = fields.Datetime.now()
        return True

    def action_open_resolution_wizard(self):
        """Open the conflict resolution wizard."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "omnisync.conflict.resolution.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_conflict_id": self.id},
        }

    def _mark_resolved(self, resolution):
        """Set resolution metadata and notify the flow."""
        self.ensure_one()
        self.state = "resolved"
        self.resolution = resolution
        self.resolved_by = self.env.user
        self.resolved_on = fields.Datetime.now()
        body = _(
            "Conflict %(name)s resolved with decision: %(resolution)s"
        ) % {"name": self.name, "resolution": resolution}
        self.flow_id.message_post(body=body)

    def _compute_display_payloads(self):
        for record in self:
            record.external_payload_display = format_json_value(record.external_payload)
            record.candidate_values_display = format_json_value(record.candidate_values)
            record.differences_display = format_json_value(record.differences_json)
