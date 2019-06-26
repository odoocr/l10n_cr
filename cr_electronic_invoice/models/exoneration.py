# -*- coding: utf-8 -*-
from odoo import models, fields


class Exoneration(models.Model):
    _name = "account.fiscal.position"
    _inherit = ['account.fiscal.position']
    has_exoneration = fields.Boolean(string = "Posee exoneración", required=True)
    type_exoneration = fields.Many2one(
        comodel_name="aut.ex", string="Tipo Autorizacion", required=True, )
    exoneration_number = fields.Char(
        string="Número de exoneración", required=False, )
    date = fields.Date(string="Fecha", required=False, )
