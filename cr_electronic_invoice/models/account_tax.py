import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class IvaCodeType(models.Model):
    _inherit = "account.tax"

    tax_code = fields.Char(string="Tax Code", required=False, )
    iva_tax_desc = fields.Char(string="VAT Tax Rate", default='N/A', required=False, )
    iva_tax_code = fields.Char(string="VAT Rate Code", default='N/A', required=False, )
    has_exoneration = fields.Boolean(string="Has Exoneration", required=False)
    percentage_exoneration = fields.Integer(string="Percentage of VAT Exoneration", required=False)
    tax_root = fields.Many2one("account.tax", string="Parent Tax", required=False, )
    non_tax_deductible = fields.Boolean(string='Indicates if this tax is no deductible for Rent and VAT',)

    @api.onchange('percentage_exoneration')
    def _onchange_percentage_exoneration(self):
        self.tax_compute_exoneration()

    @api.onchange('tax_root')
    def _onchange_tax_root(self):
        self.tax_compute_exoneration()

    def tax_compute_exoneration(self):
        if datetime.datetime.today() < datetime.datetime.strptime('2020-07-02', '%Y-%m-%d'):
            if self.percentage_exoneration <= 100:
                if self.tax_root:
                    _tax_amount = self.tax_root.amount / 100
                    _procentage = self.percentage_exoneration / 100
                    self.amount = (_tax_amount * (1 - _procentage)) * 100
            else:
                raise UserError('El porcentaje no puede ser mayor a 100')
        else:
            if self.percentage_exoneration <= 13:
                if self.tax_root:
                    self.amount = self.tax_root.amount - self.percentage_exoneration
            else:
                raise UserError('El porcentaje no puede ser mayor a 13')
