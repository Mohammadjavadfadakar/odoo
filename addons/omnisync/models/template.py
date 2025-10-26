# -*- coding: utf-8 -*-
"""Template pack models for OmniSync."""

from odoo import _, fields, models


class OmniSyncTemplatePack(models.Model):
    """Reusable template packs that bootstrap OmniSync configurations."""

    _name = "omnisync.template.pack"
    _description = "OmniSync Template Pack"
    _order = "name"

    name = fields.Char(required=True)
    key = fields.Char(required=True, index=True)
    description = fields.Text()
    category = fields.Selection(
        [
            ("commerce", "Commerce"),
            ("accounting", "Accounting"),
            ("cms", "CMS"),
        ],
        default="commerce",
    )
    payload = fields.Text(
        help="JSON or YAML payload containing serialized systems and flows.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    def action_apply(self):
        """Launch the template apply wizard."""
        self.ensure_one()
        wizard = self.env["omnisync.template.apply.wizard"].create(
            {"template_id": self.id}
        )
        return wizard.action_apply()
