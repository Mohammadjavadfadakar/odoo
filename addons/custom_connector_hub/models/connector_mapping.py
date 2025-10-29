# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ConnectorMapping(models.Model):
    _name = "connector.mapping"
    _description = "Connector Mapping"
    _order = "sequence, id"

    profile_id = fields.Many2one("connector.profile", required=True, ondelete="cascade")
    endpoint_id = fields.Many2one("connector.endpoint", ondelete="cascade")
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    direction = fields.Selection(
        selection=[
            ("inbound", "Inbound"),
            ("outbound", "Outbound"),
        ],
        required=True,
        default="inbound",
    )
    model_id = fields.Many2one("ir.model", required=True, string="Target Model", ondelete="cascade")
    domain_filter = fields.Char(string="Domain Filter")
    field_mapping = fields.Json(string="Field Mapping", help="Mapping between external payload keys and Odoo fields")
    validators = fields.Json(string="Validators")

    _sql_constraints = [
        (
            "mapping_unique",
            "unique(name, profile_id, endpoint_id, direction)",
            "Mapping name must be unique for a connector, endpoint, and direction.",
        ),
    ]

    @api.model
    def map_payload_to_values(self, mapping_id, payload):
        mapping = self.browse(mapping_id)
        return mapping._map_payload(payload)

    def _map_payload(self, payload):
        self.ensure_one()
        if not self.field_mapping:
            return {}
        values = {}
        for field_name, config in self.field_mapping.items():
            if isinstance(config, dict):
                source = config.get("source")
                default = config.get("default")
                transform = config.get("transform")
            else:
                source = config
                default = None
                transform = None
            value = self._extract_value(payload, source)
            if value is None:
                value = default
            if transform and value is not None:
                value = self._apply_transform(transform, value)
            if value is not None:
                values[field_name] = value
        return values

    def _extract_value(self, payload, path):
        if not path:
            return None
        parts = path.split(".")
        current = payload
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _apply_transform(self, transform, value):
        if transform == "to_upper":
            return str(value).upper()
        if transform == "to_lower":
            return str(value).lower()
        if transform == "to_float":
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
        if transform == "to_int":
            try:
                return int(value)
            except (ValueError, TypeError):
                return value
        return value
