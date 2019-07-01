# -*- coding: utf-8 -*-

from odoo import fields, models, api


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        context = self._context
        account_invoice = self.env['account.invoice']
        invoice_ids = context.get('active_ids')
        if context.get('mass_mark_invoice_as_sent') and \
                context.get('default_model') == 'account.invoice':
            for invoice in account_invoice.browse(invoice_ids):
                invoice.sent = True
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)
