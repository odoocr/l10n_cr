
from odoo import models, fields


class UoM(models.Model):
    _inherit = "uom.uom"
    code = fields.Char()
