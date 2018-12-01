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

logger = logging.getLogger(__name__)


class AccountInvoiceImport(models.TransientModel):
    _name = 'account.invoice.import'
    _inherit = ['account.invoice.import', 'base.fe_cr']

    @api.model
    def parse_xml_invoice(self, xml_root):
        if xml_root.tag:
            try:
                document_type = re.search('FacturaElectronica|TiqueteElectronico|NotaCreditoElectronica|NotaDebitoElectronica', xml_root.tag).group(0)
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
        """Parse UBL Invoice XML file"""
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

        document_type = re.search('FacturaElectronica|TiqueteElectronico|NotaCreditoElectronica|NotaDebitoElectronica',
                                  xml_root.tag).group(0)
        inv_type = 'in_invoice'
        if document_type == 'NotaCreditoElectronica':
            inv_type = 'in_refund'
        number_electronic = xml_root.xpath("inv:Clave", namespaces=namespaces)[0].text
        reference = number_electronic[21:41]
        date_issuance = xml_root.xpath("inv:FechaEmision", namespaces=namespaces)[0].text
        currency = xml_root.xpath("inv:ResumenFactura/inv:CodigoMoneda", namespaces=namespaces)[0].text
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

    @api.model
    def _prepare_create_invoice_vals(self, parsed_inv, import_config=False):
        (vals, import_config) = super(AccountInvoiceImport, self)._prepare_create_invoice_vals(parsed_inv, import_config)
        vals['number_electronic']=parsed_inv['number_electronic']
        vals['date_issuance']=parsed_inv['date_issuance']
        vals['amount_total_electronic_invoice']=parsed_inv['amount_total_electronic_invoice']
        vals['xml_supplier_approval']=parsed_inv['xml_supplier_approval']
        return (vals,import_config)

    @api.model
    def parse_invoice(self, invoice_file_b64, invoice_filename):
        pp_parsed_inv = super(AccountInvoiceImport, self).parse_invoice(invoice_file_b64, invoice_filename)
        pp_parsed_inv['xml_supplier_approval'] = invoice_file_b64
        return pp_parsed_inv
