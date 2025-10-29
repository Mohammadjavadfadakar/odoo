# -*- coding: utf-8 -*-
import os
import uuid
import subprocess
import tempfile

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestConnectorCore(TransactionCase):
    def setUp(self):
        super().setUp()
        self.profile = self.env["connector.profile"].create(
            {
                "name": "Azure Storage",
                "code": "azure_storage",
                "system_type": "cloud",
                "auth_mode": "api_key",
                "base_url": "https://api.example.com",
                "headers_template": {"Authorization": "Bearer secret"},
            }
        )
        self.endpoint = self.env["connector.endpoint"].create(
            {
                "name": "List Accounts",
                "profile_id": self.profile.id,
                "http_method": "get",
                "route": "/accounts",
                "pagination_mode": "page",
                "request_params": {"query": "active"},
            }
        )
        self.mapping = self.env["connector.mapping"].create(
            {
                "name": "Account Import",
                "profile_id": self.profile.id,
                "endpoint_id": self.endpoint.id,
                "direction": "inbound",
                "model_id": self.env.ref("base.model_res_partner").id,
                "field_mapping": {
                    "name": "display_name",
                    "email": {"source": "contact.email", "default": "unknown@example.com"},
                    "phone": {"source": "contact.phone", "transform": "to_upper"},
                },
            }
        )

    def test_endpoint_builds_request(self):
        request = self.endpoint.build_request(
            payload_context={"name": "Azure"},
            pagination_state={"page": 2, "limit": 50},
        )
        self.assertEqual(request["method"], "get")
        self.assertIn("https://api.example.com/accounts", request["url"])
        self.assertEqual(request["headers"].get("Authorization"), "Bearer secret")
        self.assertEqual(request["params"]["page"], 2)
        self.assertEqual(request["params"]["limit"], 50)

    def test_mapping_transforms_payload(self):
        payload = {
            "display_name": "Contoso",
            "contact": {"email": "billing@contoso.com", "phone": "555-100"},
        }
        values = self.mapping._map_payload(payload)
        self.assertEqual(values["name"], "Contoso")
        self.assertEqual(values["email"], "billing@contoso.com")
        self.assertEqual(values["phone"], "555-100".upper())


class TestModuleInstall(TransactionCase):
    @tagged("post_install", "-at_install")
    def test_install_command(self):
        module_name = "custom_connector_hub"
        base_db_name = self.env.cr.dbname
        target_db = f"{base_db_name}_cli_{uuid.uuid4().hex[:6]}"
        cnx_info = self.env.cr._cnx.info
        db_host = cnx_info.host or ""
        db_port = cnx_info.port or ""
        db_user = cnx_info.user or ""
        db_password = getattr(cnx_info, "password", "") or ""
        if db_host and not db_password:
            db_password = os.environ.get("PGPASSWORD", "odoo")
        with tempfile.NamedTemporaryFile(delete=False) as logfile:
            logfile_path = logfile.name
        try:
            command = [
                "python3",
                os.path.join(os.getcwd(), "odoo-bin"),
                "-d",
                target_db,
                "-i",
                module_name,
                "--db_host",
                db_host,
                "--db_port",
                str(db_port or ""),
                "--db_user",
                db_user,
            ]
            if db_password:
                command.extend(["--db_password", db_password])
            command.extend(
                [
                    "--test-tags",
                    "-",
                    "--stop-after-init",
                    "--no-http",
                    "--http-port",
                    "0",
                    "--log-level",
                    "warn",
                    "--logfile",
                    logfile_path,
                ]
            )
            env = os.environ.copy()
            env.setdefault("ODOO_RC", os.path.join(os.getcwd(), "odoo.conf"))
            if db_password:
                env.setdefault("PGPASSWORD", db_password)
            dropdb_cmd = [
                "dropdb",
                target_db,
            ]
            dropdb_env = env.copy()
            if db_host:
                dropdb_env["PGHOST"] = db_host
            if db_port:
                dropdb_env["PGPORT"] = str(db_port)
            if db_user:
                dropdb_env["PGUSER"] = db_user
            subprocess.run(dropdb_cmd, env=dropdb_env, capture_output=True, check=False)
            process = subprocess.run(command, env=env, capture_output=True, check=False)
            self.assertEqual(process.returncode, 0, msg=process.stderr.decode())
        finally:
            if os.path.exists(logfile_path):
                with open(logfile_path, "r", encoding="utf-8", errors="ignore") as handle:
                    handle.read()
                os.unlink(logfile_path)
            dropdb_cmd = [
                "dropdb",
                target_db,
            ]
            subprocess.run(dropdb_cmd, env=dropdb_env, capture_output=True, check=False)
