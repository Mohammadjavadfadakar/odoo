# -*- coding: utf-8 -*-
"""Tests for the OmniSync health monitoring subsystem."""

from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.omnisync.models.system import ConnectorResponse


class TestHealthChecks(TransactionCase):
    """Ensure health checks execute and persist results correctly."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.system = cls.env["omnisync.system"].create(
            {
                "name": "Health System",
                "connector_type": "rest",
                "base_url": "https://example.com/api",
                "company_id": cls.company.id,
            }
        )
        cls.flow = cls.env["omnisync.flow"].create(
            {
                "name": "Health Flow",
                "system_id": cls.system.id,
                "direction": "inbound",
                "model_id": cls.env["ir.model"].search([("model", "=", "res.partner")], limit=1).id,
                "company_id": cls.company.id,
            }
        )
        cls.mapping = cls.env["omnisync.mapping"].create(
            {
                "name": "Health Mapping",
                "flow_id": cls.flow.id,
                "target_model_id": cls.flow.model_id.id,
                "company_id": cls.company.id,
            }
        )
        cls.env["omnisync.mapping.line"].create(
            {
                "mapping_id": cls.mapping.id,
                "source_field": "payload.name",
                "target_field_name": "name",
            }
        )

    def test_connector_health_check_success(self):
        check = self.env["omnisync.health.check"].create(
            {
                "name": "Connector Ping",
                "company_id": self.company.id,
                "system_id": self.system.id,
                "check_type": "connector",
            }
        )
        with patch.object(
            type(self.system),
            "execute",
            return_value=ConnectorResponse(200, {}, {}, None),
        ):
            check._run_health_check_now()
        self.assertEqual(check.last_status, "success")
        self.assertTrue(check.log_ids)

    def test_flow_preview_health_check(self):
        check = self.env["omnisync.health.check"].create(
            {
                "name": "Preview",
                "company_id": self.company.id,
                "system_id": self.system.id,
                "flow_id": self.flow.id,
                "check_type": "flow_preview",
            }
        )
        with patch.object(type(self.flow), "run_preview", return_value=[{"foo": 1}]):
            status = check._run_health_check_now()
        self.assertEqual(status, "success")

    def test_cron_invokes_health_checks(self):
        check = self.env["omnisync.health.check"].create(
            {
                "name": "Cron Ping",
                "company_id": self.company.id,
                "system_id": self.system.id,
                "check_type": "connector",
            }
        )
        with patch.object(type(check), "_run_health_check_now", autospec=True) as mocked:
            self.env["omnisync.health.check"].cron_run_active_checks()
            self.assertTrue(mocked.called)
