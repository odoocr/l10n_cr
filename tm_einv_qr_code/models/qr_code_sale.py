# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.http import request
from . import qr_code_base


class QRCodeSale(models.Model):
    _inherit = 'sale.order'

    qr_image = fields.Binary("Código QR", compute='_generate_qr_code')
    qr_in_report = fields.Boolean('Mostrar QR en Reporte')

    @api.one
    def _generate_qr_code(self):
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        self.qr_image = qr_code_base.generate_qr_code(base_url)