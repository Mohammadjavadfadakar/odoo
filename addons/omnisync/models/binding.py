# -*- coding: utf-8 -*-
"""Binding records keeping track of external system references."""

from typing import Any, Dict, Optional

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OmniSyncBinding(models.Model):
    """Represents the relationship between an Odoo record and an external ID."""

    _name = "omnisync.binding"
    _description = "OmniSync Binding"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "external_identifier"
    _order = "last_synced_at desc, id desc"

    flow_id = fields.Many2one(
        "omnisync.flow",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    system_id = fields.Many2one(
        "omnisync.system",
        related="flow_id.system_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="flow_id.company_id",
        store=True,
        readonly=True,
    )
    model_id = fields.Many2one("ir.model", required=True)
    model_name = fields.Char(related="model_id.model", store=True, readonly=True)
    res_id = fields.Integer(string="Record ID", required=True, index=True)
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound")],
        required=True,
        default="inbound",
        index=True,
        tracking=True,
    )
    external_identifier = fields.Char(required=True, index=True, tracking=True)
    last_synced_at = fields.Datetime(index=True)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("synced", "Synced"),
            ("failed", "Failed"),
        ],
        default="pending",
        tracking=True,
        index=True,
    )
    last_error = fields.Text()
    payload_snapshot = fields.Json()
    record_display_name = fields.Char(
        string="Record Name",
        compute="_compute_record_display_name",
        store=False,
    )

    _sql_constraints = [
        (
            "omnisync_binding_unique",
            "unique(flow_id, direction, external_identifier)",
            "A binding already exists for this external identifier.",
        )
    ]

    def _compute_record_display_name(self):
        """Compute the display name of the linked Odoo record."""
        for binding in self:
            display_name = False
            model_name = binding.model_id.model
            if model_name:
                record = self.env[model_name].browse(binding.res_id)
                if record.exists():
                    display_name = record.display_name
                else:
                    display_name = _("Record not found")
            binding.record_display_name = display_name

    @api.model
    def register_binding(
        self,
        *,
        flow: models.Model,
        record: models.Model,
        identifier: str,
        direction: str,
        state: str = "synced",
        snapshot: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> "OmniSyncBinding":
        """Create or update a binding entry for the given record."""
        if not (flow and record and identifier):
            return self.browse()
        identifier_text = str(identifier)
        binding = self.search(
            [
                ("flow_id", "=", flow.id),
                ("direction", "=", direction),
                ("external_identifier", "=", identifier_text),
            ],
            limit=1,
        )
        values = {
            "res_id": record.id,
            "model_id": flow.model_id.id,
            "last_synced_at": fields.Datetime.now(),
            "state": state,
            "payload_snapshot": snapshot,
            "last_error": error_message if error_message else False,
        }
        if binding:
            binding.write(values)
        else:
            values.update(
                {
                    "flow_id": flow.id,
                    "direction": direction,
                    "external_identifier": identifier_text,
                }
            )
            binding = self.create(values)
        return binding

    def action_open_record(self):
        """Open the linked record in form view."""
        self.ensure_one()
        model_name = self.model_id.model
        if not model_name:
            raise UserError(_("The binding is missing its target model."))
        record = self.env[model_name].browse(self.res_id)
        if not record.exists():
            raise UserError(_("The linked record could not be found."))
        return {
            "type": "ir.actions.act_window",
            "name": record.display_name,
            "res_model": model_name,
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }
