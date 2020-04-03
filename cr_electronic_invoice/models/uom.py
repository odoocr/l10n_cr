# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class UoM(models.Model):
    _inherit = "uom.uom"
    code = fields.Char(string="Code", required=False, )


class UoMCategory(models.Model):
    _inherit = "uom.category"
    measure_type = fields.Selection(selection_add=[('area', 'Area'), 
                                                   ('services', 'Services'), 
                                                   ('rent', 'Rent'), ])
