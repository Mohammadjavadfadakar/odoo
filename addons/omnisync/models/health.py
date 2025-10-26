# -*- coding: utf-8 -*-
"""Health monitoring models for OmniSync."""

import logging
import time
from typing import Tuple

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import DEFAULT_QUEUE_CHANNEL
from .system import ConnectorResponse

_logger = logging.getLogger(__name__)


class OmniSyncHealthCheck(models.Model):
    """Defines automated health checks for systems and flows."""

    _name = "omnisync.health.check"
    _description = "OmniSync Health Check"
    _inherit = ["mail.thread", "mail.activity.mixin", "queue.job.mixin"]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    system_id = fields.Many2one(
        "omnisync.system",
        string="System",
        required=True,
        tracking=True,
    )
    flow_id = fields.Many2one(
        "omnisync.flow",
        string="Flow",
        tracking=True,
        domain="[('system_id', '=', system_id)]",
    )
    check_type = fields.Selection(
        [
            ("connector", "Connector Reachability"),
            ("flow_preview", "Flow Preview"),
            ("mapping", "Mapping Coverage"),
        ],
        required=True,
        default="connector",
    )
    severity = fields.Selection(
        [("info", "Info"), ("warning", "Warning"), ("critical", "Critical")],
        default="warning",
    )
    last_run = fields.Datetime(readonly=True)
    last_status = fields.Selection(
        [("idle", "Idle"), ("success", "Success"), ("failed", "Failed")],
        default="idle",
        readonly=True,
    )
    last_message = fields.Text(readonly=True)
    target_endpoint = fields.Char(
        string="Endpoint",
        help="Optional endpoint override used for ping checks.",
    )
    notify_activity_type_id = fields.Many2one(
        "mail.activity.type",
        string="Activity Type",
        help="Activity created when a critical check fails.",
    )
    responsible_user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        help="Optional user that receives health check activities.",
    )
    log_ids = fields.One2many("omnisync.health.log", "check_id")

    @api.constrains("company_id", "system_id")
    def _check_company_consistency(self):
        for record in self:
            if record.system_id.company_id != record.company_id:
                raise ValidationError(
                    _(
                        "Health check company must match the company of the selected system."
                    )
                )
            if record.flow_id and record.flow_id.company_id != record.company_id:
                raise ValidationError(
                    _(
                        "Health check company must match the company of the selected flow."
                    )
                )

    def action_run(self):
        """Queue all selected checks for immediate execution."""
        for check in self:
            check.with_delay(channel=DEFAULT_QUEUE_CHANNEL)._run_health_check()
        return True

    def _run_health_check(self):
        """Execute the health check asynchronously."""
        self.ensure_one()
        self._run_health_check_now()

    def _run_health_check_now(self):
        """Execute the health check immediately and persist outcome."""
        self.ensure_one()
        start = time.time()
        status = "success"
        message = _("Health check executed successfully.")
        try:
            status, message = self._perform_check()
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            message = str(exc)
            _logger.exception("Health check %s failed: %s", self.name, exc)
        duration = time.time() - start
        self._finalize_check(status, message, duration)
        return status

    def _finalize_check(self, status: str, message: str, duration: float):
        """Persist outcome information and create log rows."""
        self.ensure_one()
        now = fields.Datetime.now()
        self.write(
            {
                "last_run": now,
                "last_status": status,
                "last_message": message,
            }
        )
        self.env["omnisync.health.log"].create(
            {
                "check_id": self.id,
                "status": status,
                "message": message,
                "duration": duration,
                "company_id": self.company_id.id,
            }
        )
        if status == "failed" and self.severity == "critical":
            self._schedule_activity(message)

    def _schedule_activity(self, message: str):
        """Create a follow-up activity for failed critical checks."""
        self.ensure_one()
        if not self.notify_activity_type_id:
            return
        self.activity_schedule(
            self.notify_activity_type_id.id,
            summary=_("Health Check Failed"),
            note=message,
            user_id=self.responsible_user_id.id or self.env.user.id,
        )

    def _perform_check(self) -> Tuple[str, str]:
        """Execute the specific check type and return a status/message pair."""
        self.ensure_one()
        if self.check_type == "connector":
            message = self._perform_connector_check()
            return "success", message
        if self.check_type == "flow_preview":
            if not self.flow_id:
                raise UserError(
                    _("Flow preview checks require a flow to be selected.")
                )
            preview = self.flow_id.run_preview()
            return (
                "success",
                _("Flow preview executed with %s sample rows.") % len(preview),
            )
        if self.check_type == "mapping":
            self._perform_mapping_check()
            return "success", _("All mapping lines reference target fields.")
        raise UserError(_("Unsupported health check type: %s") % self.check_type)

    def _perform_connector_check(self):
        """Invoke a lightweight connector request to validate reachability."""
        endpoint = self.target_endpoint or ""
        response = self.system_id.execute(endpoint=endpoint, payload=None)
        if not isinstance(response, ConnectorResponse):
            raise UserError(
                _("Health check expected a connector response instance.")
            )
        if response.status_code >= 400:
            raise UserError(
                _("Connector returned status %(status)s during health check.")
                % {"status": response.status_code}
            )
        return _("Connector reachable via endpoint %s") % endpoint

    def _perform_mapping_check(self):
        """Validate that all mappings linked to the flow have valid targets."""
        if not self.flow_id:
            raise UserError(_("Mapping checks require an associated flow."))
        broken = []
        for mapping in self.flow_id.mapping_ids:
            for line in mapping.line_ids:
                if not line.target_field_name:
                    broken.append(mapping.name)
                    break
        if broken:
            raise UserError(
                _("Mappings missing target fields: %s") % ", ".join(sorted(set(broken)))
            )

    @api.model
    def cron_run_active_checks(self):
        """Cron entry point to run active health checks."""
        checks = self.search([("active", "=", True)])
        for check in checks:
            check._run_health_check_now()


class OmniSyncHealthLog(models.Model):
    """Stores the historic results of health check executions."""

    _name = "omnisync.health.log"
    _description = "OmniSync Health Log"
    _order = "create_date desc"

    check_id = fields.Many2one(
        "omnisync.health.check",
        required=True,
        ondelete="cascade",
    )
    status = fields.Selection(
        [("success", "Success"), ("failed", "Failed")],
        required=True,
    )
    message = fields.Text()
    duration = fields.Float(help="Execution duration in seconds.")
    company_id = fields.Many2one("res.company", required=True)
    create_date = fields.Datetime(readonly=True)

