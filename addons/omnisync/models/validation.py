# -*- coding: utf-8 -*-
"""Validation governance for OmniSync."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from ..tools import format_json_value


class OmniSyncValidationRule(models.Model):
    """Declarative validation rules evaluated during synchronization."""

    _name = "omnisync.validation.rule"
    _description = "OmniSync Validation Rule"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        help="Company scope used to evaluate the rule and restrict visibility.",
    )
    flow_id = fields.Many2one(
        "omnisync.flow",
        required=True,
        ondelete="cascade",
        help="Flow where the rule is executed during synchronization.",
    )
    direction = fields.Selection(
        [
            ("inbound", "Inbound"),
            ("outbound", "Outbound"),
            ("both", "Both"),
        ],
        default="both",
        required=True,
        help="Defines which synchronization direction should evaluate the rule.",
    )
    severity = fields.Selection(
        [
            ("error", "Block"),
            ("warning", "Warn"),
            ("info", "Info"),
        ],
        default="error",
        required=True,
        help="Controls whether violations block processing or just raise warnings.",
    )
    expression = fields.Text(
        required=True,
        help="Python expression evaluated with payload, values, record, and env variables.",
    )
    message = fields.Char(
        required=True,
        default=lambda self: _("Validation failed"),
        help="Fallback message displayed when the rule returns a failing result.",
    )
    description = fields.Text(
        help="Detailed guidance describing the business rule being enforced.",
    )
    last_triggered = fields.Datetime(
        readonly=True,
        help="Timestamp of the most recent violation raised by this rule.",
    )
    triggered_count = fields.Integer(
        readonly=True,
        default=0,
        help="Total number of recorded violations for the rule.",
    )

    def matches_direction(self, direction: str) -> bool:
        """Return whether the rule should run for the provided direction."""
        self.ensure_one()
        return self.direction in ("both", direction)

    def evaluate(
        self,
        payload: Optional[Dict[str, Any]],
        values: Optional[Dict[str, Any]],
        record: Optional[models.Model] = None,
    ) -> Tuple[bool, str]:
        """Evaluate the rule against the provided context."""
        self.ensure_one()
        localdict = {
            "payload": payload or {},
            "values": values or {},
            "record": record,
            "env": self.env,
        }
        try:
            result = safe_eval(self.expression, localdict, mode="eval")
        except Exception as exc:  # noqa: BLE001
            raise UserError(
                _("Validation rule %(name)s failed to evaluate: %(error)s")
                % {"name": self.name, "error": exc}
            ) from exc
        message = self.message
        passed: bool
        if isinstance(result, (list, tuple)) and result:
            passed = bool(result[0])
            if len(result) > 1 and result[1]:
                message = str(result[1])
        elif isinstance(result, dict):
            passed = bool(result.get("status", True))
            if result.get("message"):
                message = str(result["message"])
        else:
            passed = bool(result)
        if not passed:
            self.sudo().write(
                {
                    "last_triggered": fields.Datetime.now(),
                    "triggered_count": self.triggered_count + 1,
                }
            )
        return passed, message

    def log_violation(
        self,
        *,
        flow: "OmniSyncFlow",
        direction: str,
        payload: Optional[Dict[str, Any]],
        values: Optional[Dict[str, Any]],
        record: Optional[models.Model],
        message: str,
    ) -> None:
        """Persist a log entry when the rule fails."""
        snapshot = flow._sanitize_payload_snapshot(
            {
                "payload": payload or {},
                "values": values or {},
            }
        )
        res_model = flow.model_id.model if flow.model_id else False
        res_id = record.id if record else False
        self.env["omnisync.validation.log"].sudo().create(
            {
                "rule_id": self.id,
                "flow_id": flow.id,
                "direction": direction,
                "severity": self.severity,
                "message": message,
                "payload_snapshot": snapshot,
                "company_id": flow.company_id.id,
                "res_model": res_model,
                "res_id": res_id,
            }
        )


class OmniSyncValidationLog(models.Model):
    """Log entries for validation rule violations."""

    _name = "omnisync.validation.log"
    _description = "OmniSync Validation Log"
    _order = "create_date desc"

    name = fields.Char(
        default=lambda self: self.env["ir.sequence"].next_by_code("omnisync.validation")
        or _("Validation"),
    )
    rule_id = fields.Many2one(
        "omnisync.validation.rule",
        required=True,
        help="Validation rule that produced this log entry.",
    )
    flow_id = fields.Many2one(
        "omnisync.flow",
        required=True,
        help="Flow that triggered the validation rule violation.",
    )
    direction = fields.Selection(
        [
            ("inbound", "Inbound"),
            ("outbound", "Outbound"),
            ("both", "Both"),
        ],
        required=True,
        help="Direction that was being processed when the violation occurred.",
    )
    severity = fields.Selection(
        [
            ("error", "Block"),
            ("warning", "Warn"),
            ("info", "Info"),
        ],
        required=True,
        help="Severity inherited from the rule at the time of logging.",
    )
    message = fields.Char(
        required=True,
        help="Explanation describing why the payload did not pass validation.",
    )
    payload_snapshot = fields.Json(
        help="Sanitized payload data captured to reproduce the validation issue.",
    )
    payload_snapshot_display = fields.Text(
        string="Payload Snapshot (JSON)",
        compute="_compute_payload_snapshot_display",
        readonly=True,
        help="Formatted preview of the recorded payload snapshot.",
    )
    details = fields.Text(
        help="Optional analyst notes with remediation steps or investigation results.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    res_model = fields.Char()
    res_id = fields.Integer()
    handled = fields.Boolean(
        default=False,
        help="Flag indicating whether an operator has triaged the violation.",
    )
    handled_by = fields.Many2one(
        "res.users",
        readonly=True,
        help="User that marked the log as handled.",
    )
    handled_date = fields.Datetime(
        readonly=True,
        help="Date when the log was marked as handled.",
    )

    def action_mark_handled(self):
        """Mark the validation log as handled."""
        self.write(
            {
                "handled": True,
                "handled_by": self.env.user.id,
                "handled_date": fields.Datetime.now(),
            }
        )
        return True

    def _compute_payload_snapshot_display(self):
        for record in self:
            record.payload_snapshot_display = format_json_value(record.payload_snapshot)
