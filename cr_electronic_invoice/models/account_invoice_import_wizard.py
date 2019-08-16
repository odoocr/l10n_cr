# -*- coding: utf-8 -*-
import base64
import datetime
import re
import logging
from lxml import etree
from dateutil.parser import parse
from odoo import api, fields, models, _
from odoo.tests.common import Form
from odoo.exceptions import UserError
from odoo.tools import float_compare
from . import api_facturae


class ImportInvoiceImportWizardCR(models.TransientModel):
    _inherit = "account.invoice.import.wizard"

    static_product_id = fields.Many2one('product.product', string='Producto a asignar en las líneas', domain=[('purchase_ok', '=', True)])
    account_id = fields.Many2one('account.account', string='Expense Account', domain=[('deprecated', '=', False)])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    @api.onchange('static_product_id')
    def _onchange_static_product_id(self):
        if self.static_product_id and self.static_product_id.property_account_expense_id:
            self.account_id = self.static_product_id.property_account_expense_id

    @api.multi
    def _create_invoice_from_file(self, attachment):
        self = self.with_context(default_journal_id=self.journal_id.id)
        invoice_form = Form(self.env['account.invoice'], view='account.invoice_supplier_form')
        invoice = invoice_form.save()

        try:
            invoice_xml = etree.fromstring(attachment.index_content.encode('UTF-8'))
            document_type = re.search('FacturaElectronica|NotaCreditoElectronica|NotaDebitoElectronica', invoice_xml.tag).group(0)
        except Exception as e:
            raise UserError(_("This XML file is not XML-compliant. Error: %s") % e)

        invoice.fname_xml_supplier_approval = attachment.datas_fname
        invoice.xml_supplier_approval = base64.encodestring(attachment.index_content.encode('UTF-8'))
        api_facturae.load_xml_data(invoice, True, self.account_id.id, self.static_product_id.id, self.account_analytic_id.id)
        attachment.write({'res_model': 'account.invoice', 'res_id': invoice.id})
        invoice.message_post(attachment_ids=[attachment.id])
        return invoice
