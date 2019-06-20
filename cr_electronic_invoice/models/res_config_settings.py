# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expense_account_id = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Default Expense Account for FE invoice import",
        domain=[('deprecated', '=', False)],
        help="The expense account used when importing Costa Rican electronic invoice automatically")

    reimbursable_email = fields.Char(
        string='Este email se busca en el "to" del correo para marcar la factura como reembolsable', required=False, copy=False, index=True)

    notification_email = fields.Char(
        string='Dirección a la que se envía cualquier notificación relacionada con FE', required=False, copy=False, index=True)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            expense_account_id=int(get_param('expense_account_id')),
            reimbursable_email=get_param('reimbursable_email'),
            notification_email=get_param('notification_email'),
        )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('expense_account_id', self.expense_account_id.id)
        set_param('reimbursable_email', self.reimbursable_email)
        set_param('notification_email', self.notification_email)
