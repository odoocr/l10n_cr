# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SaleConditions(models.Model):
    _name = "sale.conditions"

    active = fields.Boolean(string="Activo", required=False, default=True)
    sequence = fields.Char(string="Secuencia", required=False, )
    name = fields.Char(string="Nombre", required=False, )
    notes = fields.Text(string="Notas", required=False, )
