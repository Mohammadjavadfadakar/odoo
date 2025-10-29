# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import api, fields, models


class ConnectorRun(models.Model):
    _name = "connector.run"
    _description = "Connector Run"
    _order = "create_date desc"

    name = fields.Char(default="New", readonly=True)
    profile_id = fields.Many2one("connector.profile", required=True, ondelete="cascade")
    endpoint_id = fields.Many2one("connector.endpoint", ondelete="set null")
    status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("running", "Running"),
            ("success", "Success"),
            ("failed", "Failed"),
            ("partial", "Partial"),
        ],
        default="draft",
        required=True,
    )
    direction = fields.Selection(
        selection=[("inbound", "Inbound"), ("outbound", "Outbound")],
        required=True,
    )
    external_reference = fields.Char()
    payload_request = fields.Json()
    payload_response = fields.Json()
    message = fields.Text()
    duration = fields.Float(help="Execution duration in seconds")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("connector.run") or "New"
        return super().create(vals_list)

    def mark_running(self):
        self.write({"status": "running"})

    def mark_done(self, success=True, message=None, response=None, started_at=None):
        values = {
            "status": "success" if success else "failed",
            "message": message,
            "payload_response": response,
        }
        if started_at:
            values["duration"] = (datetime.utcnow() - started_at).total_seconds()
        self.write(values)

    def start_new_run(self, direction, endpoint=None, payload_request=None):
        self.ensure_one()
        start_time = datetime.utcnow()
        run = self.create(
            {
                "profile_id": self.profile_id.id,
                "endpoint_id": endpoint.id if endpoint else False,
                "direction": direction,
                "status": "running",
                "payload_request": payload_request,
            }
        )
        return run, start_time

    @api.model
    def create_from_response(self, profile, endpoint, direction, request_payload, response_payload, message, success=True):
        duration = 0.0
        return self.create(
            {
                "profile_id": profile.id,
                "endpoint_id": endpoint.id if endpoint else False,
                "direction": direction,
                "status": "success" if success else "failed",
                "payload_request": request_payload,
                "payload_response": response_payload,
                "message": message,
                "duration": duration,
            }
        )
