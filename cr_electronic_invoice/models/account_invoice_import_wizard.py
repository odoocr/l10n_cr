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

    static_product_id = fields.Many2one('product.product', string='Product to asign to every line', domain=[('purchase_ok', '=', True)])
    account_id = fields.Many2one('account.account', string='Expense Account', domain=[('deprecated', '=', False)])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    @api.onchange('static_product_id')
    def _onchange_static_product_id(self):
        if self.static_product_id and self.static_product_id.property_account_expense_id:
            self.account_id = self.static_product_id.property_account_expense_id

    @api.multi
    def _create_invoice_from_file(self, attachment):

        try:
            invoice_xml = etree.fromstring(base64.b64decode(attachment.datas))
            document_type = re.search('FacturaElectronica|NotaCreditoElectronica|NotaDebitoElectronica|TiqueteElectronico', invoice_xml.tag).group(0)

            if document_type == 'TiqueteElectronico':
                raise UserError(_("This is a TICKET only invoices are valid for taxes"))

        except Exception as e:
            raise UserError(_("This XML file is not XML-compliant. Error: %s") % e)

        self = self.with_context(default_journal_id=self.journal_id.id)
        invoice_form = Form(self.env['account.invoice'], view='account.invoice_supplier_form')
        invoice = invoice_form.save()

        invoice.fname_xml_supplier_approval = attachment.datas_fname
        invoice.xml_supplier_approval = attachment.datas
        api_facturae.load_xml_data(invoice, True, self.account_id, self.static_product_id, self.account_analytic_id)
        attachment.write({'res_model': 'account.invoice', 'res_id': invoice.id})
        invoice.message_post(attachment_ids=[attachment.id])
        return invoice

    
    @api.model
    def message_new(self, msg_dict, custom_values=None):

        reimbursable_email = self.env['ir.config_parameter'].sudo(
        ).get_param('reimbursable_email')

        # Is it for reimburse
        reimbursable = reimbursable_email in msg_dict['to']

        # TODO: Agregar una expresión regular para obtener el correo de configuración
        # del cual se van a importar las facturas electrónicas
        # TODO: Mergear la lógica de esta importación con la lectura del
        # módulo 'ak_invoice_reimbursable'
        logger.info(
            'New email received associated with account.invoice.import: '
            'From: %s, Subject: %s, Date: %s, Message ID: %s. Executing '
            'with user %s ID %d',
            msg_dict.get('email_from'), msg_dict.get('subject'),
            msg_dict.get('date'), msg_dict.get('message_id'),
            self.env.user.name, self.env.user.id)
        # It seems that the "Odoo-way" to handle multi-company in E-mail
        # gateways is by using mail.aliases associated with users that
        # don't switch company (I haven't found any other way), which
        # is not convenient because you may have to create new users
        # for that purpose only. So I implemented my own mechanism,
        # based on the destination email address.
        # This method is called (indirectly) by the fetchmail cron which
        # is run by default as admin and retreive all incoming email in
        # all email accounts. We want to keep this default behavior,
        # and, in multi-company environnement, differentiate the company
        # per destination email address
        company_id = False
        all_companies = self.env['res.company'].search_read(
            [], ['invoice_import_email'])
        if len(all_companies) > 1:  # multi-company setup
            for company in all_companies:
                if company['invoice_import_email']:
                    company_dest_email = company['invoice_import_email']\
                        .strip()
                    if (
                            company_dest_email in msg_dict.get('to', '') or
                            company_dest_email in msg_dict.get('cc', '')):
                        company_id = company['id']
                        logger.info(
                            'Matched with %s: importing invoices in company '
                            'ID %d', company_dest_email, company_id)
                        break
            if not company_id:
                logger.error(
                    'Invoice import mail gateway in multi-company setup: '
                    'invoice_import_email of the companies of this DB was '
                    'not found as destination of this email (to: %s, cc: %s). '
                    'Ignoring this email.',
                    msg_dict['email_to'], msg_dict['cc'])
                return
        else:  # mono-company setup
            company_id = all_companies[0]['id']

        # Se identifican los XMLs por clave y por tipo y los PDFs se meten todos en una lista para adjuntarlos a todas las facturas en este email.
        # Porque no tenemos un metodo seguro de buscar la clave dentro del PDF

        pdfs_list = list()

        self = self.with_context(force_company=company_id)
        aiico = self.env['account.invoice.import.config']
        bdio = self.env['business.document.import']
        i = 0
        attrs_inv = {}
        if msg_dict.get('attachments'):
            # clasify all the attachments because there could be several invoices in an email or it could be a response or pdf in one email and the invoice.xml in another email.
            for attachment in msg_dict['attachments']:
                if attachment.fname.endswith('.xml'):
                    xml_root = etree.fromstring(attachment.content)
                    namespaces = xml_root.nsmap
                    inv_xmlns = namespaces.pop(None)
                    namespaces['inv'] = inv_xmlns
                    document_type = re.search(
                        'FacturaElectronica|TiqueteElectronico|NotaCreditoElectronica|NotaDebitoElectronica|MensajeHacienda', xml_root.tag).group(0)
                    if document_type != 'MensajeHacienda':
                        clave = xml_root.xpath(
                            "inv:Clave", namespaces=namespaces)[0].text
                        if clave and clave not in invoices:
                            invoices[clave] = dict()
                        invoices[clave]['invoice_attachment'] = attachment
                    elif document_type == 'MensajeHacienda':
                        invoices[clave]['respuesta_hacienda'] = attachment
                elif attachment.fname.endswith('.pdf'):
                    pdf_file = io.BytesIO(attachment.content)
                    read_pdf = PyPDF2.PdfFileReader(pdf_file)
                    number_of_pages = read_pdf.getNumPages()
                    page = read_pdf.getPage(0)
                    pdf_text = page.extractText()
                    claves = re.findall(r'\d{50}', pdf_text)
                    if claves and claves[0]:
                        clave = claves[0]
                        if clave and clave not in invoices:
                            invoices[clave] = dict()
                        invoices[clave]['pdf_attachment'] = attachment
                    else:
                        pdfs_list.append(attachment)

            i += 1
            for clave in invoices:
                invoice = False
                invoices[clave]['pdfs'] = pdfs_list
                if 'invoice_attachment' in invoices[clave]:
                    attach = invoices[clave]['invoice_attachment']
                    invoice_filename = attach.fname
                    invoice_file_b64 = base64.b64encode(attach.content)
                    file_data = base64.b64decode(invoice_file_b64)
                    filetype = mimetypes.guess_type(invoice_filename)
                    logger.info(
                        'Attachment %d: %s. Trying to import it as an invoice', i, invoice_filename)
                    parsed_inv = self.parse_invoice(
                        invoice_file_b64, invoice_filename)
                    if (filetype and filetype[0] in ['application/xml', 'text/xml'] and
                            parsed_inv != {}):
                        partner = bdio._match_partner(
                            parsed_inv['partner'], parsed_inv['chatter_msg'])

                        existing_inv = self.invoice_already_exists(
                            partner, parsed_inv)
                        if existing_inv:
                            logger.warning(
                                "Mail import: this supplier invoice already exists "
                                "in Odoo (ID %d number %s supplier number %s)",
                                existing_inv.id, existing_inv.number,
                                parsed_inv.get('invoice_number'))
                            continue
                        import_configs = aiico.search([
                            ('partner_id', '=', partner.id),
                            ('company_id', '=', company_id)])
                        if not import_configs:
                            logger.warning(
                                "Mail import: missing Invoice Import Configuration "
                                "for partner '%s'.", partner.display_name)
                            # continue
                            import_config = self._default_config(
                                partner, company_id)
                        elif len(import_configs) == 1:
                            import_config = import_configs.convert_to_import_config()
                        else:
                            logger.info(
                                "There are %d invoice import configs for partner %s. "
                                "Using the first one '%s''", len(
                                    import_configs),
                                partner.display_name, import_configs[0].name)
                            import_config =\
                                import_configs[0].convert_to_import_config()
                        attrs_inv['parsed_inv'] = parsed_inv
                        attrs_inv['import_config'] = import_config
                        # invoice = self.create_invoice(parsed_inv, import_config)
                        # logger.info('Invoice ID %d created from email', invoice.id)
                        # invoice.message_post(_(
                        #     "Invoice successfully imported from email sent by "
                        #     "<b>%s</b> on %s with subject <i>%s</i>.") % (
                        #         msg_dict.get('email_from'), msg_dict.get('date'),
                        #         msg_dict.get('subject')))
                    else:
                        # pdf
                        pass
                    if 'attachments' not in attrs_inv:
                        attrs_inv['attachments'] = {}
                    attrs_inv['attachments'][invoice_filename] = invoice_file_b64

            if 'parsed_inv' in attrs_inv:
                final_inv = {}
                final_inv.update(attrs_inv['parsed_inv'])
                final_inv['attachments'].update(attrs_inv['attachments'])
                invoice = self.create_invoice(
                    final_inv, attrs_inv['import_config'])
                logger.info('Invoice ID %d created from email', invoice.id)
                invoice.message_post(_(
                    "Invoice successfully imported from email sent by "
                    "<b>%s</b> on %s with subject <i>%s</i>.") % (
                        msg_dict.get('email_from'), msg_dict.get('date'),
                        msg_dict.get('subject')))
        else:
            logger.info('The email has no attachments, skipped.')
