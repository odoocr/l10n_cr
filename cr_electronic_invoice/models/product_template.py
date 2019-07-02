# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class ProductElectronic(models.Model):
    _inherit = "product.template"

    @api.model
    def _default_code_type_id(self):
        code_type_id = self.env['code.type.product'].search(
            [('code', '=', '04')], limit=1)
        return code_type_id or False

    commercial_measurement = fields.Char(
        string="Unidad de Medida Comercial", required=False, )
    code_type_id = fields.Many2one(comodel_name="code.type.product", string="Tipo de código", required=False,
                                   default=_default_code_type_id)

    tariff_head = fields.Char(string="Partida arancelaria para factura"
                                     " de exportación",
                              required=False, )
