# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class EconomicActivity(models.Model):
    _name = "economic.activity"

    active = fields.Boolean(string="Activo", default=True)
    code = fields.Char(string="Código", )
    name = fields.Char(string="Nombre", )
    description = fields.Char(string="Descripción", )
