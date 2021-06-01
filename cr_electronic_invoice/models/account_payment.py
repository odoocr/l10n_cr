# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PaymentMethods(models.Model):
    _name = "payment.methods"

    active = fields.Boolean(string="Active", required=False, default=True)
    sequence = fields.Char(string="Sequence", required=False, )
    name = fields.Char(string="Name", required=False, )
    notes = fields.Text(string="Notes", required=False, )


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"
    sale_conditions_id = fields.Many2one(
        "sale.conditions", string="Condiciones de venta")
