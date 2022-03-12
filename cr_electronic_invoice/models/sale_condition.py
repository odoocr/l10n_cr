
from odoo import models, fields


class SaleConditions(models.Model):
    _name = "sale.conditions"

    active = fields.Boolean(help='Set sale contitions active or inactive', default=True)
    code = fields.Char(help='Sale contitions code', required=True)
    sequence = fields.Char(help='Sale conditions sequence', required=True)
    name = fields.Char(help='Sale conditions name', required=True)
    notes = fields.Text(help='Sale conditions notes')
