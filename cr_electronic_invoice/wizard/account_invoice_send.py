from odoo import models
from odoo.tools.misc import get_lang


class AccountInvoiceSend(models.TransientModel):
    _inherit = 'account.invoice.send'

    def send_and_print_action(self):
        self.ensure_one()
        if self.composition_mode == 'mass_mail' and self.template_id:
            for move in self.invoice_ids:
                if move.company_id.frm_ws_ambiente == 'disabled':
                    active_records = self.env[self.model].browse(move.ids)
                    langs = active_records.mapped('partner_id.lang')
                    default_lang = get_lang(self.env)
                    for lang in (set(langs) or [default_lang]):
                        active_ids_lang = active_records.filtered(lambda r: r.partner_id.lang == lang).ids
                        self_lang = self.with_context(active_ids=active_ids_lang, lang=lang)
                        self_lang.onchange_template_id()
                        self_lang._send_email()
                else:
                    if move.state_tributacion == 'aceptado':
                        move.action_invoice_sent_mass()
        else:
            self._send_email()
        if self.is_print:
            return self._print_document()
        return {'type': 'ir.actions.act_window_close'}
