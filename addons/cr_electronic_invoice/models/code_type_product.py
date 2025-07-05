from odoo import models, fields


class CodeTypeProduct(models.Model):
    _name = "code.type.product"

    # ==============================================================================================
    #                                          PRODUCT TYPE
    # ==============================================================================================

    code = fields.Char()
    name = fields.Char()
