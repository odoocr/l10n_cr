# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expense_account_id = fields.Many2one(
        'account.account',
        company_dependent=True,
        string=_("Default Expense Account for loading data from XML"),
        domain=[('deprecated', '=', False)],
        help=_("The expense account used when loading Costa Rican digital invoice"))

    load_lines = fields.Boolean(
        string=_('Indicates if invoice lines should be load when loading a Costa Rican Digital Invoice'),
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            expense_account_id=int(get_param('expense_account_id')),
            load_lines=get_param('load_lines'),
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('expense_account_id', self.expense_account_id.id)
        set_param('load_lines', self.load_lines)
