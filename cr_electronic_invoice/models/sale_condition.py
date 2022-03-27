
from odoo import models, fields


class SaleConditions(models.Model):
    _name = "sale.conditions"

    active = fields.Boolean(default=True)
    code = fields.Char()
    sequence = fields.Char()
    name = fields.Char()
    notes = fields.Text()
