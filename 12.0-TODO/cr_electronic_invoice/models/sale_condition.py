# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SaleConditions(models.Model):
    _name = "sale.conditions"

    active = fields.Boolean(string="Active", required=False, default=True)
    sequence = fields.Char(string="Sequence", required=False, )
    name = fields.Char(string="Name", required=False, )
    notes = fields.Text(string="Notes", required=False, )
