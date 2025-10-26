# -*- coding: utf-8 -*-
"""Public controllers for OmniSync."""

from odoo import http
from odoo.http import request


class OmniSyncDashboardController(http.Controller):
    """Controller providing dashboard data for auto-refresh widgets."""

    @http.route("/omnisync/dashboard/metrics", type="json", auth="user")
    def dashboard_metrics(self):
        dashboard = request.env["omnisync.dashboard"].sudo().create({})
        return {
            "success": dashboard.success_count,
            "failure": dashboard.failure_count,
            "avg_duration": dashboard.avg_duration,
            "jobs": dashboard.last_jobs,
        }

    @http.route(
        "/omnisync/webhook/<string:secret>",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def webhook_ingest(self, secret, **payload):
        """Receive webhook payloads and persist them for queue processing."""
        system = request.env["omnisync.system"].sudo().search(
            [("webhook_secret", "=", secret)],
            limit=1,
        )
        if not system:
            return {"status": "error", "message": "Unknown webhook secret"}
        request.env["omnisync.webhook.event"].sudo().create(
            {
                "system_id": system.id,
                "event_code": payload.get("event"),
                "payload": payload,
            }
        )
        return {"status": "ok"}
