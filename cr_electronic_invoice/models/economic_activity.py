
from odoo import models, fields


class EconomicActivity(models.Model):
    _name = "economic.activity"
    _description = 'Economic activities listed by Ministerio de Hacienda'
    _order = "code"

    active = fields.Boolean(default=True)
    code = fields.Char()
    name = fields.Char()
    description = fields.Char()

    sale_type = fields.Selection(selection=[('goods', 'Goods'), ('services', 'Services')],
                                 default='goods',
                                 required=True)
