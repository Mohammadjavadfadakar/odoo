# -*- coding: utf-8 -*-
"""Integration system definitions and connector implementations."""
import csv
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import format_json_value, parse_json_text

_logger = logging.getLogger(__name__)


@dataclass
class ConnectorResponse:
    """Represents a normalized response from a connector."""

    status_code: int
    data: Any
    headers: Dict[str, Any]
    raw: Any


class BaseConnector:
    """Base connector class providing shared utilities."""

    def __init__(self, system_record: "OmniSyncSystem"):
        self.system = system_record
        self.session = requests.Session()

    # pylint: disable=unused-argument
    def execute(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, **kwargs):
        raise NotImplementedError

    def _prepare_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "Odoo-OmniSync/1.0"}
        if self.system.auth_profile_id:
            try:
                headers.update(self.system.auth_profile_id.get_authorization_header())
            except UserError as exc:
                raise
            except Exception as exc:  # noqa: BLE001
                _logger.exception("Failed to generate authorization header: %s", exc)
        headers.update(self.system.extra_headers or {})
        return headers


class RestConnector(BaseConnector):
    """Connector for REST/JSON APIs."""

    def execute(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, **kwargs):
        method = kwargs.get("method", "GET").upper()
        url = self.system._build_url(endpoint)
        headers = self._prepare_headers()
        params = kwargs.get("params")
        timeout = kwargs.get("timeout", 60)
        data = None
        json_payload = None
        if method in {"POST", "PUT", "PATCH"}:
            if kwargs.get("json", True):
                json_payload = payload
            else:
                data = payload
        response = self.session.request(
            method,
            url,
            params=params,
            json=json_payload,
            data=data,
            headers=headers,
            timeout=timeout,
        )
        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text
        return ConnectorResponse(
            status_code=response.status_code,
            data=response_data,
            headers=dict(response.headers),
            raw=response,
        )


class SoapConnector(BaseConnector):
    """Connector for SOAP/WSDL services using the requests session."""

    def execute(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, **kwargs):
        url = self.system._build_url(endpoint)
        headers = self._prepare_headers()
        headers.setdefault("Content-Type", "text/xml;charset=UTF-8")
        body = payload.get("body") if payload else None
        response = self.session.post(url, data=body, headers=headers)
        return ConnectorResponse(
            status_code=response.status_code,
            data=response.text,
            headers=dict(response.headers),
            raw=response,
        )


class GraphQLConnector(RestConnector):
    """Connector dedicated to GraphQL endpoints."""

    def execute(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, **kwargs):
        query = kwargs.get("query") or (payload or {}).get("query")
        variables = kwargs.get("variables") or (payload or {}).get("variables") or {}
        if not query:
            query = self.system.graphql_default_query
        if not query:
            raise UserError(_("GraphQL query is required for system %s") % self.system.name)
        url = self.system._build_url(endpoint or "")
        headers = self._prepare_headers()
        response = self.session.post(
            url,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=kwargs.get("timeout", 60),
        )
        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text
        return ConnectorResponse(
            status_code=response.status_code,
            data=response_data,
            headers=dict(response.headers),
            raw=response,
        )


class DatabaseConnector(BaseConnector):
    """Connector handling PostgreSQL and MySQL operations."""

    def _get_connection(self):
        params = self.system._get_database_parameters()
        engine = params.get("engine")
        missing = [key for key in ("host", "database", "username") if not params.get(key)]
        if missing:
            raise UserError(
                _("Database configuration is missing values: %s") % ", ".join(missing)
            )
        if engine == "postgres":
            try:
                import psycopg2  # type: ignore
            except ImportError as exc:  # noqa: BLE001
                raise UserError(_("psycopg2 is required for PostgreSQL connections")) from exc
            return psycopg2.connect(
                host=params.get("host"),
                port=params.get("port"),
                dbname=params.get("database"),
                user=params.get("username"),
                password=params.get("password"),
            )
        if engine == "mysql":
            try:
                import mysql.connector  # type: ignore  # noqa: WPS433
            except ImportError as exc:  # noqa: BLE001
                raise UserError(
                    _(
                        "mysql-connector-python is required for MySQL connections."
                        " Install it on the Odoo server."
                    )
                ) from exc
            return mysql.connector.connect(
                host=params.get("host"),
                port=params.get("port"),
                database=params.get("database"),
                user=params.get("username"),
                password=params.get("password"),
            )
        raise UserError(_("Unsupported database engine: %s") % engine)

    def execute(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, **kwargs):
        query = kwargs.get("query") or endpoint
        if not query:
            raise UserError(_("Database query is required for system %s") % self.system.name)
        parameters = kwargs.get("parameters") or (payload or {}).get("parameters")
        operation = kwargs.get("operation", "read")
        connection = self._get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(query, parameters)
            headers: Dict[str, Any] = {}
            data: List[Dict[str, Any]] = []
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
            if operation in {"write", "delete", "update"} and not connection.autocommit:
                connection.commit()
            return ConnectorResponse(
                status_code=200,
                data=data,
                headers=headers,
                raw=None,
            )
        finally:
            cursor.close()
            connection.close()


class FileConnector(BaseConnector):
    """Connector to interact with local or remote file systems."""

    def execute(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, **kwargs):
        backend = self.system.file_backend
        operation = kwargs.get("operation", "read")
        target_path = kwargs.get("path") or endpoint
        if backend != "local":
            raise UserError(
                _(
                    "Only the local file backend is supported out of the box."
                    " Configure an external scheduler or extend the connector."
                )
            )
        base_path = Path(self.system.file_base_path or ".")
        if target_path:
            candidate = Path(target_path)
            file_path = candidate if candidate.is_absolute() else base_path / candidate
        else:
            file_path = base_path
        if operation == "read":
            if not file_path.exists():
                if target_path:
                    raise UserError(_("File %s was not found") % file_path)
                file_path.mkdir(parents=True, exist_ok=True)
            if file_path.is_dir():
                return ConnectorResponse(status_code=200, data=[], headers={}, raw=None)
            content = file_path.read_text(encoding="utf-8")
            if self.system.file_format == "csv":
                reader = csv.DictReader(content.splitlines())
                data = list(reader)
            else:
                data = content
            return ConnectorResponse(status_code=200, data=data, headers={}, raw=content)
        if operation == "write":
            content = kwargs.get("content") or (payload or {}).get("content")
            if content is None:
                raise UserError(_("No content provided for file write operation"))
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, (list, tuple)):
                if self.system.file_format != "csv":
                    raise UserError(
                        _(
                            "Structured content can only be written when the file format"
                            " is set to CSV."
                        )
                    )
                with file_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=content[0].keys())
                    writer.writeheader()
                    writer.writerows(content)
            else:
                file_path.write_text(str(content), encoding="utf-8")
            return ConnectorResponse(status_code=200, data=True, headers={}, raw=None)
        raise UserError(_("Unsupported file operation: %s") % operation)


class WebhookConnector(BaseConnector):
    """Connector in charge of emitting or consuming webhook events."""

    def execute(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, **kwargs):
        operation = kwargs.get("operation", "emit")
        if operation == "consume":
            event_code = kwargs.get("event_code")
            event = (
                self.system.env["omnisync.webhook.event"].sudo().search(
                    [
                        ("system_id", "=", self.system.id),
                        ("state", "=", "pending"),
                        ("event_code", "=", event_code) if event_code else ("id", "!=", 0),
                    ],
                    order="create_date",
                    limit=1,
                )
            )
            if not event:
                return ConnectorResponse(status_code=204, data=[], headers={}, raw=None)
            event.state = "processed"
            return ConnectorResponse(status_code=200, data=event.payload, headers={}, raw=None)
        url = self.system._build_url(endpoint or "")
        headers = self._prepare_headers()
        response = self.session.post(url, json=payload, headers=headers)
        return ConnectorResponse(
            status_code=response.status_code,
            data=response.json() if response.headers.get("Content-Type", "").startswith("application/json") else response.text,
            headers=dict(response.headers),
            raw=response,
        )


class QueueConnector(BaseConnector):
    """Connector dispatching messages to queues or internal buffers."""

    def execute(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, **kwargs):
        backend = self.system.queue_backend or "internal"
        operation = kwargs.get("operation", "publish")
        topic = kwargs.get("topic") or endpoint or self.system.queue_topic_prefix
        message_payload = payload or {}
        if backend == "internal":
            env = self.system.env["omnisync.queue.message"].sudo()
            if operation == "publish":
                message = env.create(
                    {
                        "system_id": self.system.id,
                        "topic": topic,
                        "payload": message_payload,
                    }
                )
                return ConnectorResponse(status_code=200, data={"message_id": message.id}, headers={}, raw=None)
            if operation == "consume":
                message = env.search(
                    [
                        ("system_id", "=", self.system.id),
                        ("state", "=", "pending"),
                    ],
                    order="create_date",
                    limit=1,
                )
                if not message:
                    return ConnectorResponse(status_code=204, data=[], headers={}, raw=None)
                message.state = "processed"
                return ConnectorResponse(status_code=200, data=message.payload, headers={}, raw=None)
        if backend == "rabbitmq":
            try:
                import pika  # type: ignore  # noqa: WPS433
            except ImportError as exc:  # noqa: BLE001
                raise UserError(_("Install pika to publish messages to RabbitMQ.")) from exc
            credentials = self.system._get_queue_credentials()
            if not credentials.get("url"):
                raise UserError(_("RabbitMQ URL is missing in the authentication profile."))
            parameters = pika.URLParameters(credentials.get("url"))
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.basic_publish(exchange="", routing_key=topic, body=json.dumps(message_payload))
            connection.close()
            return ConnectorResponse(status_code=200, data=True, headers={}, raw=None)
        if backend == "kafka":
            try:
                from kafka import KafkaProducer  # type: ignore  # noqa: WPS433
            except ImportError as exc:  # noqa: BLE001
                raise UserError(_("Install kafka-python to publish messages to Kafka.")) from exc
            credentials = self.system._get_queue_credentials()
            if not credentials.get("bootstrap_servers"):
                raise UserError(_("Kafka bootstrap servers are missing in the authentication profile."))
            producer = KafkaProducer(bootstrap_servers=credentials.get("bootstrap_servers"))
            producer.send(topic, json.dumps(message_payload).encode("utf-8"))
            producer.flush()
            producer.close()
            return ConnectorResponse(status_code=200, data=True, headers={}, raw=None)
        raise UserError(_("Unsupported queue backend: %s") % backend)


class OmniSyncSystem(models.Model):
    """Integration system definitions."""

    _name = "omnisync.system"
    _description = "OmniSync Integration System"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    connector_type = fields.Selection(
        [
            ("rest", "REST / JSON"),
            ("soap", "SOAP / WSDL"),
            ("graphql", "GraphQL"),
            ("database", "Database"),
            ("file", "File System"),
            ("webhook", "Webhook"),
            ("queue", "Message Queue"),
        ],
        required=True,
        default="rest",
    )
    base_url = fields.Char()
    auth_profile_id = fields.Many2one("omnisync.auth.profile", string="Auth Profile")
    extra_headers = fields.Json(string="Extra Headers")
    extra_headers_json = fields.Text(
        string="Extra Headers (JSON)",
        compute="_compute_extra_headers_json",
        inverse="_inverse_extra_headers_json",
        readonly=False,
        help="Pretty printed representation used to edit the JSON headers.",
    )
    default_params = fields.Json(string="Default Parameters")
    default_params_json = fields.Text(
        string="Default Parameters (JSON)",
        compute="_compute_default_params_json",
        inverse="_inverse_default_params_json",
        readonly=False,
        help="Pretty printed representation used to edit the default query parameters.",
    )
    sandbox_mode = fields.Boolean(
        help="Enable sandbox mode to simulate the synchronization without"
        " committing data changes."
    )
    notes = fields.Text()
    last_sync_status = fields.Selection(
        [
            ("idle", "Idle"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        default="idle",
    )
    flow_ids = fields.One2many("omnisync.flow", "system_id", string="Flows")
    graphql_default_query = fields.Text(
        help="Optional default GraphQL query executed when flows do not provide one."
    )
    db_engine = fields.Selection(
        [("postgres", "PostgreSQL"), ("mysql", "MySQL")],
        string="Database Engine",
        default="postgres",
    )
    db_host = fields.Char(string="Database Host")
    db_port = fields.Integer(string="Database Port", default=5432)
    db_name = fields.Char(string="Database Name")
    db_username = fields.Char(string="Database User")
    file_backend = fields.Selection(
        [("local", "Local Storage")],
        string="File Backend",
        default="local",
    )
    file_base_path = fields.Char(
        string="Base Path",
        help="Base directory for local file operations.",
    )
    file_format = fields.Selection(
        [("json", "JSON"), ("csv", "CSV")],
        string="File Format",
        default="json",
    )
    webhook_secret = fields.Char(
        string="Webhook Secret",
        help="Optional secret used to validate inbound webhook payloads.",
    )
    queue_backend = fields.Selection(
        [
            ("internal", "Internal Buffer"),
            ("rabbitmq", "RabbitMQ"),
            ("kafka", "Kafka"),
        ],
        string="Queue Backend",
        default="internal",
    )
    queue_topic_prefix = fields.Char(
        string="Default Topic",
        help="Topic or routing key used when flows do not provide one.",
    )

    @api.onchange("connector_type")
    def _onchange_connector_type(self):
        """Adjust default values when switching connector types."""
        if self.connector_type == "database" and not self.db_port:
            self.db_port = 5432 if self.db_engine == "postgres" else 3306
        if self.connector_type == "file" and not self.file_base_path:
            self.file_base_path = "odoo_sync"

    @api.onchange("db_engine")
    def _onchange_db_engine(self):
        """Ensure the default port follows the selected engine."""
        if self.connector_type == "database":
            self.db_port = 5432 if self.db_engine == "postgres" else 3306

    def _build_url(self, endpoint: str) -> str:
        """Utility to create a full URL from base and endpoint."""
        self.ensure_one()
        if endpoint.startswith("http"):
            return endpoint
        return "%s/%s" % (self.base_url.rstrip("/"), endpoint.lstrip("/"))

    def get_connector(self) -> BaseConnector:
        """Return the connector implementation for this system."""
        self.ensure_one()
        if self.connector_type == "rest":
            return RestConnector(self)
        if self.connector_type == "soap":
            return SoapConnector(self)
        if self.connector_type == "graphql":
            return GraphQLConnector(self)
        if self.connector_type == "database":
            return DatabaseConnector(self)
        if self.connector_type == "file":
            return FileConnector(self)
        if self.connector_type == "webhook":
            return WebhookConnector(self)
        if self.connector_type == "queue":
            return QueueConnector(self)
        raise UserError(_("Unsupported connector type: %s") % self.connector_type)

    def execute(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, **kwargs):
        """Execute a request through the configured connector."""
        self.ensure_one()
        connector = self.get_connector()
        response = connector.execute(endpoint, payload=payload, **kwargs)
        self._log_activity(response)
        if response.status_code >= 400:
            self.last_sync_status = "failed"
            raise UserError(
                _("Request to %s failed with status %s")
                % (self.name, response.status_code)
            )
        self.last_sync_status = "success"
        return response

    def _log_activity(self, response: ConnectorResponse):
        """Create a message post summarizing the connector response."""
        self.ensure_one()
        message = _(
            "Executed sync call with status %(status)s and headers %(headers)s"
        ) % {"status": response.status_code, "headers": response.headers}
        if response.status_code >= 400:
            message = _(
                "Sync call failed with status %(status)s. Response preview: %(preview)s"
            ) % {
                "status": response.status_code,
                "preview": str(response.data)[:500],
            }
        self.message_post(body=message)

    def action_test_connection(self):
        """Test the connection using a lightweight request."""
        for system in self:
            try:
                if system.connector_type == "database":
                    response = system.execute(endpoint="SELECT 1", operation="read")
                elif system.connector_type == "file":
                    response = system.execute(endpoint="", operation="read")
                elif system.connector_type == "queue":
                    response = system.execute(endpoint="test", operation="publish", payload={"ping": True})
                elif system.connector_type == "webhook":
                    response = system.execute(endpoint="", payload={"ping": True})
                else:
                    response = system.execute(endpoint="", payload=None)
            except Exception as exc:  # noqa: BLE001
                raise UserError(
                    _("Connection test for %s failed: %s") % (system.name, exc)
                ) from exc
            if response.status_code >= 400:
                raise UserError(
                    _("Connection test for %s returned status %s")
                    % (system.name, response.status_code)
                )
        return True

    def export_configuration(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the system."""
        self.ensure_one()
        return {
            "name": self.name,
            "connector_type": self.connector_type,
            "base_url": self.base_url,
            "extra_headers": self.extra_headers or {},
            "default_params": self.default_params or {},
            "sandbox_mode": self.sandbox_mode,
            "notes": self.notes,
            "graphql_default_query": self.graphql_default_query,
            "database": {
                "engine": self.db_engine,
                "host": self.db_host,
                "port": self.db_port,
                "database": self.db_name,
                "username": self.db_username,
            },
            "file": {
                "backend": self.file_backend,
                "base_path": self.file_base_path,
                "format": self.file_format,
            },
            "queue": {
                "backend": self.queue_backend,
                "topic": self.queue_topic_prefix,
            },
        }

    @api.depends("extra_headers")
    def _compute_extra_headers_json(self):
        for record in self:
            record.extra_headers_json = format_json_value(record.extra_headers)

    @api.depends("default_params")
    def _compute_default_params_json(self):
        for record in self:
            record.default_params_json = format_json_value(record.default_params)

    def _inverse_extra_headers_json(self):
        for record in self:
            try:
                record.extra_headers = parse_json_text(record.extra_headers_json)
            except ValueError as error:
                raise ValidationError(
                    _("The extra headers value must be valid JSON.\n%(error)s")
                    % {"error": error}
                ) from error

    def _inverse_default_params_json(self):
        for record in self:
            try:
                record.default_params = parse_json_text(record.default_params_json)
            except ValueError as error:
                raise ValidationError(
                    _("The default parameters value must be valid JSON.\n%(error)s")
                    % {"error": error}
                ) from error

    def _get_auth_payload(self) -> Dict[str, Any]:
        """Return decrypted payload from the related authentication profile."""
        self.ensure_one()
        if not self.auth_profile_id:
            return {}
        return self.auth_profile_id._get_secret_payload()

    def _get_database_parameters(self) -> Dict[str, Any]:
        """Assemble database connection parameters from system fields and secrets."""
        self.ensure_one()
        payload = self._get_auth_payload()
        return {
            "engine": self.db_engine,
            "host": self.db_host or payload.get("host"),
            "port": self.db_port or payload.get("port"),
            "database": self.db_name or payload.get("database"),
            "username": self.db_username or payload.get("username"),
            "password": payload.get("password"),
        }

    def _get_queue_credentials(self) -> Dict[str, Any]:
        """Return queue credentials sourced from the authentication profile."""
        self.ensure_one()
        payload = self._get_auth_payload()
        return {
            "url": payload.get("queue_url"),
            "bootstrap_servers": payload.get("bootstrap_servers"),
            "username": payload.get("username"),
            "password": payload.get("password"),
        }
