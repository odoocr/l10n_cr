# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from . import api_facturae
import base64
from lxml import etree
from odoo.tests.common import Form
import re
import logging

_logger = logging.getLogger(__name__)

class AccountJournalInherit(models.Model):
    _name = 'account.journal'
    _inherit = 'account.journal'

    sucursal = fields.Integer(string="Branch", required=False, default="1")
    terminal = fields.Integer(string="Terminal", required=False, default="1")

    FE_sequence_id = fields.Many2one("ir.sequence",
                                     string="Electronic Invoice Sequence",
                                     required=False)

    TE_sequence_id = fields.Many2one("ir.sequence",
                                     string="Electronic Ticket Sequence",
                                     required=False)

    FEE_sequence_id = fields.Many2one("ir.sequence",
                                      string="Sequence of Electronic Export Invoices",
                                      required=False)

    NC_sequence_id = fields.Many2one("ir.sequence",
                                     string="Electronic Credit Notes Sequence",
                                     required=False)

    ND_sequence_id = fields.Many2one("ir.sequence",
                                     string="Electronic Debit Notes Sequence",
                                     required=False)

    expense_product_id = fields.Many2one(
        'product.product',
        string=_("Default product for expenses when loading data from XML"),
        help=_("The default product used when loading Costa Rican digital invoice"))

    expense_account_id = fields.Many2one(
        'account.account',
        string=_("Default Expense Account when loading data from XML"),
        help=_("The expense account used when loading Costa Rican digital invoice"))

    expense_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string=_("Default Analytic Account for expenses when loading data from XML"),
        help=_("The analytic account used when loading Costa Rican digital invoice"))

    load_lines = fields.Boolean(
        string=_('Indicates if invoice lines should be load when loading a Costa Rican Digital Invoice'),
        default=True
    )

    def invoice_from_xml(self, attachment):

        try:
            invoice_xml = etree.fromstring(base64.b64decode(attachment.datas))
            document_type = re.search('FacturaElectronica|NotaCreditoElectronica|NotaDebitoElectronica|TiqueteElectronico', invoice_xml.tag).group(0)

            if document_type == 'TiqueteElectronico':
                raise UserError(_("This is a TICKET only invoices are valid for taxes"))

        except Exception as e:
            raise UserError(_("This XML file is not XML-compliant. Error: %s") % e)

        attachment.write({'res_model': 'mail.compose.message'})
        decoders = self.env['account.move']._get_create_invoice_from_attachment_decoders()
        invoice = False
        for decoder in sorted(decoders, key=lambda d: d[0]):
            invoice = decoder[1](attachment)
            if invoice:
                break
        if not invoice:
            invoice = self.env['account.move'].create({})
        # No se crea el mensaje para ahorrar espacio en la BD ya que almancearia el adjunto y tambien el del objeto account.move
        #invoice.with_context(no_new_invoice=True).message_post(attachment_ids=[attachment.id])

        invoice.fname_xml_supplier_approval = attachment.name
        invoice.xml_supplier_approval = attachment.datas
        #invoice.load_xml_data()
        return invoice

    def create_invoice_from_attachment(self, attachment_ids=[]):
        ''' Create the invoices from files.
         :return: A action redirecting to account.move tree/form view.
        '''
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        if not attachments:
            raise UserError(_("No attachment was provided"))

        invoices = self.env['account.move']
        for attachment in attachments:
            if ".xml" in attachment.name or ".XML" in attachment.name:
                invoice = self.invoice_from_xml(attachment)
                invoices += invoice
            else:
                attachment.write({'res_model': 'mail.compose.message'})
                decoders = self.env['account.move']._get_create_invoice_from_attachment_decoders()
                invoice = False
                for decoder in sorted(decoders, key=lambda d: d[0]):
                    invoice = decoder[1](attachment)
                    if invoice:
                        break
                if not invoice:
                    invoice = self.env['account.move'].create({})
                invoice.with_context(no_new_invoice=True).message_post(attachment_ids=[attachment.id])
                invoices += invoice

        action_vals = {
            'name': _('Generated Documents'),
            'domain': [('id', 'in', invoices.ids)],
            'res_model': 'account.move',
            'views': [[False, "tree"], [False, "form"]],
            'type': 'ir.actions.act_window',
            'context': self._context
        }
        if len(invoices) == 1:
            action_vals.update({'res_id': invoices[0].id, 'view_mode': 'form'})
        else:
            action_vals['view_mode'] = 'tree,form'
        return action_vals