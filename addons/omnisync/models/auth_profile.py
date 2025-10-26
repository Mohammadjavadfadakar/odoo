# -*- coding: utf-8 -*-
"""Authentication profile models for OmniSync."""

from datetime import datetime, timedelta
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OmniSyncAuthProfile(models.Model):
    """Represents an authentication profile used by integrations."""

    _name = "omnisync.auth.profile"
    _description = "OmniSync Authentication Profile"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    auth_type = fields.Selection(
        [
            ("api_key", "API Key"),
            ("basic", "Basic Auth"),
            ("oauth2_client", "OAuth2 Client Credentials"),
            ("oauth2_pkce", "OAuth2 PKCE"),
            ("custom_flow", "Custom Flow"),
        ],
        required=True,
        default="api_key",
        tracking=True,
    )
    description = fields.Text()
    auth_payload = fields.Text(
        string="Auth Payload",
        help="JSON structure describing the authentication payload."
        " Secrets are stored encrypted and masked in the UI.",
        tracking=False,
    )
    encrypted_secret = fields.Text(
        string="Encrypted Secret",
        readonly=True,
        copy=False,
        help="Contains the encrypted secret material. Use the action buttons"
        " to update or view masked values.",
    )
    token_endpoint = fields.Char()
    client_id = fields.Char()
    client_secret_masked = fields.Char(
        compute="_compute_masked_secret",
        string="Client Secret",
    )
    access_token = fields.Char(string="Access Token", copy=False)
    refresh_token = fields.Char(string="Refresh Token", copy=False)
    token_expiration = fields.Datetime(copy=False)
    last_sync_status = fields.Selection(
        [
            ("idle", "Idle"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        default="idle",
        tracking=True,
    )

    def _encrypt_value(self, value):
        """Encrypt the provided value using Odoo's secret key infrastructure."""
        if not value:
            return False
        config = self.env["ir.config_parameter"].sudo()
        encrypt = getattr(config, "_encrypt", None)
        if not encrypt:
            raise UserError(
                _(
                    "Encryption service is not available on this Odoo instance."
                    " Please enable the 'Secret Storage' feature."
                )
            )
        return encrypt(value)

    def _decrypt_value(self, value):
        """Decrypt a stored encrypted value."""
        if not value:
            return False
        config = self.env["ir.config_parameter"].sudo()
        decrypt = getattr(config, "_decrypt", None)
        if not decrypt:
            raise UserError(
                _(
                    "Decryption service is not available on this Odoo instance."
                    " Please enable the 'Secret Storage' feature."
                )
            )
        return decrypt(value)

    @api.depends("encrypted_secret")
    def _compute_masked_secret(self):
        """Display a masked representation of the secret material."""
        for profile in self:
            if profile.encrypted_secret:
                profile.client_secret_masked = "••••••••"
            else:
                profile.client_secret_masked = False

    def write(self, vals):
        """Encrypt incoming secret payloads before saving them."""
        payload = vals.get("auth_payload")
        if payload:
            vals["encrypted_secret"] = self._encrypt_value(payload)
            vals["auth_payload"] = "***"
        for field_name in ["access_token", "refresh_token"]:
            if vals.get(field_name):
                vals[field_name] = "***"
        res = super().write(vals)
        return res

    @api.model
    def create(self, vals):
        """Encrypt secrets at create time."""
        payload = vals.get("auth_payload")
        if payload:
            vals["encrypted_secret"] = self._encrypt_value(payload)
            vals["auth_payload"] = "***"
        for field_name in ["access_token", "refresh_token"]:
            if vals.get(field_name):
                vals[field_name] = "***"
        return super().create(vals)

    def _get_secret_payload(self):
        """Return the decrypted secret payload as a Python dictionary."""
        self.ensure_one()
        if not self.encrypted_secret:
            return {}
        decrypted = self._decrypt_value(self.encrypted_secret)
        return json.loads(decrypted or "{}")

    def _update_tokens(self, token_data):
        """Store token information in encrypted format."""
        self.ensure_one()
        payload = self._get_secret_payload()
        payload["last_token"] = token_data
        self.encrypted_secret = self._encrypt_value(json.dumps(payload))
        self.last_sync_status = "success"
        if token_data.get("access_token"):
            self.access_token = "***"
        if token_data.get("refresh_token"):
            self.refresh_token = "***"
        if token_data.get("expires_in"):
            self.token_expiration = datetime.utcnow() + timedelta(
                seconds=token_data["expires_in"]
            )

    def action_test_authentication(self):
        """Simulate an authentication run to validate credentials."""
        for profile in self:
            payload = profile._get_secret_payload()
            if not payload:
                raise UserError(
                    _(
                        "No authentication payload defined for profile %s."
                        " Please configure the credentials."
                    )
                    % profile.name
                )
            profile.message_post(
                body=_("Authentication payload validated."),
            )
            profile.last_sync_status = "success"
        return True

    def get_authorization_header(self):
        """Return a standard authorization header based on the auth type."""
        self.ensure_one()
        payload = self._get_secret_payload()
        if self.auth_type == "api_key":
            api_key = payload.get("api_key")
            if not api_key:
                raise UserError(
                    _("API key is missing in the authentication profile %s")
                    % self.name
                )
            return {"Authorization": payload.get("header_template", "Bearer %s") % api_key}
        if self.auth_type == "basic":
            username = payload.get("username")
            password = payload.get("password")
            if not username or not password:
                raise UserError(
                    _("Username or password missing in authentication profile %s")
                    % self.name
                )
            return {"Authorization": "Basic %s:%s" % (username, password)}
        if self.auth_type in ("oauth2_client", "oauth2_pkce") and self.token_expiration:
            if fields.Datetime.now() >= self.token_expiration:
                raise UserError(
                    _(
                        "The OAuth token for profile %s has expired. Please refresh"
                        " the token manually or configure automatic refresh."
                    )
                    % self.name
                )
            payload_token = payload.get("last_token", {})
            token = payload_token.get("access_token")
            if token:
                return {"Authorization": "Bearer %s" % token}
        return {}
