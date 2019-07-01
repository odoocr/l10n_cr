# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class Resolution(models.Model):
    _name = "resolution"

    active = fields.Boolean(string="Activo", required=False, default=True)
    name = fields.Char(string="Nombre", required=False, )
    date_resolution = fields.Date(
        string="Fecha de resolución", required=False, )
