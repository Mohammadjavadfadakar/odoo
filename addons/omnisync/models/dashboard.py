# -*- coding: utf-8 -*-
"""Dashboard models for OmniSync."""

from odoo import fields, models


class OmniSyncDashboard(models.TransientModel):
    """Transient model providing KPI data for the dashboard."""

    _name = "omnisync.dashboard"
    _description = "OmniSync Dashboard"

    success_count = fields.Integer(compute="_compute_metrics")
    failure_count = fields.Integer(compute="_compute_metrics")
    avg_duration = fields.Float(compute="_compute_metrics")
    conflict_count = fields.Integer(compute="_compute_metrics")
    awaiting_approval = fields.Integer(compute="_compute_metrics")
    binding_failed_count = fields.Integer(compute="_compute_metrics")
    validation_block_count = fields.Integer(compute="_compute_metrics")
    last_jobs = fields.Json(compute="_compute_metrics")
    health_failure_count = fields.Integer(compute="_compute_metrics")
    runbook_queue_count = fields.Integer(compute="_compute_metrics")

    def _compute_metrics(self):
        summary = self.env["omnisync.job.summary"].search([])
        jobs = self.env["omnisync.job.log"].search([], order="create_date desc", limit=10)
        for record in self:
            record.success_count = sum(summary.mapped("success_count"))
            record.failure_count = sum(summary.mapped("failure_count"))
            durations = summary.mapped("avg_duration")
            record.avg_duration = sum(durations) / len(durations) if durations else 0.0
            record.conflict_count = self.env["omnisync.conflict"].search_count([("state", "=", "pending")])
            record.awaiting_approval = self.env["omnisync.flow.version"].search_count([("state", "=", "awaiting")])
            record.binding_failed_count = self.env["omnisync.binding"].search_count([("state", "=", "failed")])
            record.validation_block_count = self.env["omnisync.validation.log"].search_count(
                [("severity", "=", "error"), ("handled", "=", False)]
            )
            record.health_failure_count = self.env["omnisync.health.check"].search_count(
                [("last_status", "=", "failed")]
            )
            record.runbook_queue_count = self.env["omnisync.runbook"].search_count(
                [("last_status", "=", "queued")]
            )
            record.last_jobs = [
                {
                    "name": job.name,
                    "flow": job.flow_id.name,
                    "status": job.status,
                    "create_date": job.create_date,
                    "records": job.records_processed,
                }
                for job in jobs
            ]

    def action_reload(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "omnisync.dashboard",
            "view_mode": "kanban,form",
            "target": "current",
        }
