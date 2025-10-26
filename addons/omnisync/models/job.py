# -*- coding: utf-8 -*-
"""Job log models for OmniSync."""

from datetime import timedelta

from odoo import _, fields, models


class OmniSyncJobLog(models.Model):
    """Stores execution logs for OmniSync jobs."""

    _name = "omnisync.job.log"
    _description = "OmniSync Job Log"
    _order = "create_date desc"

    name = fields.Char(default=lambda self: self.env["ir.sequence"].next_by_code("omnisync.job") or _("Job"))
    flow_id = fields.Many2one("omnisync.flow", required=True)
    system_id = fields.Many2one(related="flow_id.system_id", store=True)
    status = fields.Selection(
        [("pending", "Pending"), ("success", "Success"), ("failed", "Failed")],
        default="pending",
        required=True,
    )
    duration = fields.Float(help="Execution duration in seconds")
    latency = fields.Float(help="Latency reported by external system")
    records_processed = fields.Integer(default=0)
    payload_preview = fields.Text()
    error_message = fields.Text()
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )

    def mark_success(self, metrics):
        self.ensure_one()
        self.write(
            {
                "status": "success",
                "duration": metrics.get("duration"),
                "latency": metrics.get("latency"),
                "records_processed": metrics.get("records_processed"),
            }
        )

    def mark_failure(self, message, payload=None):
        self.ensure_one()
        self.write(
            {
                "status": "failed",
                "error_message": message[:2000] if message else False,
                "payload_preview": payload and payload[:2000],
            }
        )


class OmniSyncJobSummary(models.Model):
    """Materialized statistics per flow for dashboard usage."""

    _name = "omnisync.job.summary"
    _description = "OmniSync Job Summary"
    _auto = False

    flow_id = fields.Many2one("omnisync.flow", readonly=True)
    success_count = fields.Integer(readonly=True)
    failure_count = fields.Integer(readonly=True)
    avg_duration = fields.Float(readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW omnisync_job_summary AS (
                SELECT
                    MIN(id) AS id,
                    flow_id,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failure_count,
                    AVG(duration) AS avg_duration
                FROM omnisync_job_log
                GROUP BY flow_id
            )
        """)


class OmniSyncJobLogMixin(models.AbstractModel):
    """Mixin providing helper methods for recording job logs."""

    _name = "omnisync.job.log.mixin"
    _description = "OmniSync Job Log Helper"

    def _create_job_log(self, flow, status="pending", payload_preview=None):
        return self.env["omnisync.job.log"].create(
            {
                "flow_id": flow.id,
                "status": status,
                "payload_preview": payload_preview,
                "company_id": flow.company_id.id,
            }
        )
