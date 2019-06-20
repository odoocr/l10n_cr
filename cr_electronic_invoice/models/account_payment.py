# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PaymentMethods(models.Model):
    _name = "payment.methods"

    active = fields.Boolean(string="Activo", required=False, default=True)
    sequence = fields.Char(string="Secuencia", required=False, )
    name = fields.Char(string="Nombre", required=False, )
    notes = fields.Text(string="Notas", required=False, )


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"
    sale_conditions_id = fields.Many2one(
        comodel_name="sale.conditions", string="Condiciones de venta")
