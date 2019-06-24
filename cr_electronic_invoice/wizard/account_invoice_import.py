# -*- coding: utf-8 -*-
# © 2016-2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare
from datetime import datetime
from dateutil.parser import parse
from lxml import etree
import logging
import re
import io
import mimetypes
import base64
import PyPDF2

logger = logging.getLogger(__name__)

# Dictionary to store all the attachemnts until they are processed
invoices = {}


class AccountInvoiceImport(models.TransientModel):
    _name = 'account.invoice.import'
    _inherit = ['account.invoice.import', 'base.fe_cr']
    _description = 'Wizard to import supplier invoices/refunds'

    @api.model
    def parse_xml_invoice(self, xml_root):
        if xml_root.tag:
            try:
                document_type = re.search(
                    'FacturaElectronica|TiqueteElectronico|NotaCreditoElectronica|NotaDebitoElectronica', xml_root.tag).group(0)
                return self.parse_fe_cr_invoice(xml_root, document_type)
            except AttributeError:
                return super(AccountInvoiceImport, self).parse_xml_invoice(xml_root)
        else:
            return super(AccountInvoiceImport, self).parse_xml_invoice(xml_root)

    def parse_fe_cr_invoice_line(self, iline, counters, namespaces):
        # sample amount_total_xpath = xml_root.xpath("inv:ResumenFactura/inv:TotalComprobante", namespaces=namespaces)
        qty_xpath = iline.xpath("inv:Cantidad", namespaces=namespaces)
        qty = float(qty_xpath[0].text)
        uom_xpath = iline.xpath("inv:UnidadMedida", namespaces=namespaces)
        uom_pre = uom_xpath[0].text
        if uom_pre == 'Otros':
            uom_pre = 'Unid'
        uom = {'cr_code': uom_pre}
        # product_dict = self.fe_cr_parse_product(iline, namespaces)
        name_xpath = iline.xpath("inv:Detalle", namespaces=namespaces)
        name = name_xpath and name_xpath[0].text or '-'
        price_unit_xpath = iline.xpath(
            "inv:PrecioUnitario", namespaces=namespaces)
        price_unit = float(price_unit_xpath[0].text)
        MontoTotal = iline.xpath("inv:MontoTotal", namespaces=namespaces)
        total_line = float(MontoTotal[0].text)
        discount_xpath = iline.xpath(
            "inv:MontoDescuento", namespaces=namespaces)
        if discount_xpath:
            discount_amount = float(discount_xpath[0].text)
            discount = discount_amount / total_line * 100
            discount_details_xpath = iline.xpath(
                "inv:NaturalezaDescuento", namespaces=namespaces)
            discount_details = discount_details_xpath[0].text
        else:
            discount = 0
            discount_details = ''
        price_subtotal_xpath = iline.xpath(
            "inv:SubTotal", namespaces=namespaces)
        price_subtotal = float(price_subtotal_xpath[0].text)
        # if not price_subtotal:
        #    return False
        counters['lines'] += price_subtotal
        taxes_xpath = iline.xpath("inv:Impuesto", namespaces=namespaces)
        taxes = []
        for tax in taxes_xpath:
            tax_code_xpath = tax.xpath("inv:Codigo", namespaces=namespaces)
            tax_code = tax_code_xpath[0].text
            # categ_code_xpath = tax.xpath(
            #    "cbc:ID", namespaces=namespaces)
            # categ_code = 'S'
            percent_xpath = tax.xpath("inv:Tarifa", namespaces=namespaces)
            percentage = percent_xpath[0].text and float(percent_xpath[0].text)
            tax_dict = {
                'amount_type': 'percent',
                'amount': percentage,
                'tax_code': tax_code,
            }
            taxes.append(tax_dict)
        product_code_xpath = iline.xpath(
            "inv:Codigo/inv:Codigo", namespaces=namespaces)
        product_dict = {
            'barcode': False,
            'code': product_code_xpath and product_code_xpath[0].text or False,
            'taxes': taxes,
            'name': name,
            'price': price_subtotal / qty,
            'uom': uom['cr_code']
        }

        vals = {
            'product': product_dict,
            'qty': qty,
            'uom': uom,
            'price_unit': price_unit,
            'discount': discount,
            'discount_details': discount_details,
            'price_subtotal': price_subtotal,
            'name': name,
            'taxes': taxes,
        }
        return vals

    @api.model
    def parse_fe_cr_invoice(self, xml_root, document_type):
        """Parse UBL Invoice XML file"""
        namespaces = xml_root.nsmap
        inv_xmlns = namespaces.pop(None)
        namespaces['inv'] = inv_xmlns
        logger.debug('XML file namespaces=%s', namespaces)
        xml_string = etree.tostring(
            xml_root, pretty_print=True, encoding='UTF-8',
            xml_declaration=True)
        # fe_cr_version_xpath = xml_root.xpath(
        #    "//cbc:UBLVersionID", namespaces=namespaces)
        # fe_cr_version = fe_cr_version_xpath and fe_cr_version_xpath[0].text or '2.1'
        fe_cr_version = '4.2'
        # Check XML schema to avoid headaches trying to import invalid files
        # not working !
        # self._fe_cr_check_xml_schema(xml_string, document_type, version=fe_cr_version)
        prec = self.env['decimal.precision'].precision_get('Account')

        document_type = re.search('FacturaElectronica|TiqueteElectronico|NotaCreditoElectronica|NotaDebitoElectronica',
                                  xml_root.tag).group(0)
        inv_type = 'in_invoice'
        if document_type == 'NotaCreditoElectronica':
            inv_type = 'in_refund'
        number_electronic = xml_root.xpath(
            "inv:Clave", namespaces=namespaces)[0].text
        reference = number_electronic[21:41]
        date_issuance = xml_root.xpath(
            "inv:FechaEmision", namespaces=namespaces)[0].text
        currency_xpath = xml_root.xpath(
            "inv:ResumenFactura/inv:CodigoMoneda", namespaces=namespaces)
        currency = currency_xpath and currency_xpath[0].text or 'CRC'
        currency_id = self.env['res.currency'].search(
            [('name', '=', currency)], limit=1).id
        date_invoice = parse(date_issuance)

        origin = False
        supplier_dict = self.fe_cr_parse_party(xml_root.xpath(
            'inv:Emisor', namespaces=namespaces)[0], namespaces)
        company_dict_full = self.fe_cr_parse_party(xml_root.xpath(
            'inv:Receptor', namespaces=namespaces)[0], namespaces)
        company_dict = {}

        # We only take the "official references" for company_dict
        if company_dict_full.get('vat'):
            company_dict = {'vat': company_dict_full['vat']}

        total_untaxed_xpath = xml_root.xpath(
            "inv:ResumenFactura/inv:TotalVentaNeta", namespaces=namespaces)
        if total_untaxed_xpath:
            amount_untaxed = float(total_untaxed_xpath[0].text)
        else:
            amount_untaxed = 0

        amount_total_xpath = xml_root.xpath(
            "inv:ResumenFactura/inv:TotalComprobante", namespaces=namespaces)
        amount_total = float(amount_total_xpath[0].text)

        amount_total_tax_xpath = xml_root.xpath(
            "inv:ResumenFactura/inv:TotalImpuesto", namespaces=namespaces)
        if amount_total_tax_xpath:
            amount_total_tax = float(amount_total_tax_xpath[0].text)
        else:
            amount_total_tax = 0

        total_line = amount_untaxed

        # payment_type_code = xml_root.xpath(
        #    "/inv:Invoice/cac:PaymentMeans/"
        #    "cbc:PaymentMeansCode[@listAgencyID='6']",
        #   namespaces=namespaces)

        res_lines = []
        counters = {'lines': 0.0}
        inv_line_xpath = xml_root.xpath(
            'inv:DetalleServicio/inv:LineaDetalle', namespaces=namespaces)
        for iline in inv_line_xpath:
            line_vals = self.parse_fe_cr_invoice_line(
                iline, counters, namespaces)
            if line_vals is False:
                continue
            res_lines.append(line_vals)

        if float_compare(
                total_line, counters['lines'], precision_digits=prec):
            logger.warning(
                "The gloabl LineExtensionAmount (%s) doesn't match the "
                "sum of the amounts of each line (%s). It can "
                "have a diff of a few cents due to sum of rounded values vs "
                "rounded sum policies.", total_line, counters['lines'])

        attachments = {}
        res = {
            'type': inv_type,
            'partner': supplier_dict,
            'company': company_dict,
            'number_electronic': number_electronic,
            'invoice_number': reference,
            'reference': reference,
            'origin': origin,
            # 'date': fields.Date.to_string(date_issuance),
            'date': date_issuance,
            'date_issuance': date_issuance,
            # 'date_due': date_due_str,
            'currency': {'iso': currency},
            'amount_total': amount_total,
            'amount_total_tax': amount_total_tax,
            'amount_untaxed': amount_untaxed,
            'amount_total_electronic_invoice': amount_total,
            'lines': res_lines,
            'attachments': attachments,
        }
        logger.info('Result of CR FE XML parsing: %s', res)
        return res

    @api.model
    def _prepare_create_invoice_vals(self, parsed_inv, import_config=False):
        (vals, import_config) = super(AccountInvoiceImport,
                                      self)._prepare_create_invoice_vals(parsed_inv, import_config)
        vals['number_electronic'] = parsed_inv['number_electronic']
        vals['date_issuance'] = parsed_inv['date_issuance']
        vals['amount_total_electronic_invoice'] = parsed_inv['amount_total_electronic_invoice']
        vals['xml_supplier_approval'] = parsed_inv['xml_supplier_approval']
        vals['fname_xml_supplier_approval'] = parsed_inv['fname_xml_supplier_approval']
        vals['amount_tax_electronic_invoice'] = parsed_inv['amount_total_tax']
        return (vals, import_config)

    @api.model
    def parse_invoice(self, invoice_file_b64, invoice_filename):
        pp_parsed_inv = super(AccountInvoiceImport, self).parse_invoice(
            invoice_file_b64, invoice_filename)
        if pp_parsed_inv != {}:
            pp_parsed_inv['xml_supplier_approval'] = invoice_file_b64
            pp_parsed_inv['fname_xml_supplier_approval'] = invoice_filename
        return pp_parsed_inv

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
