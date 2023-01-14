from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # === URL fields === #

    url_base_yo_contribuyo = fields.Char(
        related="company_id.url_base_yo_contribuyo",
        readonly=False
    )
    url_base = fields.Char(
        related="company_id.url_base",
    )

    # === Boolean fields === #

    get_tributary_information = fields.Boolean(
        related="company_id.get_tributary_information",
        readonly=False
    )
    get_yo_contribuyo_information = fields.Boolean(
        related="company_id.get_yo_contribuyo_information",
        readonly=False
    )

    # === Access fields === #

    usuario_yo_contribuyo = fields.Char(
        related="company_id.usuario_yo_contribuyo",
        readonly=False
    )
    token_yo_contribuyo = fields.Char(
        related="company_id.token_yo_contribuyo",
        readonly=False
    )

    # === API Answer fields === #

    ultima_respuesta_yo_contribuyo = fields.Text(
        related="company_id.ultima_respuesta_yo_contribuyo"
    )
    ultima_respuesta = fields.Text(
        related="company_id.ultima_respuesta"
    )
