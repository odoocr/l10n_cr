# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class UoM(models.Model):
    _inherit = "product.uom"
    code = fields.Char(string="Código", required=False, )
