from odoo import models, fields, api, _
from odoo.exceptions import UserError


class IvaCodeType(models.Model):
    _inherit = "account.tax"

    tax_code = fields.Char(string="Tax Code")
    iva_tax_desc = fields.Char(string="VAT Tax Rate", default='N/A')
    iva_tax_code = fields.Char(string="VAT Rate Code", default='N/A')
    has_exoneration = fields.Boolean(string="Has Exoneration")
    percentage_exoneration = fields.Integer(string="Percentage of VAT Exoneration")
    tax_root = fields.Many2one("account.tax", string="Parent Tax")
    non_tax_deductible = fields.Boolean(string='Indicates if this tax is no deductible for Rent and VAT',)

    @api.onchange('percentage_exoneration')
    def _onchange_percentage_exoneration(self):
        self.tax_compute_exoneration()

    @api.onchange('tax_root')
    def _onchange_tax_root(self):
        self.tax_compute_exoneration()

    def tax_compute_exoneration(self):
        if self.percentage_exoneration <= 13:
            if self.tax_root:
                self.amount = self.tax_root.amount - self.percentage_exoneration
        else:
            raise UserError(_('El porcentaje no puede ser mayor a 13'))
