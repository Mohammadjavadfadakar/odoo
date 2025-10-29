# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ConnectorProfile(models.Model):
    _name = "connector.profile"
    _description = "Connector Profile"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True, copy=False)
    sequence = fields.Integer(default=10)
    system_type = fields.Selection(
        selection=[
            ("accounting", "Accounting Platform"),
            ("cloud", "Cloud Provider"),
            ("crm", "CRM"),
            ("custom", "Custom"),
        ],
        default="custom",
        required=True,
        tracking=True,
    )
    auth_mode = fields.Selection(
        selection=[
            ("no_auth", "No Authentication"),
            ("api_key", "API Key"),
            ("basic", "Basic Auth"),
            ("oauth2", "OAuth2 Client Credentials"),
        ],
        string="Authentication Mode",
        default="no_auth",
        required=True,
    )
    base_url = fields.Char(required=True)
    auth_payload = fields.Json(string="Authentication Payload")
    headers_template = fields.Json(string="Base Headers")
    description = fields.Text()
    is_active = fields.Boolean(default=True)
    endpoint_ids = fields.One2many("connector.endpoint", "profile_id", string="Endpoints")
    mapping_ids = fields.One2many("connector.mapping", "profile_id", string="Mappings")
    run_ids = fields.One2many("connector.run", "profile_id", string="Runs")

    @api.constrains("code")
    def _check_code_uniqueness(self):
        for record in self:
            if not record.code:
                raise ValidationError("A technical code is required for every connector profile.")
            domain = [
                ("id", "!=", record.id),
                ("code", "=", (record.code or "").strip()),
            ]
            if self.search_count(domain):
                raise ValidationError("Connector code must be unique.")

    @api.model
    def get_connector_by_code(self, code):
        return self.search([("code", "=", code)], limit=1)

    def action_open_dashboard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"{self.name} Dashboard",
            "res_model": "connector.run",
            "view_mode": "tree,form",
            "domain": [("profile_id", "=", self.id)],
            "context": {"default_profile_id": self.id},
        }
