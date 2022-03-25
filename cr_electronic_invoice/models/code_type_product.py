
from odoo import models, fields


class CodeTypeProduct(models.Model):
    _name = "code.type.product"

    code = fields.Char()
    name = fields.Char()
