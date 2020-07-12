# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class EconomicActivity(models.Model):
    _name = "economic.activity"
    _description = 'Economic activities listed by Ministerio de Hacienda'
    _order = "code"


    active = fields.Boolean(string="Active", default=True)
    code = fields.Char(string="Code", )
    name = fields.Char(string="Name", )
    description = fields.Char(string="Description", )

    sale_type = fields.Selection(
        string='Sale Type',
        selection=[('goods', 'Goods'), ('services', 'Services')],
        default = 'goods',
        required=True
    )
    