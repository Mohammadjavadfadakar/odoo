# -*- coding: utf-8 -*-
import json
from urllib.parse import urljoin

from odoo import fields, models


class ConnectorEndpoint(models.Model):
    _name = "connector.endpoint"
    _description = "Connector Endpoint"

    profile_id = fields.Many2one("connector.profile", required=True, ondelete="cascade")
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    http_method = fields.Selection(
        selection=[("get", "GET"), ("post", "POST"), ("put", "PUT"), ("patch", "PATCH"), ("delete", "DELETE")],
        default="get",
        required=True,
    )
    route = fields.Char(required=True)
    request_params = fields.Json(string="Query Parameters")
    request_body_template = fields.Json(string="Request Body Template")
    response_type = fields.Selection(
        selection=[("json", "JSON"), ("xml", "XML"), ("text", "Text")],
        default="json",
    )
    pagination_mode = fields.Selection(
        selection=[
            ("none", "No Pagination"),
            ("page", "Page + Limit"),
            ("offset", "Offset + Limit"),
            ("cursor", "Cursor"),
        ],
        default="none",
    )
    pagination_field = fields.Char(string="Pagination Field")
    pagination_limit = fields.Integer(default=100)
    mapping_ids = fields.One2many("connector.mapping", "endpoint_id", string="Mappings")

    _sql_constraints = [
        ("name_profile_unique", "unique(name, profile_id)", "Endpoint names must be unique per connector."),
    ]

    def _build_headers(self):
        self.ensure_one()
        headers = {}
        if self.profile_id.headers_template:
            headers.update(self.profile_id.headers_template)
        return headers

    def _build_params(self, pagination_state=None):
        self.ensure_one()
        params = {}
        if self.request_params:
            params.update(self.request_params)
        if self.pagination_mode == "page" and pagination_state:
            params.setdefault("page", pagination_state.get("page", 1))
            params.setdefault("limit", pagination_state.get("limit", self.pagination_limit))
        elif self.pagination_mode == "offset" and pagination_state:
            params.setdefault("offset", pagination_state.get("offset", 0))
            params.setdefault("limit", pagination_state.get("limit", self.pagination_limit))
        elif self.pagination_mode == "cursor" and pagination_state:
            cursor_field = self.pagination_field or "cursor"
            if pagination_state.get(cursor_field):
                params[cursor_field] = pagination_state[cursor_field]
        return params

    def _build_body(self, payload_context=None):
        self.ensure_one()
        if not self.request_body_template:
            return None
        template = json.loads(json.dumps(self.request_body_template))
        payload_context = payload_context or {}
        return self._render_dynamic_values(template, payload_context)

    def _render_dynamic_values(self, payload, context):
        if isinstance(payload, dict):
            return {key: self._render_dynamic_values(value, context) for key, value in payload.items()}
        if isinstance(payload, list):
            return [self._render_dynamic_values(value, context) for value in payload]
        if isinstance(payload, str) and payload.startswith("${") and payload.endswith("}"):
            key = payload[2:-1]
            return context.get(key)
        return payload

    def build_request(self, payload_context=None, pagination_state=None):
        self.ensure_one()
        url = urljoin(self.profile_id.base_url.rstrip("/") + "/", self.route.lstrip("/"))
        return {
            "method": self.http_method,
            "url": url,
            "headers": self._build_headers(),
            "params": self._build_params(pagination_state=pagination_state),
            "json": self._build_body(payload_context=payload_context) if self.response_type == "json" else None,
            "data": None if self.response_type == "json" else self._build_body(payload_context=payload_context),
        }
