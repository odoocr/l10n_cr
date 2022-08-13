from unittest.result import failfast
from odoo import models, fields, api, _

class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"

    tax_code = fields.Char(string="Tax Code")
    iva_tax_desc = fields.Char(string="VAT Tax Rate", default='N/A')
    iva_tax_code = fields.Char(string="VAT Rate Code", default='N/A')
    non_tax_deductible = fields.Boolean(string='Indicates if this tax is no deductible for Rent and VAT',)
