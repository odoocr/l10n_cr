from odoo import models, fields


class PaymentMethods(models.Model):
    _name = "payment.methods"

    # ==============================================================================================
    #                                          PAYMENT METHODS
    # ==============================================================================================

    active = fields.Boolean(
        default=True
    )
    sequence = fields.Char()
    name = fields.Char()
    notes = fields.Text()
