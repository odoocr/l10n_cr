from odoo import models, fields, api


class ProductCategory(models.Model):
    _inherit = "product.category"

    # ==============================================================================================
    #                                          PRODUCT CATEGORIES
    # ==============================================================================================

    economic_activity_id = fields.Many2one(
        comodel_name="economic.activity",
        string="Economic Activity",
        help='Economic activity code from Ministerio de Hacienda'
    )

    cabys_code = fields.Char(
        string="CAByS Code",
        help='CAByS code from Ministerio de Hacienda'
    )
