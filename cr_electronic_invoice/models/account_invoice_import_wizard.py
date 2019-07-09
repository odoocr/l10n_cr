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
        # invoice = self.env['account.invoice'].new({})
        # invoice.journal_id = self.journal_id
        # invoice.company_id = self.journal_id.company_id
        self.load_xml_data(invoice, attachment)
        attachment.write({'res_model': 'account.invoice', 'res_id': invoice.id})
        invoice.message_post(attachment_ids=[attachment.id])
        return invoice

    @api.multi
    def load_xml_data(self, invoice, attachment):
        try:
            invoice_xml = etree.fromstring(attachment.index_content.encode('UTF-8'))
            document_type = re.search('FacturaElectronica|NotaCreditoElectronica|NotaDebitoElectronica', invoice_xml.tag).group(0)
        except Exception as e:
            raise UserError(_("This XML file is not XML-compliant. Error: %s") % e)

        invoice.fname_xml_supplier_approval = attachment.datas_fname
        invoice.xml_supplier_approval = base64.encodestring(attachment.index_content.encode('UTF-8'))
        namespaces = invoice_xml.nsmap
        inv_xmlns = namespaces.pop(None)
        namespaces['inv'] = inv_xmlns

        invoice.consecutive_number_receiver = invoice_xml.xpath(
            "inv:NumeroConsecutivo", namespaces=namespaces)[0].text

        invoice.reference = invoice.consecutive_number_receiver

        invoice.number_electronic = invoice_xml.xpath(
            "inv:Clave", namespaces=namespaces)[0].text
        invoice.date_issuance = invoice_xml.xpath(
            "inv:FechaEmision", namespaces=namespaces)[0].text
        emisor = invoice_xml.xpath(
            "inv:Emisor/inv:Identificacion/inv:Numero",
            namespaces=namespaces)[0].text
        receptor = invoice_xml.xpath(
            "inv:Receptor/inv:Identificacion/inv:Numero",
            namespaces=namespaces)[0].text

        if receptor != invoice.company_id.vat:
            raise UserError('El receptor no corresponde con la compañía actual con identificación ' +
                             receptor + '. Por favor active la compañía correcta.')  # noqa

        date_time_obj = datetime.datetime.strptime(invoice.date_issuance, '%Y-%m-%dT%H:%M:%S')
        invoice_date = date_time_obj.date()

        invoice.date_invoice = invoice_date

        partner = self.env['res.partner'].search([('vat', '=', emisor),
                                                  ('supplier', '=', True),
                                                  '|',
                                                  ('company_id', '=', invoice.company_id.id),
                                                  ('company_id', '=', False)],
                                                 limit=1)

        if partner:
            invoice.partner_id = partner
        else:
            raise UserError(_('The provider with ID %s does not exists. Please review it.', emisor))

        lines = invoice_xml.xpath("inv:DetalleServicio/inv:LineaDetalle", namespaces=namespaces)
        new_lines = self.env['account.invoice.line']
        for line in lines:
            product_uom = self.env['uom.uom'].search(
                [('code', '=', line.xpath("inv:UnidadMedida", namespaces=namespaces)[0].text)],
                limit=1).id
            total_amount = float(line.xpath("inv:MontoTotal", namespaces=namespaces)[0].text)

            discount_percentage = 0.0
            discount_note = None

            discount_node = line.xpath("inv:Descuento", namespaces=namespaces)
            if discount_node:
                discount_amount_node = discount_node[0].xpath("inv:MontoDescuento", namespaces=namespaces)[0]
                discount_amount = float(discount_amount_node.text or '0.0')
                discount_percentage = discount_amount / total_amount * 100
                discount_note = discount_node[0].xpath("inv:NaturalezaDescuento", namespaces=namespaces)[0].text
            else:
                discount_amount_node = line.xpath("inv:MontoDescuento", namespaces=namespaces)
                if discount_amount_node:
                    discount_amount = float(discount_amount_node[0].text or '0.0')
                    discount_percentage = discount_amount / total_amount * 100
                    discount_note = line.xpath("inv:NaturalezaDescuento", namespaces=namespaces)[0].text

            total_tax = 0.0
            taxes = self.env['account.tax']
            tax_nodes = line.xpath("inv:Impuesto", namespaces=namespaces)
            for tax_node in tax_nodes:
                tax = self.env['account.tax'].search(
                    [('tax_code', '=', re.sub(r"[^0-9]+", "", tax_node.xpath("inv:Codigo", namespaces=namespaces)[0].text)),
                    ('amount', '=', tax_node.xpath("inv:Tarifa", namespaces=namespaces)[0].text),
                    ('type_tax_use', '=', 'purchase')],
                    limit=1)
                if tax:
                    total_tax += float(tax_node.xpath("inv:Monto", namespaces=namespaces)[0].text)

                    # TODO: Add exonerations and exemptions

                    taxes += tax
                else:
                    raise UserError(_('Tax code %s and percentage %s is not registered in the system',
                                    tax_node.xpath("inv:Codigo", namespaces=namespaces)[0].text,
                                    tax_node.xpath("inv:Tarifa", namespaces=namespaces)[0].text))

            invoice_line = self.env['account.invoice.line'].create({
                'name': line.xpath("inv:Detalle", namespaces=namespaces)[0].text,
                'invoice_id': invoice.id,
                'price_unit': line.xpath("inv:PrecioUnitario", namespaces=namespaces)[0].text,
                'quantity': line.xpath("inv:Cantidad", namespaces=namespaces)[0].text,
                'uom_id': product_uom,
                'sequence': line.xpath("inv:NumeroLinea", namespaces=namespaces)[0].text,
                'discount': discount_percentage,
                'discount_note': discount_note,
                'total_amount': total_amount,
                'product_id': self.static_product_id.id,
                'account_id': self.account_id.id,
                'account_analytic_id': self.account_analytic_id.id,
            })

            # This must be assigned after line is created
            invoice_line.invoice_line_tax_ids = taxes
            invoice_line.total_tax = total_tax
            invoice_line.amount_untaxed = float(line.xpath("inv:SubTotal", namespaces=namespaces)[0].text)

            new_lines += invoice_line

        invoice.invoice_line_ids = new_lines

        invoice.amount_total_electronic_invoice = invoice_xml.xpath("inv:ResumenFactura/inv:TotalComprobante", namespaces=namespaces)[0].text

        tax_node = invoice_xml.xpath("inv:ResumenFactura/inv:TotalImpuesto", namespaces=namespaces)
        if tax_node:
            invoice.amount_tax_electronic_invoice = tax_node[0].text

        invoice.compute_taxes()
