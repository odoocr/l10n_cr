
from odoo import models, fields


class PaymentMethods(models.Model):
    _name = "payment.methods"

    active = fields.Boolean(default=True)
    sequence = fields.Char()
    name = fields.Char()
    notes = fields.Text()


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    sale_conditions_id = fields.Many2one("sale.conditions")
