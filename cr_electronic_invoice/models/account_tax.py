from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class IvaCodeType(models.Model):
    _inherit = "account.tax"

    tax_code = fields.Char(string="Código de impuesto", required=False, )
    iva_tax_desc = fields.Char(
        string="Tarifa IVA", default='N/A', required=False, )
    iva_tax_code = fields.Char(
        string="Código Tarifa IVA", default='N/A', required=False, )
    has_exoneration = fields.Boolean(string="Impuesto Exonerado", required=False)
    percentage_exoneration = fields.Integer(string="Porcentaje de Exoneracion", required=False)
    tax_root = fields.Many2one(
        comodel_name="account.tax", string="Impuesto Padre", required=False, )

    @api.onchange('percentage_exoneration')
    def _onchange_percentage_exoneration(self):
        self.tax_compute_exoneration()

    @api.onchange('tax_root')
    def _onchange_tax_root(self):
        self.tax_compute_exoneration()

    def tax_compute_exoneration(self):
        if self.percentage_exoneration <= 100:
            if self.tax_root:
                _tax_amount = self.tax_root.amount / 100
                _procentage = self.percentage_exoneration / 100
                self.amount = (_tax_amount * (1 - _procentage)) * 100
        else:
            raise UserError(
                'El porcentaje no puede ser mayor a 100')



