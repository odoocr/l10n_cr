from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero, float_round
from odoo.exceptions import ValidationError, UserError
from odoo.http import request
from odoo.osv.expression import AND

import logging
_logger = logging.getLogger(__name__)


class POSPaymentMethods(models.Model):
    _inherit = 'pos.payment.method'
    _description = "Métodos de pago POS"

    sequence = fields.Char(string="Sequence", required=False,  index=False)