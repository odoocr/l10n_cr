
from odoo import models, fields


class AutEx(models.Model):
    _name = "aut.ex"

    active = fields.Boolean(default=True)
    code = fields.Char()
    name = fields.Char()
