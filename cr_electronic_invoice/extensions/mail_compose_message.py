

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def send_mail(self, auto_commit=False):
        context = self._context
        if context.get('mass_mark_invoice_as_sent') and \
                context.get('default_model') == 'account.move':
            account_invoice = self.env['account.move']
            invoice_ids = context.get('active_ids')
            for invoice in account_invoice.browse(invoice_ids):
                invoice.invoice_sent = True
        return super().send_mail(auto_commit=auto_commit)
