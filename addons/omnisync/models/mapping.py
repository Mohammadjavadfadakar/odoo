# -*- coding: utf-8 -*-
"""Mapping engine models for OmniSync."""

import json
from typing import Any, Dict, Optional

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


TRANSFORM_SELECTION = [
    ("trim", "Trim"),
    ("upper", "Uppercase"),
    ("lower", "Lowercase"),
    ("type_cast", "Type Cast"),
    ("jalali_to_gregorian", "Jalali → Gregorian"),
    ("gregorian_to_jalali", "Gregorian → Jalali"),
    ("format", "Format"),
]


class OmniSyncMapping(models.Model):
    """A mapping definition linking external payload to Odoo fields."""

    _name = "omnisync.mapping"
    _description = "OmniSync Mapping"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        help="Company that owns this mapping. Automatically aligned with the flow company.",
    )
    flow_id = fields.Many2one("omnisync.flow", string="Flow", required=True)
    target_model_id = fields.Many2one(
        "ir.model",
        string="Target Model",
        required=True,
        domain=[("model", "!=", "")],
    )
    mode = fields.Selection(
        [("simple", "Simple"), ("advanced", "Advanced")],
        default="simple",
        required=True,
    )
    line_ids = fields.One2many("omnisync.mapping.line", "mapping_id", copy=True)
    validation_domain = fields.Char(
        help="Optional domain that is evaluated prior to write operations"
        " to validate incoming data."
    )

    @api.onchange("flow_id")
    def _onchange_flow_id(self):
        if self.flow_id:
            self.company_id = self.flow_id.company_id

    def apply(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the mapping to the incoming payload."""
        self.ensure_one()
        result = {}
        for line in self.line_ids:
            value = line.extract_value(payload)
            result[line.target_field_name] = value
        if self.validation_domain:
            domain = safe_eval(self.validation_domain)
            if not isinstance(domain, (list, tuple)):
                raise UserError(_("Validation domain must evaluate to a domain list."))
        return result

    def export_configuration(self) -> Dict[str, Any]:
        """Return a portable representation of the mapping."""
        self.ensure_one()
        return {
            "name": self.name,
            "mode": self.mode,
            "target_model": self.target_model_id.model,
            "lines": [line.export_configuration() for line in self.line_ids],
        }

    def extract_external_identifier(
        self,
        payload: Dict[str, Any],
        mapped_values: Optional[Dict[str, Any]] = None,
    ):
        """Return the identifier flagged by mapping lines, if present."""
        self.ensure_one()
        for line in self.line_ids:
            if not line.is_external_identifier:
                continue
            identifier = None
            if payload:
                identifier = line.extract_value(payload)
            if identifier in (None, "") and mapped_values:
                identifier = mapped_values.get(line.target_field_name)
            if identifier not in (None, ""):
                return identifier
        return None


class OmniSyncMappingLine(models.Model):
    """Individual mapping instructions."""

    _name = "omnisync.mapping.line"
    _description = "OmniSync Mapping Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    mapping_id = fields.Many2one("omnisync.mapping", required=True, ondelete="cascade")
    source_field = fields.Char(
        help="Path to the value in the external payload (JSONPath or key)."
    )
    target_field_name = fields.Char(required=True)
    default_value = fields.Char(
        help="Default value if the source is not found."
    )
    formula = fields.Text(
        help="Safe evaluation formula executed in advanced mode."
    )
    transform_chain = fields.Char(
        help="Comma separated transforms to apply in order."
    )
    is_external_identifier = fields.Boolean(
        string="External Identifier",
        help="Mark this line as providing the external system identifier for"
        " binding tracking.",
    )
    relation_resolution = fields.Selection(
        [
            ("none", "No Relation"),
            ("match", "Match Existing"),
            ("create", "Create if Missing"),
        ],
        default="none",
    )

    def export_configuration(self) -> Dict[str, Any]:
        self.ensure_one()
        return {
            "source_field": self.source_field,
            "target_field_name": self.target_field_name,
            "default_value": self.default_value,
            "formula": self.formula,
            "transforms": self.transform_chain,
            "is_external_identifier": self.is_external_identifier,
            "relation_resolution": self.relation_resolution,
        }

    def _apply_transforms(self, value: Any) -> Any:
        """Apply configured transforms to the provided value."""
        transforms = (self.transform_chain or "").split(",")
        for transform in [item.strip() for item in transforms if item.strip()]:
            if transform == "trim" and isinstance(value, str):
                value = value.strip()
            elif transform == "upper" and isinstance(value, str):
                value = value.upper()
            elif transform == "lower" and isinstance(value, str):
                value = value.lower()
            elif transform == "type_cast":
                value = self._type_cast(value)
            elif transform == "format" and isinstance(value, str) and self.default_value:
                value = self.default_value.format(value=value)
            elif transform == "jalali_to_gregorian":
                value = self._convert_jalali_to_gregorian(value)
            elif transform == "gregorian_to_jalali":
                value = self._convert_gregorian_to_jalali(value)
        return value

    def _type_cast(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        try:
            return float(value)
        except (ValueError, TypeError):
            return value

    def _convert_jalali_to_gregorian(self, value: Any) -> Any:
        # Placeholder for actual conversion logic
        return value

    def _convert_gregorian_to_jalali(self, value: Any) -> Any:
        # Placeholder for actual conversion logic
        return value

    def extract_value(self, payload: Dict[str, Any]):
        """Extract a value from the payload applying transforms and defaults."""
        value = self._walk_payload(payload, self.source_field) if self.source_field else None
        if value is None and self.default_value is not None:
            value = self.default_value
        if self.formula:
            env = {
                "value": value,
                "payload": payload,
                "json": json,
            }
            value = safe_eval(self.formula, env, nocopy=True)
        value = self._apply_transforms(value)
        return value

    def _walk_payload(self, payload: Dict[str, Any], path: str):
        """Navigate in a nested dictionary using dotted path."""
        if not path:
            return None
        cursor = payload
        for key in path.split("."):
            if isinstance(cursor, dict) and key in cursor:
                cursor = cursor[key]
            else:
                return None
        return cursor
