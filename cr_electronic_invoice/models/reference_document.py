# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ReferenceDocument(models.Model):
    _name = "reference.document"

    active = fields.Boolean(string="Activo", required=False, default=True)
    code = fields.Char(string="Código", required=False, )
    name = fields.Char(string="Nombre", required=False, )
