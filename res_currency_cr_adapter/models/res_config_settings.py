# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    exchange_source = fields.Selection([
        ('disabled', 'Disabled'),
        ('bccr', 'BCCR (recommended)'),
        ('hacienda', 'Hacienda')
        ], required=True, default='disabled')
        
    bccr_username = fields.Char(string="BCCR username", required=False, )
    bccr_email = fields.Char(string="e-mail registered in the BCCR", required=False, )
    bccr_token = fields.Char(string="Token to use in the BCCR", required=False, )
    
    
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            bccr_username=get_param('bccr_username'),
            bccr_email=get_param('bccr_email'),
            bccr_token=get_param('bccr_token'),
            exchange_source=get_param('exchange_source'),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('bccr_username', self.bccr_username)
        set_param('bccr_email', self.bccr_email)
        set_param('bccr_token', self.bccr_token)
        set_param('exchange_source', self.exchange_source)

