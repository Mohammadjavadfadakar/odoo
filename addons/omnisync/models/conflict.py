# -*- coding: utf-8 -*-
"""Conflict management models for OmniSync."""

from odoo import _, fields, models


class OmniSyncConflict(models.Model):
    """Store detected conflicts between remote payloads and Odoo records."""

    _name = "omnisync.conflict"
    _description = "OmniSync Conflict"
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
