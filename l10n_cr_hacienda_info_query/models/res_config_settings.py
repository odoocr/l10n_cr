# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    url_base_yo_contribuyo = fields.Char(string="URL Base Yo Contribuyo",
                                         help="URL Base Yo Contribuyo",
                                         default="https://api.hacienda.go.cr/fe/mifacturacorreo?")

    usuario_yo_contribuyo = fields.Char(string="Yo Contribuyo User",
                                        help="Yo Contribuyo Developer Identification")

    token_yo_contribuyo = fields.Char(string="Yo Contribuyo Token",
                                      help="Yo Contribuyo Token provided by Ministerio de Hacienda")

    ultima_respuesta = fields.Text(string="Latest API response",
                                   help="Last API Response, this allows debugging errors if they exist")
    url_base = fields.Char(string="URL Base",
                           help="URL Base of the END POINT",
                           default="https://api.hacienda.go.cr/fe/ae?")

    get_tributary_information = fields.Boolean(default=True)
    get_yo_contribuyo_information = fields.Boolean(default=True)

    @api.model
    def get_values(self):
        res = super().get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            ultima_respuesta=get_param('ultima_respuesta'),
            url_base=get_param('url_base'),
            url_base_yo_contribuyo=get_param('url_base_yo_contribuyo'),
            usuario_yo_contribuyo=get_param('usuario_yo_contribuyo'),
            token_yo_contribuyo=get_param('token_yo_contribuyo'),
            get_tributary_information=bool(get_param('get_tributary_information')),
            get_yo_contribuyo_information=bool(get_param('get_yo_contribuyo_information'))
        )
        return res

    @api.model
    def set_values(self):
        super().set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('ultima_respuesta', self.ultima_respuesta)
        set_param('url_base', self.url_base)
        set_param('url_base_yo_contribuyo', self.url_base_yo_contribuyo)
        set_param('usuario_yo_contribuyo', self.usuario_yo_contribuyo)
        set_param('token_yo_contribuyo', self.token_yo_contribuyo)
        set_param('get_tributary_information', self.get_tributary_information)
        set_param('get_yo_contribuyo_information', self.get_yo_contribuyo_information)
