# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AutEx(models.Model):
    _name = "aut.ex"

    active = fields.Boolean(string="Activo", required=False, default=True)
    code = fields.Char(string="Código", required=False, )
    name = fields.Char(string="Nombre", required=False, )
