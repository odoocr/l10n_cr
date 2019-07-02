# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class EconomicActivity(models.Model):
    _name = "economic_activity"

    active = fields.Boolean(string="Activo", required=False, default=True)
    code = fields.Char(string="Código", required=False, )
    name = fields.Char(string="Nombre", required=False, )
    description = fields.Char(string="Descripción", required=False, )
