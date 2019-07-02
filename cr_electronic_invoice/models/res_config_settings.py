# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_expense_account_id = fields.Many2one('account.account', company_dependent=True,
        string="Default Expense Account for FE invoice import",
        domain=[('deprecated', '=', False)],
        help="The expense account used when importing Costa Rican electronic invoice automatically")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            default_expense_account_id=int(get_param('default_expense_account_id')),
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('default_expense_account_id', self.default_expense_account_id.id)
