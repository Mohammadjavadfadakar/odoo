# -*- coding: utf-8 -*-
"""Versioning models for OmniSync flows."""

import json

from odoo import _, fields, models
from odoo.exceptions import UserError


class OmniSyncFlowVersion(models.Model):
    """Persist snapshots of flow configurations with approval workflow."""

    _name = "omnisync.flow.version"
    _description = "OmniSync Flow Version"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True)
    flow_id = fields.Many2one("omnisync.flow", required=True, ondelete="cascade")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("awaiting", "Awaiting Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
    )
    data_blob = fields.Text(string="Serialized Configuration", readonly=True)
    change_note = fields.Text()
    approved_by = fields.Many2one("res.users", readonly=True)
    approved_on = fields.Datetime(readonly=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    def action_submit(self):
        """Submit the version for approval."""
        for version in self:
            if version.state not in {"draft", "rejected"}:
                continue
            version.state = "awaiting"
            version.flow_id.approval_state = "awaiting"
        return True

    def action_approve(self):
        """Approve the version and activate it on the flow."""
        for version in self.filtered(lambda v: v.state == "awaiting"):
            version.state = "approved"
            version.approved_by = self.env.user
            version.approved_on = fields.Datetime.now()
            version.flow_id._apply_version(version)
            version.flow_id.approval_state = "approved"
        return True

    def action_reject(self):
        """Reject the submitted version."""
        for version in self.filtered(lambda v: v.state == "awaiting"):
            version.state = "rejected"
            version.flow_id.approval_state = "rejected"
        return True

    def action_rollback(self):
        """Rollback the flow to this approved version."""
        for version in self:
            if version.state != "approved":
                raise UserError(_("Only approved versions can be rolled back."))
            version.flow_id._apply_version(version)
        return True

    def capture_from_flow(self, flow):
        """Utility method to create a snapshot from the given flow."""
        self.ensure_one()
        self.data_blob = json.dumps(flow.export_configuration(), indent=2)

    def get_configuration(self):
        """Return the stored configuration payload."""
        self.ensure_one()
        if not self.data_blob:
            return {}
        return json.loads(self.data_blob)
