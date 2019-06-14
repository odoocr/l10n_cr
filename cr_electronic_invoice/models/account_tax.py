from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class IvaCodeType(models.Model):
    _inherit = "account.tax"

    iva_tax_desc = fields.Char(string="Tarifa IVA", default='N/A', required=False, )
    iva_tax_code = fields.Char(string="Código Tarifa IVA", default='N/A', required=False, )
