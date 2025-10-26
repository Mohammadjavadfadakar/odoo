# -*- coding: utf-8 -*-
"""Webhook event store for OmniSync."""

from odoo import fields, models


class OmniSyncWebhookEvent(models.Model):
    """Persist inbound webhook payloads for asynchronous processing."""

    _name = "omnisync.webhook.event"
    _description = "OmniSync Webhook Event"
    _order = "create_date desc"

    name = fields.Char(
        default=lambda self: self.env["ir.sequence"].next_by_code("omnisync.webhook")
        or "WEBHOOK",
        readonly=True,
    )
    system_id = fields.Many2one("omnisync.system", required=True, ondelete="cascade")
    event_code = fields.Char()
    payload = fields.Json()
    state = fields.Selection(
        [("pending", "Pending"), ("processed", "Processed")],
        default="pending",
        index=True,
    )
    processed_on = fields.Datetime()

    def mark_processed(self):
        """Mark the webhook event as processed."""
        for event in self.filtered(lambda e: e.state == "pending"):
            event.state = "processed"
            event.processed_on = fields.Datetime.now()
        return True
