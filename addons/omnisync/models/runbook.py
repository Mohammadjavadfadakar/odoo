# -*- coding: utf-8 -*-
"""Runbook orchestration for OmniSync."""

import logging
import time

from odoo import _, api, fields, models

from ..tools import DEFAULT_QUEUE_CHANNEL

_logger = logging.getLogger(__name__)


class OmniSyncRunbook(models.Model):
    """Groups flows into orchestrated execution plans."""

    _name = "omnisync.runbook"
    _description = "OmniSync Runbook"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    line_ids = fields.One2many("omnisync.runbook.line", "runbook_id", copy=True)
    description = fields.Text()
    last_run = fields.Datetime(readonly=True)
    last_status = fields.Selection(
        [("idle", "Idle"), ("queued", "Queued"), ("failed", "Failed")],
        default="idle",
        readonly=True,
    )
    last_message = fields.Text(readonly=True)
    last_duration = fields.Float(readonly=True)
    notify_user_id = fields.Many2one(
        "res.users",
        string="Notify User",
        help="User notified when runbook execution fails.",
    )

    def action_execute(self):
        """Queue the runbook execution as a background job."""
        for runbook in self:
            runbook.with_delay(channel=DEFAULT_QUEUE_CHANNEL)._execute_runbook()
        return True

    def _execute_runbook(self):
        """Execute all flows contained in the runbook."""
        self.ensure_one()
        start = time.time()
        message_lines = []
        status = "queued"
        try:
            processed = self._execute_runbook_now(message_lines)
            message_lines.append(_("Queued %s flows for execution.") % processed)
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            message_lines.append(str(exc))
            _logger.exception("Runbook %s failed to queue flows: %s", self.name, exc)
            self._notify_failure(str(exc))
        duration = time.time() - start
        self.write(
            {
                "last_run": fields.Datetime.now(),
                "last_status": status,
                "last_duration": duration,
                "last_message": "\n".join(message_lines),
            }
        )

    def _execute_runbook_now(self, message_lines):
        """Internal helper performing runbook orchestration."""
        self.ensure_one()
        processed = 0
        for line in self.line_ids.sorted("sequence"):
            flow = line.flow_id
            context = {}
            if line.preview_mode:
                context["omnisync_preview"] = True
            flow.with_context(**context).action_sync_now()
            processed += 1
            message_lines.append(
                _("Flow %(flow)s queued in %(mode)s mode.")
                % {
                    "flow": flow.name,
                    "mode": _("preview") if line.preview_mode else _("live"),
                }
            )
        return processed

    def _notify_failure(self, message: str):
        """Notify stakeholders when runbook execution fails."""
        self.ensure_one()
        partner = self.notify_user_id.partner_id if self.notify_user_id else False
        if not partner:
            return
        self.message_post(
            body=_("Runbook execution failed: %s") % message,
            partner_ids=[partner.id],
        )


class OmniSyncRunbookLine(models.Model):
    """Sequence of flows that compose a runbook."""

    _name = "omnisync.runbook.line"
    _description = "OmniSync Runbook Line"
    _order = "sequence, id"

    runbook_id = fields.Many2one("omnisync.runbook", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    flow_id = fields.Many2one("omnisync.flow", required=True)
    preview_mode = fields.Boolean(
        string="Preview Mode",
        help="Queue the flow in sandbox preview mode when enabled.",
    )
    notes = fields.Text()

    @api.constrains("runbook_id", "flow_id")
    def _check_company(self):
        for line in self:
            if line.flow_id.company_id != line.runbook_id.company_id:
                raise models.ValidationError(
                    _("Runbook and flow companies must match for %s")
                    % line.flow_id.name
                )

