from odoo import models,fields,api


class DebitAccountInvoice(models.Model):
    _inherit = "account.invoice"

    refund_type = fields.Selection([('debit', 'Debit Note'), ('invoice', 'Factura'), ('credit', 'Credit Note')],
                                   index=True, string='Refund type',
                                   track_visibility='always')
