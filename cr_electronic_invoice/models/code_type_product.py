# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CodeTypeProduct(models.Model):
    _name = "code.type.product"

    code = fields.Char(string=u"Código", required=False,)
    name = fields.Char(string=u"Nombre", required=False,)
