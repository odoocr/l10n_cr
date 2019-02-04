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
import mimetypes
import base64

logger = logging.getLogger(__name__)


class AccountInvoiceImport(models.TransientModel):
    _name = 'account.invoice.import'
    _inherit = ['account.invoice.import', 'base.fe_cr']

    @api.model
    def parse_xml_invoice(self, xml_root):
        if xml_root.tag:
            try:
                document_type = re.search('FacturaElectronica|TiqueteElectronico|NotaCreditoElectronica|NotaDebitoElectronica|MensajeHacienda', xml_root.tag).group(0)
                return self.parse_fe_cr_invoice(xml_root, document_type)
            except AttributeError:
                return super(AccountInvoiceImport, self).parse_xml_invoice(xml_root)
        else:
            return super(AccountInvoiceImport, self).parse_xml_invoice(xml_root)

    def parse_fe_cr_invoice_line(self, iline, counters, namespaces):
        ## sample amount_total_xpath = xml_root.xpath("inv:ResumenFactura/inv:TotalComprobante", namespaces=namespaces)
        qty_xpath = iline.xpath("inv:Cantidad", namespaces=namespaces)
        qty = float(qty_xpath[0].text)
        uom_xpath = iline.xpath("inv:UnidadMedida", namespaces=namespaces)
        uom_pre = uom_xpath[0].text
        if uom_pre == 'Otros':
            uom_pre = 'Unid'
        uom = {'unece_code': uom_pre}
        #product_dict = self.fe_cr_parse_product(iline, namespaces)
        name_xpath = iline.xpath("inv:Detalle", namespaces=namespaces)
        name = name_xpath and name_xpath[0].text or '-'
        price_unit_xpath = iline.xpath("inv:PrecioUnitario", namespaces=namespaces)
        price_unit = float(price_unit_xpath[0].text)
        discount_xpath = iline.xpath("inv:MontoDescuento", namespaces=namespaces)
        if discount_xpath:
            discount_amount = float(discount_xpath[0].text)
            discount = discount_amount / qty / price_unit * 100
            discount_details_xpath = iline.xpath("inv:NaturalezaDescuento", namespaces=namespaces)
            discount_details = discount_details_xpath[0].text
        else:
            discount = 0
            discount_details = ''
        price_subtotal_xpath = iline.xpath("inv:SubTotal", namespaces=namespaces)
        price_subtotal = float(price_subtotal_xpath[0].text)
        #if not price_subtotal:
        #    return False
        counters['lines'] += price_subtotal
        taxes_xpath = iline.xpath("inv:Impuesto", namespaces=namespaces)
        taxes = []
        for tax in taxes_xpath:
            tax_code_xpath = tax.xpath("inv:Codigo", namespaces=namespaces)
            tax_code = tax_code_xpath[0].text
            #categ_code_xpath = tax.xpath(
            #    "cbc:ID", namespaces=namespaces)
            #categ_code = 'S'
            percent_xpath = tax.xpath("inv:Tarifa", namespaces=namespaces)
            percentage = percent_xpath[0].text and float(percent_xpath[0].text)
            tax_dict = {
                'amount_type': 'percent',
                'amount': percentage,
                'tax_code': tax_code,
                }
            taxes.append(tax_dict)
        product_code_xpath = iline.xpath("inv:Codigo/inv:Codigo", namespaces=namespaces)
        product_dict = {
            'barcode': False,
            'code': product_code_xpath and product_code_xpath[0].text or False,
            'taxes': taxes,
            'name': name,
            'price': price_subtotal / qty,
            'uom': uom['unece_code']
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
        """Parse FE CR Invoice XML file"""
        namespaces = xml_root.nsmap
        inv_xmlns = namespaces.pop(None)
        namespaces['inv'] = inv_xmlns
        logger.debug('XML file namespaces=%s', namespaces)
        xml_string = etree.tostring(
            xml_root, pretty_print=True, encoding='UTF-8',
            xml_declaration=True)
        #fe_cr_version_xpath = xml_root.xpath(
        #    "//cbc:UBLVersionID", namespaces=namespaces)
        #fe_cr_version = fe_cr_version_xpath and fe_cr_version_xpath[0].text or '2.1'
        fe_cr_version = '4.2'
        # Check XML schema to avoid headaches trying to import invalid files
        # not working !
        # self._fe_cr_check_xml_schema(xml_string, document_type, version=fe_cr_version)
        prec = self.env['decimal.precision'].precision_get('Account')

        document_type = re.search('FacturaElectronica|TiqueteElectronico|NotaCreditoElectronica|NotaDebitoElectronica|MensajeHacienda',
                                  xml_root.tag).group(0)
        if document_type != 'MensajeHacienda':
            inv_type = 'in_invoice'
            if document_type == 'NotaCreditoElectronica':
                inv_type = 'in_refund'
            number_electronic = xml_root.xpath("inv:Clave", namespaces=namespaces)[0].text
            reference = number_electronic[21:41]
            date_issuance = xml_root.xpath("inv:FechaEmision", namespaces=namespaces)[0].text
            currency = xml_root.xpath("inv:ResumenFactura/inv:CodigoMoneda", namespaces=namespaces)[0].text or "CRC"
            currency_id = self.env['res.currency'].search([('name', '=', currency)], limit=1).id
            date_invoice = parse(date_issuance)

            origin = False
            supplier_dict = self.fe_cr_parse_party(xml_root.xpath('inv:Emisor',namespaces=namespaces)[0], namespaces)
            company_dict_full = self.fe_cr_parse_party(xml_root.xpath('inv:Receptor',namespaces=namespaces)[0], namespaces)
            company_dict = {}
            # We only take the "official references" for company_dict
            if company_dict_full.get('vat'):
                company_dict = {'vat': company_dict_full['vat']}

            total_untaxed_xpath = xml_root.xpath("inv:ResumenFactura/inv:TotalVentaNeta", namespaces=namespaces)
            amount_untaxed = float(total_untaxed_xpath[0].text)
            amount_total_xpath = xml_root.xpath("inv:ResumenFactura/inv:TotalComprobante", namespaces=namespaces)
            amount_total = float(amount_total_xpath[0].text)
            total_line = amount_untaxed
            #payment_type_code = xml_root.xpath(
            #    "/inv:Invoice/cac:PaymentMeans/"
            #    "cbc:PaymentMeansCode[@listAgencyID='6']",
            #   namespaces=namespaces)
            res_lines = []
            counters = {'lines': 0.0}
            inv_line_xpath = xml_root.xpath('inv:DetalleServicio/inv:LineaDetalle', namespaces=namespaces)
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
                #'date': fields.Date.to_string(date_issuance),
                'date': date_issuance,
                'date_issuance': date_issuance,
                #'date_due': date_due_str,
                'currency': {'iso': currency},
                'amount_total': amount_total,
                'amount_untaxed': amount_untaxed,
                'amount_total_electronic_invoice': amount_total,
                'lines': res_lines,
                'attachments': attachments,
                }
            logger.info('Result of CR FE XML parsing: %s', res)
            return res
        else:
            #xml-hacienda
            return {}


    @api.model
    def _prepare_create_invoice_vals(self, parsed_inv, import_config=False):
        assert parsed_inv.get('pre-processed'), 'pre-processing not done'
        # WARNING: on future versions, import_config will probably become
        # a required argument
        aio = self.env['account.invoice']
        ailo = self.env['account.invoice.line']
        bdio = self.env['business.document.import']
        rpo = self.env['res.partner']
        company_id = self._context.get('force_company') or\
            self.env.user.company_id.id
        start_end_dates_installed = hasattr(ailo, 'start_date') and\
            hasattr(ailo, 'end_date')
        if parsed_inv['type'] in ('out_invoice', 'out_refund'):
            partner_type = 'customer'
        else:
            partner_type = 'supplier'
        partner = bdio._match_partner(
            parsed_inv['partner'], parsed_inv['chatter_msg'],
            partner_type=partner_type)
        partner = partner.commercial_partner_id
        currency = bdio._match_currency(
            parsed_inv.get('currency'), parsed_inv['chatter_msg'])
        journal_id = aio.with_context(
            type=parsed_inv['type'],
            company_id=company_id)._default_journal().id
        vals = {
            'partner_id': partner.id,
            'currency_id': currency.id,
            'type': parsed_inv['type'],
            'company_id': company_id,
            'origin': parsed_inv.get('origin'),
            'reference': parsed_inv.get('invoice_number'),
            'date_invoice': parsed_inv.get('date'),
            'journal_id': journal_id,
            'invoice_line_ids': [],
        }
        #vals = aio.play_onchanges(vals, ['partner_id'])
        vals['invoice_line_ids'] = []
        # Force due date of the invoice
        if parsed_inv.get('date_due'):
            vals['date_due'] = parsed_inv.get('date_due')
        # Bank info
        if parsed_inv.get('iban'):
            partner = rpo.browse(vals['partner_id'])
            partner_bank = bdio._match_partner_bank(
                partner, parsed_inv['iban'], parsed_inv.get('bic'),
                parsed_inv['chatter_msg'], create_if_not_found=True)
            if partner_bank:
                vals['partner_bank_id'] = partner_bank.id
        config = import_config  # just to make variable name shorter
        if not config:
            if not partner.invoice_import_ids:
                raise UserError(_(
                    "Missing Invoice Import Configuration on partner '%s'.")
                    % partner.display_name)
            else:
                import_config_obj = partner.invoice_import_ids[0]
                config = import_config_obj.convert_to_import_config()

        if config['invoice_line_method'].startswith('1line'):
            if config['invoice_line_method'] == '1line_no_product':
                if config['taxes']:
                    invoice_line_tax_ids = [(6, 0, config['taxes'].ids)]
                else:
                    invoice_line_tax_ids = False
                il_vals = {
                    'account_id': config['account'].id,
                    'invoice_line_tax_ids': invoice_line_tax_ids,
                    'price_unit': parsed_inv.get('amount_untaxed'),
                    }
            elif config['invoice_line_method'] == '1line_static_product':
                product = config['product']
                il_vals = {'product_id': product.id, 'invoice_id': vals}
                il_vals = ailo.play_onchanges(il_vals, ['product_id'])
                il_vals.pop('invoice_id')
            if config.get('label'):
                il_vals['name'] = config['label']
            elif parsed_inv.get('description'):
                il_vals['name'] = parsed_inv['description']
            elif not il_vals.get('name'):
                il_vals['name'] = _('MISSING DESCRIPTION')
            self.set_1line_price_unit_and_quantity(il_vals, parsed_inv)
            self.set_1line_start_end_dates(il_vals, parsed_inv)
            vals['invoice_line_ids'].append((0, 0, il_vals))
        elif config['invoice_line_method'].startswith('nline'):
            if not parsed_inv.get('lines'):
                raise UserError(_(
                    "You have selected a Multi Line method for this import "
                    "but Odoo could not extract/read any XML file inside "
                    "the PDF invoice."))
            if config['invoice_line_method'] == 'nline_no_product':
                static_vals = {
                    'account_id': config['account'].id,
                    }
            elif config['invoice_line_method'] == 'nline_static_product':
                sproduct = config['product']
                static_vals = {'product_id': sproduct.id, 'invoice_id': vals}
                static_vals = ailo.play_onchanges(static_vals, ['product_id'])
                static_vals.pop('invoice_id')
            else:
                static_vals = {}
            for line in parsed_inv['lines']:
                il_vals = static_vals.copy()
                if config['invoice_line_method'] == 'nline_auto_product':
                    product = bdio._match_product(
                        line['product'], parsed_inv['chatter_msg'],
                        seller=partner)
                    il_vals = {'product_id': product.id, 'invoice_id': vals}
                    il_vals = ailo.play_onchanges(il_vals, ['product_id'])
                    il_vals.pop('invoice_id')
                elif config['invoice_line_method'] == 'nline_no_product':
                    taxes = bdio._match_taxes(
                        line.get('taxes'), parsed_inv['chatter_msg'])
                    il_vals['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                if not il_vals.get('account_id') and il_vals.get('product_id'):
                    product = self.env['product.product'].browse(
                        il_vals['product_id'])
                    raise UserError(_(
                        "Account missing on product '%s' or on it's related "
                        "category '%s'.") % (product.display_name,
                                             product.categ_id.display_name))
                if line.get('name'):
                    il_vals['name'] = line['name']
                elif not il_vals.get('name'):
                    il_vals['name'] = _('MISSING DESCRIPTION')
                if start_end_dates_installed:
                    il_vals['start_date'] =\
                        line.get('date_start') or parsed_inv.get('date_start')
                    il_vals['end_date'] =\
                        line.get('date_end') or parsed_inv.get('date_end')
                uom = bdio._match_uom(
                    line.get('uom'), parsed_inv['chatter_msg'])
                il_vals['uom_id'] = uom.id
                il_vals.update({
                    'quantity': line['qty'],
                    'price_unit': line['price_unit'],  # TODO fix for tax incl
                    })
                vals['invoice_line_ids'].append((0, 0, il_vals))
        # Write analytic account + fix syntax for taxes
        aacount_id = config.get('account_analytic') and\
            config['account_analytic'].id or False
        if aacount_id:
            for line in vals['invoice_line_ids']:
                line[2]['account_analytic_id'] = aacount_id
        vals['number_electronic']=parsed_inv['number_electronic']
        vals['date_issuance']=parsed_inv['date_issuance']
        vals['amount_total_electronic_invoice']=parsed_inv['amount_total_electronic_invoice']
        vals['xml_supplier_approval']=parsed_inv['xml_supplier_approval']
        vals['fname_xml_supplier_approval']=parsed_inv['fname_xml_supplier_approval']
        return (vals,config)

    @api.model
    def parse_invoice(self, invoice_file_b64, invoice_filename):
        assert invoice_file_b64, 'No invoice file'
        logger.info('Starting to import invoice %s', invoice_filename)
        file_data = base64.b64decode(invoice_file_b64)
        parsed_inv = {}
        pp_parsed_inv = {}
        filetype = mimetypes.guess_type(invoice_filename)
        logger.debug('Invoice mimetype: %s', filetype)
        if filetype and filetype[0] in ['application/xml', 'text/xml']:
            try:
                xml_root = etree.fromstring(file_data)
            except Exception as e:
                raise UserError(_(
                    "This XML file is not XML-compliant. Error: %s") % e)
            pretty_xml_string = etree.tostring(
                xml_root, pretty_print=True, encoding='UTF-8',
                xml_declaration=True)
            logger.debug('Starting to import the following XML file:')
            logger.debug(pretty_xml_string)
            parsed_inv = self.parse_xml_invoice(xml_root)
            if parsed_inv == {}:
                #xml-hacienda
                pass
            elif parsed_inv is False:
                raise UserError(_(
                    "This type of XML invoice is not supported. "
                    "Did you install the module to support this type "
                    "of file?"))
        # Fallback on PDF
        else:
            #pdf
            #We cant define a common structure for PDFs
            #parsed_inv = self.parse_pdf_invoice(file_data)
            pass
        # pre_process_parsed_inv() will be called again a second time,
        # but it's OK
        if 'number_electronic' in parsed_inv:
            pp_parsed_inv = self.pre_process_parsed_inv(parsed_inv)
        else:
            #xml-hacienda
            #pdf
            pass
        if pp_parsed_inv != {}:
                pp_parsed_inv['xml_supplier_approval'] = invoice_file_b64
                pp_parsed_inv['fname_xml_supplier_approval'] = invoice_filename
        else:
            #xml-hacienda
            #pdf
            pass
        return pp_parsed_inv
    
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        #TODO: Agregar una expresión regular para obtener el correo de configuración
        # del cual se van a importar las facturas electrónicas
        #TODO: Mergear la lógica de esta importación con la lectura del
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

        self = self.with_context(force_company=company_id)
        aiico = self.env['account.invoice.import.config']
        bdio = self.env['business.document.import']
        i = 0
        attrs_inv = {}
        if msg_dict.get('attachments'):
            i += 1
            for attach in msg_dict['attachments']:
                invoice_filename = attach.fname
                invoice_file_b64 = base64.b64encode(attach.content)
                filetype = mimetypes.guess_type(invoice_filename)
                logger.info(
                    'Attachment %d: %s. Trying to import it as an invoice',
                    i, invoice_filename)
                parsed_inv = self.parse_invoice(
                    invoice_file_b64, invoice_filename)
                if (filetype and 
                        filetype[0] in ['application/xml', 'text/xml'] and
                        parsed_inv != {}):
                    partner = bdio._match_partner(
                        parsed_inv['partner'], parsed_inv['chatter_msg'])

                    existing_inv = self.invoice_already_exists(partner, parsed_inv)
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
                        #continue
                        import_config = self._default_config(partner, company_id)
                    elif len(import_configs) == 1:
                        import_config = import_configs.convert_to_import_config()
                    else:
                        logger.info(
                            "There are %d invoice import configs for partner %s. "
                            "Using the first one '%s''", len(import_configs),
                            partner.display_name, import_configs[0].name)
                        import_config =\
                            import_configs[0].convert_to_import_config()
                    attrs_inv['parsed_inv'] = parsed_inv
                    attrs_inv['import_config'] = import_config 
                    #invoice = self.create_invoice(parsed_inv, import_config)
                    #logger.info('Invoice ID %d created from email', invoice.id)
                    # invoice.message_post(_(
                    #     "Invoice successfully imported from email sent by "
                    #     "<b>%s</b> on %s with subject <i>%s</i>.") % (
                    #         msg_dict.get('email_from'), msg_dict.get('date'),
                    #         msg_dict.get('subject')))
                else:
                    #pdf
                    pass
                if 'attachments' not in attrs_inv:
                    attrs_inv['attachments'] = {}
                attrs_inv['attachments'][invoice_filename] = invoice_file_b64
            if 'parsed_inv' in attrs_inv:
                final_inv = {}
                final_inv.update(attrs_inv['parsed_inv'])
                final_inv['attachments'].update(attrs_inv['attachments'])
                invoice = self.create_invoice(final_inv, attrs_inv['import_config'])
                logger.info('Invoice ID %d created from email', invoice.id)
                invoice.message_post(_(
                    "Invoice successfully imported from email sent by "
                    "<b>%s</b> on %s with subject <i>%s</i>.") % (
                        msg_dict.get('email_from'), msg_dict.get('date'),
                        msg_dict.get('subject')))
        else:
            logger.info('The email has no attachments, skipped.')
