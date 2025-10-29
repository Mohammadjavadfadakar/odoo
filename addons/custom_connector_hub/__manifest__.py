# -*- coding: utf-8 -*-
{
    "name": "Custom Connector Hub",
    "summary": "Framework to integrate third-party systems with Odoo using configurable connectors, mappings, and validation rules.",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "website": "https://www.odoo.com",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/connector_sequences.xml",
        "data/connector_menus.xml",
        "views/connector_dashboard_views.xml",
        "views/connector_configuration_views.xml",
    ],
    "demo": [],
    "installable": True,
    "application": True,
    "assets": {
        "web.assets_backend": [
            "custom_connector_hub/static/src/js/connector_dashboard.esm.js",
            "custom_connector_hub/static/src/scss/connector_dashboard.scss",
        ],
    },
}
