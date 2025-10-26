# -*- coding: utf-8 -*-
"""Escalation policies for OmniSync flows."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from odoo import _, fields, models


class OmniSyncEscalationPolicy(models.Model):
    """Configuration describing automated remediation steps for flows."""

    _name = "omnisync.escalation.policy"
    _description = "OmniSync Escalation Policy"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    flow_id = fields.Many2one(
        "omnisync.flow",
        required=True,
        ondelete="cascade",
    )
    event_type = fields.Selection(
        [
            ("job_failure", "Job Failure"),
            ("validation_failure", "Validation Failure"),
        ],
        required=True,
        default="job_failure",
    )
    trigger_after = fields.Integer(
        default=3,
        help="Number of consecutive events required before the policy triggers.",
    )
    cooldown_hours = fields.Float(
        default=1.0,
        help="Minimum hours between two automatic executions of the policy.",
    )
    action_type = fields.Selection(
        [
            ("pause", "Pause Flow"),
            ("notify", "Notify Partners"),
            ("activity", "Create Activity"),
        ],
        required=True,
        default="notify",
    )
    partner_ids = fields.Many2many(
        "res.partner",
        string="Notification Recipients",
        domain=[("share", "=", False)],
    )
    activity_type_id = fields.Many2one("mail.activity.type")
    activity_summary = fields.Char()
    message_template = fields.Text(
        help="Optional message template posted when the policy executes.",
    )
    last_triggered = fields.Datetime(readonly=True)
    triggered_count = fields.Integer(readonly=True, default=0)

    def should_trigger(self, *, streak: int) -> bool:
        """Return whether the policy should activate for the current streak."""
        self.ensure_one()
        if not self.active:
            return False
        if streak < max(1, self.trigger_after):
            return False
        if not self.last_triggered:
            return True
        delta = fields.Datetime.now() - self.last_triggered
        return delta >= timedelta(hours=self.cooldown_hours or 0)

    def execute_policy(self, flow: "OmniSyncFlow", context: Dict[str, Any]) -> None:
        """Run the configured action against the provided flow."""
        self.ensure_one()
        message = self._render_message(flow, context)
        if self.action_type == "pause":
            if flow.active:
                flow.active = False
                flow.message_post(body=message)
        elif self.action_type == "notify":
            partners = self.partner_ids
            if not partners:
                partners = flow.alert_partner_ids
            if partners:
                flow.message_post(body=message, partner_ids=partners.ids)
        elif self.action_type == "activity":
            activity_vals = {
                "res_id": flow.id,
                "res_model_id": self.env.ref("omnisync.model_omnisync_flow").id,
                "activity_type_id": self.activity_type_id.id if self.activity_type_id else False,
                "summary": self.activity_summary or message,
                "note": message,
            }
            if not activity_vals["activity_type_id"]:
                activity_vals["activity_type_id"] = self.env.ref("mail.mail_activity_data_todo").id
            self.env["mail.activity"].create(activity_vals)
        self.write(
            {
                "last_triggered": fields.Datetime.now(),
                "triggered_count": self.triggered_count + 1,
            }
        )

    def _render_message(self, flow: "OmniSyncFlow", context: Dict[str, Any]) -> str:
        """Format a message using the provided context."""
        base = self.message_template or _(
            "Escalation policy %(policy)s executed for flow %(flow)s after %(streak)s events."
        )
        values = {
            "policy": self.name,
            "flow": flow.name,
            "streak": context.get("streak"),
            "event": context.get("event"),
            "details": context.get("message"),
        }
        return base % values
