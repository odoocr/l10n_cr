# -*- coding: utf-8 -*-
from odoo import models, fields, api


class InvoiceTaxElectronic(models.Model):
    _inherit = "account.tax"

    tax_code = fields.Char(string=u"Código de impuesto", required=False,)
