# -*- coding: utf-8 -*-
"""Queue buffer models for OmniSync."""

from odoo import fields, models


class OmniSyncQueueMessage(models.Model):
    """Internal buffer for queue connector messages."""

    _name = "omnisync.queue.message"
    _description = "OmniSync Queue Message"
    _order = "create_date"

    name = fields.Char(
        default=lambda self: self.env["ir.sequence"].next_by_code("omnisync.queue")
        or "QUEUE",
        readonly=True,
    )
    system_id = fields.Many2one("omnisync.system", required=True, ondelete="cascade")
    topic = fields.Char(required=True)
    payload = fields.Json()
    state = fields.Selection(
        [("pending", "Pending"), ("processed", "Processed")],
        default="pending",
        index=True,
    )
    processed_on = fields.Datetime()

    def mark_processed(self):
        """Mark the message as processed."""
        for message in self.filtered(lambda m: m.state == "pending"):
            message.state = "processed"
            message.processed_on = fields.Datetime.now()
        return True
