from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    # === URL fields === #

    url_base = fields.Char(
        string="URL Base",
        help="URL Base of the END POINT",
        default="https://api.hacienda.go.cr/fe/ae?"
    )
    url_base_yo_contribuyo = fields.Char(
        string="URL Base Yo Contribuyo",
        help="URL Base Yo Contribuyo",
        default="https://api.hacienda.go.cr/fe/mifacturacorreo?"
    )

    # === Boolean fields === #

    get_tributary_information = fields.Boolean(default=True)
    get_yo_contribuyo_information = fields.Boolean(default=True)

    # === Access fields === #

    usuario_yo_contribuyo = fields.Char(
        string="Yo Contribuyo User",
        help="Yo Contribuyo Developer Identification"
    )
    token_yo_contribuyo = fields.Char(
        string="Yo Contribuyo Token",
        help="Yo Contribuyo Token provided by Ministerio de Hacienda"
    )

    # === API Answer fields === #

    ultima_respuesta_yo_contribuyo = fields.Text(
        string="Latest API response",
        help="Last API Response, this allows debugging errors if they exist"
    )
    ultima_respuesta = fields.Text(
        string="Latest API response",
        help="Last API Response, this allows debugging errors if they exist"
    )
