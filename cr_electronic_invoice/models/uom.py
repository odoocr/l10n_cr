from odoo import models, fields, api


class ProductUom(models.Model):
    _inherit = "uom.uom"
    code = fields.Char(string="Código", required=False, )
