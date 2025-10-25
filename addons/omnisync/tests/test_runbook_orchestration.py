# -*- coding: utf-8 -*-
"""Tests for OmniSync runbook orchestration."""

from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.omnisync.models.flow import OmniSyncFlow


class TestRunbookOrchestration(TransactionCase):
    """Validate runbook execution sequences and notifications."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        system = cls.env["omnisync.system"].create(
            {
                "name": "Runbook System",
                "connector_type": "rest",
                "base_url": "https://example.com/api",
                "company_id": cls.company.id,
            }
        )
        model_id = cls.env["ir.model"].search([("model", "=", "res.partner")], limit=1).id
        cls.flow_preview = cls.env["omnisync.flow"].create(
            {
                "name": "Preview Flow",
                "system_id": system.id,
                "direction": "inbound",
                "model_id": model_id,
                "company_id": cls.company.id,
            }
        )
        cls.flow_live = cls.env["omnisync.flow"].create(
            {
                "name": "Live Flow",
                "system_id": system.id,
                "direction": "outbound",
                "model_id": model_id,
                "company_id": cls.company.id,
            }
        )

    def setUp(self):
        super().setUp()
        self.runbook = self.env["omnisync.runbook"].create(
            {
                "name": "Master Runbook",
                "company_id": self.company.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "flow_id": self.flow_preview.id,
                            "preview_mode": True,
                            "sequence": 5,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "flow_id": self.flow_live.id,
                            "preview_mode": False,
                            "sequence": 10,
                        },
                    ),
                ],
            }
        )

    def test_runbook_queues_flows_in_correct_modes(self):
        contexts = []

        def _fake_action_sync(self):
            contexts.append(bool(self.env.context.get("omnisync_preview")))

        with patch.object(OmniSyncFlow, "action_sync_now", autospec=True, side_effect=_fake_action_sync):
            count = self.runbook._execute_runbook_now([])
        self.assertEqual(count, 2)
        self.assertEqual(contexts, [True, False])

    def test_runbook_notify_failure_posts_message(self):
        user = self.env.ref("base.user_admin")
        self.runbook.notify_user_id = user
        initial_count = len(self.runbook.message_ids)
        self.runbook._notify_failure("Simulated failure")
        self.assertGreater(len(self.runbook.message_ids), initial_count)
