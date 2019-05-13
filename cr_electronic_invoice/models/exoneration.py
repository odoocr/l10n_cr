# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class Exoneration(models.Model):
    _name = "exoneration"

    name = fields.Char(string="Nombre", required=False, )
    type = fields.Many2one(comodel_name="aut.ex", string="Tipo Autorizacion/Exoneracion", required=True, )
    exoneration_number = fields.Char(string="Número de exoneración", required=False, )
    name_institution = fields.Char(string="Nombre de institución", required=False, )
    date = fields.Date(string="Fecha", required=False, )
    percentage_exoneration = fields.Float(string="Porcentaje de exoneración", required=False, )
