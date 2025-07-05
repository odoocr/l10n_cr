from odoo import fields, models

import logging
_logger = logging.getLogger(__name__)


class POSPaymentMethods(models.Model):
    _inherit = 'pos.payment.method'
    _description = "Métodos de pago POS"

    sequence = fields.Char()
