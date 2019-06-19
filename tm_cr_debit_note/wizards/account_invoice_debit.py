from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
import datetime


class AccountInvoiceRefund(models.TransientModel):
    """Debit Notes"""

    _name = "account.invoice.debit"
    _description = "Debit Note"

    @api.model
    def _get_invoice_id(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            return active_id
        return ''

    @api.model
    def _get_journal(self):
        journal_type = self._context.get('journal_type')
        journal = False
        if journal_type == 'sale':
            journal = self.env.ref('tm_cr_debit_note.account_journal_sale_debit_note')
        elif journal_type == 'purchase':
            journal = self.env.ref('tm_cr_debit_note.account_journal_purchase_debit_note')
        return journal and journal.id or False

    '''OK, same as original Credit Note'''
    @api.model
    def _get_reason(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.name
        return ''

    date_invoice = fields.Date(string='Debit Note Date', default=fields.Date.context_today, required=True)
    date = fields.Date(string='Accounting Date')
    description = fields.Char(string='Reason', required=True, default=_get_reason)
    filter_debit = fields.Selection([('debit', 'Create a draft debit note')],
                                    default='debit', string='Debit Note Method', required=True,
                                    help='Debit Note base on this type. You can not Modify and Cancel if the '
                                         'invoice is already reconciled')
    reference_code_id = fields.Many2one(comodel_name="reference.code", string="Reference Code", required=True, )
    invoice_id = fields.Many2one(comodel_name="account.invoice", string="Reference Document",
                                 default=_get_invoice_id, required=False, )
    journal_id = fields.Many2one('account.journal', string='Journal', default=_get_journal)
    date_due = fields.Date(string='Vencimiento ND', default=fields.Date.context_today, required=True)

    @api.multi
    def compute_debit(self, mode='debit'):
        inv_obj = self.env['account.invoice']
        context = dict(self._context or {})
        xml_id = False

        for form in self:
            created_inv = []

            for inv in inv_obj.browse(context.get('active_ids')):
                if inv.state in ['draft', 'cancel']:
                    raise UserError(_('Cannot create debit note for the draft/cancelled credit note.'))
                if inv.reconciled and mode in ('cancel', 'modify'):
                    raise UserError(_('Cannot create a debit not for the credit note which is already reconciled, '
                                      'credit note should be unreconciled first, then only you can add debit note'
                                      ' for this credit note.'))

                date = form.date or False
                description = form.description or inv.name
                journal_id = form.journal_id or inv.journal_id

                debit = inv.copy()

                if inv.type == 'out_refund':
                    '''We Just want to update the debit note info, not the credit note'''
                    '''We must change invoice type to out_invoice to sum amounts'''
                    debit.type = 'out_invoice'
                else:
                    debit.type = 'in_invoice'

                or_date = form.date_invoice #datetime.datetime.strptime(form.date_invoice, '%Y-%m-%d')
                #hc_date = datetime.date.strftime(or_date, "%Y-%m-%dT%H:%M:%S-06:00")
                hc_date = or_date.strftime("%Y-%m-%dT%H:%M:%S-06:00")

                debit.update({
                    'type': debit.type,
                    'refund_type': 'debit',
                    'date_invoice': hc_date,
                    'state': 'draft',
                    'name': description,
                    'journal_id': journal_id.id,
                    'date_due': form.date_due,
                    'invoice_id': form.invoice_id,
                    'date': date,
                    'origin': inv.number,
                    'fiscal_position_id': inv.fiscal_position_id.id,
                    'tipo_comprobante': 'ND',
                })

                created_inv.append(debit.id)
                xml_id = (inv.type in ['out_refund', 'out_invoice']) and 'action_invoice_tree3'

                # Put the reason in the chatter
                subject = _("Debit Note")
                body = description
                debit.message_post(body=body, subject=subject)
        if xml_id:
            result = self.env.ref('tm_cr_debit_note.%s' % xml_id).read()[0]
            invoice_domain = safe_eval(result['domain'])
            invoice_domain.append(('id', 'in', created_inv))
            result['domain'] = invoice_domain
            return result
        return True

    @api.multi
    def invoice_debit(self):
        data_debit = self.read(['filter_debit'])[0]['filter_debit']
        return self.compute_debit(data_debit)
