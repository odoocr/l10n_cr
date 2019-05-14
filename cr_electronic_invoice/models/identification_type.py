from odoo import models, fields, api


class IdentificationType(models.Model):
    _name = "identification.type"

    code = fields.Char(string="Código", required=False,)
    name = fields.Char(string="Nombre", required=False,)
    notes = fields.Text(string="Notas", required=False,)
