# -*- coding: utf-8 -*-
"""Tests covering the OmniSync mapping engine."""

from odoo.tests.common import TransactionCase


class TestMappingEngine(TransactionCase):
    """Validate mapping transforms and identifier extraction."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        system_model = cls.env["omnisync.system"]
        flow_model = cls.env["omnisync.flow"]
        mapping_model = cls.env["omnisync.mapping"]

        cls.system = system_model.create(
            {
                "name": "Test REST",
                "connector_type": "rest",
                "base_url": "https://example.com/api",
                "company_id": cls.company.id,
            }
        )
        cls.flow = flow_model.create(
            {
                "name": "Test Flow",
                "system_id": cls.system.id,
                "direction": "inbound",
                "model_id": cls.env["ir.model"].search([("model", "=", "res.partner")], limit=1).id,
                "company_id": cls.company.id,
            }
        )
        cls.mapping = mapping_model.create(
            {
                "name": "Partner Mapping",
                "flow_id": cls.flow.id,
                "target_model_id": cls.flow.model_id.id,
                "company_id": cls.company.id,
            }
        )
        cls.line_trim_upper = cls.env["omnisync.mapping.line"].create(
            {
                "mapping_id": cls.mapping.id,
                "source_field": "payload.name",
                "target_field_name": "name",
                "transform_chain": "trim,upper",
            }
        )
        cls.line_format = cls.env["omnisync.mapping.line"].create(
            {
                "mapping_id": cls.mapping.id,
                "source_field": "payload.sku",
                "target_field_name": "ref",
                "default_value": "SKU-{value}",
                "transform_chain": "format",
            }
        )
        cls.line_identifier = cls.env["omnisync.mapping.line"].create(
            {
                "mapping_id": cls.mapping.id,
                "source_field": "payload.external_id",
                "target_field_name": "x_studio_external_id",
                "is_external_identifier": True,
            }
        )

    def test_transform_chain_applies_trim_and_upper(self):
        payload = {"payload": {"name": "  acme inc  "}}
        values = self.mapping.apply(payload)
        self.assertEqual(values.get("name"), "ACME INC")

    def test_format_transform_uses_default_template(self):
        payload = {"payload": {"sku": "123"}}
        values = self.mapping.apply(payload)
        self.assertEqual(values.get("ref"), "SKU-123")

    def test_extract_external_identifier_prefers_payload(self):
        payload = {"payload": {"external_id": "WP-42"}}
        mapped = self.mapping.apply(payload)
        identifier = self.mapping.extract_external_identifier(payload.get("payload"), mapped)
        self.assertEqual(identifier, "WP-42")
