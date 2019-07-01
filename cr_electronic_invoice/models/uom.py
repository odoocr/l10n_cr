# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class UoM(models.Model):
    _inherit = "product.uom"
    code = fields.Char(string="Código", required=False, )


#class UoMCategory(models.Model):
#    _inherit = "product.uom.categ"
#    measure_type = fields.Selection(
#        selection_add=[('area', 'Area'), ('services', 'Services'), ('rent', 'Rent'), ])
