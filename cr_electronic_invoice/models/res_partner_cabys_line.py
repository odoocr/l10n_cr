from odoo import models, fields


class AutEx(models.Model):
    _name = "res.partner.cabys.line"
    _description = "Allowed CABYS"

    # ==============================================================================================
    #                                          Allowed  CABYS
    # ==============================================================================================

    parent_id = fields.Many2one(
        comodel_name='res.partner'
    )
    name = fields.Char(
        string="CABYS Code"
    )
