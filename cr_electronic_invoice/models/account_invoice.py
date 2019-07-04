# -*- coding: utf-8 -*-

import base64
import datetime
import json
import logging
import re
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from . import api_facturae
from .. import extensions

_logger = logging.getLogger(__name__)


class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    @api.model
    def _get_invoice_id(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            return active_id
        return ''

    reference_code_id = fields.Many2one(
        comodel_name="reference.code", string="Código de referencia",
        required=True, )
    invoice_id = fields.Many2one(comodel_name="account.invoice",
                                 string="Documento de referencia",
                                 default=_get_invoice_id, required=False, )

    @api.multi
    def compute_refund(self, mode='refund'):
        if self.env.user.company_id.frm_ws_ambiente == 'disabled':
            result = super(AccountInvoiceRefund, self).compute_refund()
            return result
        else:
            inv_obj = self.env['account.invoice']
            inv_tax_obj = self.env['account.invoice.tax']
            inv_line_obj = self.env['account.invoice.line']
            context = dict(self._context or {})
            xml_id = False

            for form in self:
                created_inv = []
                for inv in inv_obj.browse(context.get('active_ids')):
                    if inv.state in ['draft', 'proforma2', 'cancel']:
                        raise UserError(
                            _(
                                'Cannot refund draft/proforma/cancelled invoice.'))
                    if inv.reconciled and mode in ('cancel', 'modify'):
                        raise UserError(_(
                            'Cannot refund invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.'))

                    date = form.date or False
                    description = form.description or inv.name
                    refund = inv.refund(form.date_invoice, date, description,
                                        inv.journal_id.id, form.invoice_id.id,
                                        form.reference_code_id.id)

                    created_inv.append(refund.id)

                    if mode in ('cancel', 'modify'):
                        movelines = inv.move_id.line_ids
                        to_reconcile_ids = {}
                        to_reconcile_lines = self.env['account.move.line']
                        for line in movelines:
                            if line.account_id.id == inv.account_id.id:
                                to_reconcile_lines += line
                                to_reconcile_ids.setdefault(
                                    line.account_id.id, []).append(line.id)
                            if line.reconciled:
                                line.remove_move_reconcile()

                        refund.payment_term_id = inv.payment_term_id
                        refund.action_invoice_open()
                        for tmpline in refund.move_id.line_ids:
                            if tmpline.account_id.id == inv.account_id.id:
                                to_reconcile_lines += tmpline
                        to_reconcile_lines.filtered(
                            lambda l: l.reconciled is False).reconcile()
                        if mode == 'modify':
                            invoice = inv.read(
                                inv_obj._get_refund_modify_read_fields())
                            invoice = invoice[0]
                            del invoice['id']
                            invoice_lines = inv_line_obj.browse(
                                invoice['invoice_line_ids'])
                            invoice_lines = inv_obj.with_context(
                                mode='modify')._refund_cleanup_lines(
                                invoice_lines)
                            tax_lines = inv_tax_obj.browse(
                                invoice['tax_line_ids'])
                            tax_lines = inv_obj._refund_cleanup_lines(
                                tax_lines)
                            invoice.update({
                                'type': inv.type,
                                'date_invoice': form.date_invoice,
                                'state': 'draft',
                                'number': False,
                                'invoice_line_ids': invoice_lines,
                                'tax_line_ids': tax_lines,
                                'date': date,
                                'origin': inv.origin,
                                'fiscal_position_id': inv.fiscal_position_id.id,
                                'invoice_id': inv.id,  # agregado
                                'reference_code_id': form.reference_code_id.id,
                                # agregado
                            })
                            for field in inv_obj._get_refund_common_fields():
                                if inv_obj._fields[field].type == 'many2one':
                                    invoice[field] = invoice[field] and \
                                                     invoice[field][0]
                                else:
                                    invoice[field] = invoice[field] or False
                            inv_refund = inv_obj.create(invoice)
                            if inv_refund.payment_term_id.id:
                                inv_refund._onchange_payment_term_date_invoice()
                            created_inv.append(inv_refund.id)

                    xml_id = (inv.type in ['out_refund',
                                           'out_invoice']) and 'action_invoice_tree1' or \
                             (inv.type in ['in_refund', 'in_invoice']
                              ) and 'action_invoice_tree2'
                    # Put the reason in the chatter
                    subject = _("Invoice refund")
                    body = description
                    refund.message_post(body=body, subject=subject)
            if xml_id:
                result = self.env.ref('account.%s' % (xml_id)).read()[0]
                invoice_domain = safe_eval(result['domain'])
                invoice_domain.append(('id', 'in', created_inv))
                result['domain'] = invoice_domain
                return result
            return True


class InvoiceLineElectronic(models.Model):
    _inherit = "account.invoice.line"

    total_amount = fields.Float(string="Monto total", required=False, )
    total_discount = fields.Float(string="Total descuento", required=False, )
    discount_note = fields.Char(string="Nota de descuento", required=False, )
    total_tax = fields.Float(string="Total impuesto", required=False, )

    third_party_id = fields.Many2one(comodel_name="res.partner",
                                     string="Tercero otros cargos",)

    tariff_head = fields.Char(string="Partida arancelaria para factura"
                                     " de exportación",
                              required=False, )

    categ_name = fields.Char(
        related='product_id.categ_id.name',
    )
    product_code = fields.Char(
        related='product_id.default_code',
    )


class AccountInvoiceElectronic(models.Model):
    _inherit = "account.invoice"

    number_electronic = fields.Char(
        string="Número electrónico", required=False, copy=False, index=True)
    date_issuance = fields.Char(
        string="Fecha de emisión", required=False, copy=False)
    consecutive_number_receiver = fields.Char(
        string="Número Consecutivo Receptor", required=False, copy=False,
        readonly=True, index=True)
    state_send_invoice = fields.Selection([('aceptado', 'Aceptado'),
                                           ('rechazado', 'Rechazado'),
                                           ('error', 'Error'),
                                           ('na', 'No Aplica'),
                                           ('ne', 'No Encontrado'),
                                           ('firma_invalida', 'Firma Inválida'),
                                           ('procesando', 'Procesando')],
                                          'Estado FE Proveedor')

    state_tributacion = fields.Selection([('aceptado', 'Aceptado'),
                                          ('rechazado', 'Rechazado'),
                                          ('recibido', 'Recibido'),
                                          ('firma_invalida', 'Firma Inválida'),
                                          ('error', 'Error'),
                                          ('procesando', 'Procesando'),
                                          ('na', 'No Aplica'),
                                          ('ne', 'No Encontrado')],
                                         'Estado FE',
                                         copy=False)

    state_invoice_partner = fields.Selection(
        [('1', 'Aceptado'), ('3', 'Rechazado'), ('2', 'Aceptacion parcial')],
        'Respuesta del Cliente')
    reference_code_id = fields.Many2one(
        comodel_name="reference.code", string="Código de referencia",
        required=False, )

    payment_methods_id = fields.Many2one(
        comodel_name="payment.methods", string="Métodos de Pago",
        required=False, )

    invoice_id = fields.Many2one(comodel_name="account.invoice",
                                 string="Documento de referencia",
                                 required=False,
                                 copy=False)
    xml_respuesta_tributacion = fields.Binary(
        string="Respuesta Tributación XML", required=False, copy=False,
        attachment=True)

    electronic_invoice_return_message = fields.Char(
        string='Respuesta Hacienda', readonly=True, )

    fname_xml_respuesta_tributacion = fields.Char(
        string="Nombre de archivo XML Respuesta Tributación", required=False,
        copy=False)
    xml_comprobante = fields.Binary(
        string="Comprobante XML", required=False, copy=False, attachment=True)
    fname_xml_comprobante = fields.Char(
        string="Nombre de archivo Comprobante XML", required=False, copy=False,
        attachment=True)
    xml_supplier_approval = fields.Binary(
        string="XML Proveedor", required=False, copy=False, attachment=True)
    fname_xml_supplier_approval = fields.Char(
        string="Nombre de archivo Comprobante XML proveedor", required=False,
        copy=False, attachment=True)
    amount_tax_electronic_invoice = fields.Monetary(
        string='Total de impuestos FE', readonly=True, )
    amount_total_electronic_invoice = fields.Monetary(
        string='Total FE', readonly=True, )
    tipo_documento = fields.Selection(
        selection=[('FE', 'Factura Electrónica'),
                   ('FEE', 'Factura Electrónica de Exportación'),
                   ('TE', 'Tiquete Electrónico'),
                   ('NC', 'Nota de Crédito'),
                   ('ND', 'Nota de Débito'),
                   ('CCE', 'MR Aceptación'),
                   ('CPCE', 'MR Aceptación Parcial'),
                   ('RCE', 'MR Rechazo'),
                   ('FEC', 'Factura Electrónica de Exportación')],
        string="Tipo Comprobante",
        required=False, default='FE',
        help='Indica el tipo de documento de acuerdo a la '
             'clasificación del Ministerio de Hacienda')

    sequence = fields.Char(string='Consecutivo', readonly=True, copy=False)

    state_email = fields.Selection([('no_email', 'Sin cuenta de correo'), (
        'sent', 'Enviado'), ('fe_error', 'Error FE')], 'Estado email',
                                   copy=False)

    invoice_amount_text = fields.Char(
        string='Monto en Letras', readonly=True, required=False, )

    ignore_total_difference = fields.Boolean(
        string="Ingorar Diferencia en Totales", required=False, default=False)

    error_count = fields.Integer(
        string="Cantidad de errores", required=False, default="0")

    _sql_constraints = [
        ('number_electronic_uniq', 'unique (company_id, number_electronic)',
         "La clave de comprobante debe ser única"),
    ]

    @api.multi
    def action_invoice_sent(self):
        self.ensure_one()

        invoice_id = self.id
        # context = dict(self._context or {})

        if self.invoice_id.type == 'in_invoice' or self.invoice_id.type == 'in_refund':
            email_template = self.env.ref(
                'cr_electronic_invoice.email_template_invoice_vendor', False)
        else:
            email_template = self.env.ref(
                'account.email_template_edi_invoice', False)

        email_template.attachment_ids = [(5)]

        if self.partner_id and self.partner_id.email:  # and not i.partner_id.opt_out:

            attachment = self.env['ir.attachment'].search(
                [('res_model', '=', 'account.invoice'),
                 ('res_id', '=', self.id),
                 ('res_field', '=', 'xml_comprobante')], limit=1)
            if attachment:
                attachment.name = self.fname_xml_comprobante
                attachment.datas_fname = self.fname_xml_comprobante

                attachment_resp = self.env['ir.attachment'].search(
                    [('res_model', '=', 'account.invoice'),
                     ('res_id', '=', self.id),
                     ('res_field', '=', 'xml_respuesta_tributacion')], limit=1)

                if attachment_resp:
                    attachment_resp.name = self.fname_xml_respuesta_tributacion
                    attachment_resp.datas_fname = self.fname_xml_respuesta_tributacion

                    email_template.attachment_ids = [
                        (6, 0, [attachment.id, attachment_resp.id])]

                    email_template.with_context(type='binary',
                                                default_type='binary').send_mail(
                        self.id,
                        raise_exception=False,
                        force_send=True)  # default_type='binary'

                    email_template.attachment_ids = [(5)]

                    self.write({
                        'invoice_mailed': True,
                        'sent': True,
                    })
                else:
                    raise UserError(
                        _('Response XML from Hacienda has not been received'))
            else:
                raise UserError(_('Invoice XML has not been generated'))
        else:
            raise UserError(_('Partner is not assigne to this invoice'))

    @api.onchange('xml_supplier_approval')
    def _onchange_xml_supplier_approval(self):
        if self.xml_supplier_approval:
            xml_decoded = base64.b64decode(self.xml_supplier_approval)
            try:
                factura = etree.fromstring(xml_decoded)
            except Exception as e:
                _logger.info(
                    'E-INV CR - This XML file is not XML-compliant.  Exception %s' % e)
                return {'status': 400,
                        'text': 'Excepción de conversión de XML'}

            pretty_xml_string = etree.tostring(
                factura, pretty_print=True,
                encoding='UTF-8', xml_declaration=True)
            _logger.error('E-INV CR - send_file XML: %s' % pretty_xml_string)
            namespaces = factura.nsmap
            inv_xmlns = namespaces.pop(None)
            namespaces['inv'] = inv_xmlns
            if not factura.xpath("inv:Clave", namespaces=namespaces):
                return {'value': {'xml_supplier_approval': False},
                        'warning': {'title': 'Atención',
                                    'message': 'El archivo xml no contiene el nodo Clave. '
                                               'Por favor cargue un archivo con el formato correcto.'}}

            if not factura.xpath("inv:FechaEmision", namespaces=namespaces):
                return {'value': {'xml_supplier_approval': False},
                        'warning': {'title': 'Atención',
                                    'message': 'El archivo xml no contiene el nodo FechaEmision. Por favor cargue un '
                                               'archivo con el formato correcto.'}}

            if not factura.xpath("inv:Emisor/inv:Identificacion/inv:Numero",
                                 namespaces=namespaces):
                return {'value': {'xml_supplier_approval': False},
                        'warning': {'title': 'Atención',
                                    'message': 'El archivo xml no contiene el nodo Emisor. Por favor '
                                               'cargue un archivo con el formato correcto.'}}

            if not factura.xpath("inv:ResumenFactura/inv:TotalComprobante",
                                 namespaces=namespaces):
                return {'value': {'xml_supplier_approval': False},
                        'warning': {'title': 'Atención',
                                    'message': 'No se puede localizar el nodo TotalComprobante. Por favor cargue '
                                               'un archivo con el formato correcto.'}}

        else:
            self.state_tributacion = False
            self.state_send_invoice = False
            self.xml_supplier_approval = False
            self.fname_xml_supplier_approval = False
            self.xml_respuesta_tributacion = False
            self.fname_xml_respuesta_tributacion = False
            self.date_issuance = False
            self.number_electronic = False
            self.state_invoice_partner = False

    @api.multi
    def load_xml_data(self):
        if (
                self.type == 'out_invoice' or self.type == 'out_refund') and self.xml_comprobante:
            # remove any character not a number digit in the invoice sequence
            self.sequence = re.sub(r"[^0-9]+", "", self.sequence)
            root = ET.fromstring(re.sub(' xmlns="[^"]+"', '', base64.b64decode(
                self.xml_comprobante).decode("utf-8"),
                                        count=1))  # noqa quita el namespace de los elementos

            partner_id = root.findall('Receptor')[0].find(
                'Identificacion')[1].text
            date_issuance = root.findall('FechaEmision')[0].text
            consecutive = root.findall('NumeroConsecutivo')[0].text

            partner = self.env['res.partner'].search(
                [('vat', '=', partner_id)])

            if partner and self.partner_id.id != partner.id:
                raise UserError('El cliente con identificación ' + partner_id +
                                ' no coincide con el cliente de esta factura: ' + self.partner_id.vat)
            elif str(self.date_invoice) != date_issuance:
                raise UserError('La fecha del XML () ' + date_issuance +
                                ' no coincide con la fecha de esta factura')
            elif self.sequence != consecutive:
                raise UserError('El número cosecutivo ' + consecutive +
                                ' no coincide con el de esta factura')
            else:
                self.number_electronic = root.findall('Clave')[0].text
                self.date_issuance = date_issuance
                self.date_invoice = date_issuance

        elif self.xml_supplier_approval:
            root = ET.fromstring(re.sub(' xmlns="[^"]+"', '', base64.b64decode(
                self.xml_supplier_approval).decode("utf-8"),
                                        count=1))

            xml_decoded = base64.b64decode(self.xml_supplier_approval)

            try:
                factura = etree.fromstring(xml_decoded)
            except Exception as e:
                # raise UserError(_(
                #    "This XML file is not XML-compliant. Error: %s") % e)
                _logger.error(
                    'MAB - This XML file is not XML-compliant.  Exception %s' % e)
                return {'status': 400,
                        'text': 'Excepción de conversión de XML'}

            pretty_xml_string = etree.tostring(
                factura, pretty_print=True, encoding='UTF-8',
                xml_declaration=True)

            _logger.info('Send_file XML: %s' % pretty_xml_string)

            namespaces = factura.nsmap
            inv_xmlns = namespaces.pop(None)
            namespaces['inv'] = inv_xmlns

            self.consecutive_number_receiver = factura.xpath(
                "inv:NumeroConsecutivo", namespaces=namespaces)[0].text

            self.reference = self.consecutive_number_receiver

            self.number_electronic = factura.xpath(
                "inv:Clave", namespaces=namespaces)[0].text
            self.date_issuance = factura.xpath(
                "inv:FechaEmision", namespaces=namespaces)[0].text
            emisor = factura.xpath(
                "inv:Emisor/inv:Identificacion/inv:Numero",
                namespaces=namespaces)[0].text
            receptor = factura.xpath(
                "inv:Receptor/inv:Identificacion/inv:Numero",
                namespaces=namespaces)[0].text

            if receptor != self.company_id.vat:
                raise UserError(
                    'El receptor no corresponde con la compañía actual con identificación ' + receptor + '. Por favor active la compañía correcta.')  # noqa

            date_time_obj = datetime.datetime.strptime(
                self.date_issuance, '%Y-%m-%dT%H:%M:%S-06:00')
            invoice_date = date_time_obj.date()

            self.date_invoice = invoice_date

            partner = self.env['res.partner'].search([('vat', '=', emisor),
                                                      ('supplier', '=', True),
                                                      '|',
                                                      ('company_id', '=',
                                                       self.company_id.id),
                                                      ('company_id', '=',
                                                       False)], limit=1)

            default_account_id = self.env['ir.config_parameter'].sudo(
            ).get_param('expense_account_id')

            if partner:
                self.partner_id = partner.id
            else:
                raise UserError('El proveedor con identificación ' + emisor +
                                ' no existe. Por favor creelo primero en el sistema.')

            lines = root.find('DetalleServicio').findall('LineaDetalle')

            new_lines = self.env['account.invoice.line']

            for line in lines:
                product_uom = self.env['uom.uom'].search(
                    [('code', '=', line.find('UnidadMedida').text)],
                    limit=1).id
                total_amount = float(line.find('MontoTotal').text)

                discount_percentage = 0.0
                discount_note = None
                discount_node = line.find('MontoDescuento')
                if discount_node:
                    discount_amount = float(discount_node.text or '0.0')
                    discount_percentage = discount_amount / total_amount * 100
                    discount_note = line.find('NaturalezaDescuento').text

                taxes = self.env['account.tax']
                tax_nodes = line.findall('Impuesto')
                total_tax = 0.0
                if tax_nodes:
                    for tax_node in tax_nodes:
                        if tax_node:
                            tax_amount = float(tax_node.find('Monto').text)
                            if tax_amount > 0:
                                tax = self.env['account.tax'].search(
                                    [('tax_code', '=', re.sub(r"[^0-9]+", "",
                                                              tax_node.find(
                                                                  'Codigo').text)),
                                     ('amount', '=',
                                      tax_node.find('Tarifa').text),
                                     ('type_tax_use', '=', 'purchase')],
                                    limit=1)
                                tax_amount = float(tax_node.find('Monto').text)
                                if tax and tax.amount == float(
                                        re.sub(r"[^0-9.]+", "",
                                               tax_node.find('Tarifa').text)):
                                    taxes += tax
                                    total_tax += tax_amount
                                else:
                                    raise UserError(
                                        'Un tipo de impuesto en el XML no existe en la configuración: ' + tax_node.find(
                                            'Codigo').text)
                            # TODO: insert exonerations

                invoice_line = self.env['account.invoice.line'].new({
                    'name': line.find('Detalle').text,
                    'invoice_id': self.id,
                    'price_unit': line.find('PrecioUnitario').text,
                    'quantity': line.find('Cantidad').text,
                    'uom_id': product_uom,
                    'sequence': line.find('NumeroLinea').text,
                    'discount': discount_percentage,
                    'discount_note': discount_note,
                    'total_amount': total_amount,
                    'amount_untaxed': float(line.find('SubTotal').text),
                    'invoice_line_tax_ids': taxes,
                    'total_tax': total_tax,
                    'account_id': default_account_id,
                })
                new_lines += invoice_line

            self.invoice_line_ids = new_lines

            # tax_node = root.findall('ResumenFactura')[0].findall('TotalImpuesto')
            tax_node = factura.xpath(
                "inv:ResumenFactura/inv:TotalImpuesto", namespaces=namespaces)

            if tax_node:
                self.amount_tax_electronic_invoice = tax_node[0].text
            # self.amount_total_electronic_invoice = root.findall('ResumenFactura')[0].findall('TotalComprobante')[0].text
            self.amount_total_electronic_invoice = factura.xpath(
                "inv:ResumenFactura/inv:TotalComprobante",
                namespaces=namespaces)[0].text
        self.compute_taxes()

    @api.multi
    def send_mrs_to_hacienda(self):
        for inv in self:
            if inv.xml_supplier_approval:

                '''Verificar si el MR ya fue enviado y estamos esperando la confirmación'''
                if inv.state_send_invoice == 'procesando':

                    token_m_h = api_facturae.get_token_hacienda(
                        inv, inv.company_id.frm_ws_ambiente)

                    api_facturae.consulta_documentos(self, inv,
                                                     inv.company_id.frm_ws_ambiente,
                                                     token_m_h,
                                                     api_facturae.get_time_hacienda(),
                                                     False)
                else:

                    if inv.state_send_invoice and inv.state_send_invoice in (
                            'aceptado', 'rechazado', 'na'):
                        raise UserError(
                            'Aviso!.\n La factura de proveedor ya fue confirmada')

                    if abs(
                            self.amount_total_electronic_invoice - self.amount_total) > 1:
                        inv.message_post(
                            subject='Error',
                            body='Aviso!.\n Monto total no concuerda con monto del XML')
                        continue
                        raise UserError(
                            'Aviso!.\n Monto total no concuerda con monto del XML')

                    elif not inv.xml_supplier_approval:
                        inv.message_post(
                            subject='Error',
                            body='Aviso!.\n No se ha cargado archivo XML')
                        continue
                        raise UserError(
                            'Aviso!.\n No se ha cargado archivo XML')

                    elif not inv.company_id.sucursal_MR or not inv.company_id.terminal_MR:
                        inv.state_send_invoice = 'error'
                        inv.message_post(subject='Error',
                                         body='Aviso!.\nPor favor configure el diario de compras, terminal y sucursal')
                        continue
                        # raise UserError('Aviso!.\nPor favor configure el diario de compras, terminal y sucursal')

                    if not inv.state_invoice_partner:
                        inv.state_send_invoice = 'error'
                        inv.message_post(subject='Error',
                                         body='Aviso!.\nDebe primero seleccionar el tipo de respuesta para el archivo cargado.')
                        continue
                        # raise UserError('Aviso!.\nDebe primero seleccionar el tipo de respuesta para .'
                        #                'el archivo cargado.')

                    if inv.company_id.frm_ws_ambiente != 'disabled' and inv.state_invoice_partner:

                        # url = self.company_id.frm_callback_url
                        message_description = "<p><b>Enviando Mensaje Receptor</b></p>"

                        '''Si por el contrario es un documento nuevo, asignamos todos los valores'''
                        if not inv.xml_comprobante or inv.state_invoice_partner not in ['procesando', 'aceptado']:

                            if inv.state_invoice_partner == '1':
                                detalle_mensaje = 'Aceptado'
                                tipo = 1
                                tipo_documento = 'CCE'
                                sequence = inv.company_id.CCE_sequence_id.next_by_id()

                            elif inv.state_invoice_partner == '2':
                                detalle_mensaje = 'Aceptado parcial'
                                tipo = 2
                                tipo_documento = 'CPCE'
                                sequence = inv.company_id.CPCE_sequence_id.next_by_id()
                            else:
                                detalle_mensaje = 'Rechazado'
                                tipo = 3
                                tipo_documento = 'RCE'
                                sequence = inv.company_id.RCE_sequence_id.next_by_id()

                            '''Si el mensaje fue rechazado, necesitamos generar un nuevo id'''
                            if inv.state_send_invoice == 'rechazado' or inv.state_send_invoice == 'error':
                                message_description += '<p><b>Cambiando consecutivo del Mensaje de Receptor</b> <br />' \
                                                       '<b>Consecutivo anterior: </b>' + inv.consecutive_number_receiver + \
                                                       '<br/>' \
                                                       '<b>Estado anterior: </b>' + inv.state_send_invoice + '</p>'

                            '''Solicitamos la clave para el Mensaje Receptor'''
                            response_json = api_facturae.get_clave_hacienda(
                                self, tipo_documento, sequence,
                                inv.company_id.sucursal_MR,
                                inv.company_id.terminal_MR)

                            inv.consecutive_number_receiver = response_json.get(
                                'consecutivo')
                            '''Generamos el Mensaje Receptor'''

                            if inv.company_id.version_hacienda == '4.2':
                                xml = api_facturae.gen_xml_mr_42(
                                    inv.number_electronic,
                                    inv.partner_id.vat, inv.date_issuance,
                                    tipo, detalle_mensaje, inv.company_id.vat,
                                    inv.consecutive_number_receiver,
                                    inv.amount_tax_electronic_invoice,
                                    inv.amount_total_electronic_invoice)
                            else:
                                xml = api_facturae.gen_xml_mr_43(
                                    inv.number_electronic, inv.partner_id.vat,
                                    inv.date_issuance,
                                    tipo, detalle_mensaje, inv.company_id.vat,
                                    inv.consecutive_number_receiver,
                                    inv.amount_tax_electronic_invoice,
                                    inv.amount_total_electronic_invoice,
                                    inv.company_id.activity_id.code,
                                    '01')

                            xml_firmado = api_facturae.sign_xml(
                                inv.company_id.signature,
                                inv.company_id.frm_pin, xml)

                            inv.fname_xml_comprobante = tipo_documento + '_' + inv.number_electronic + '.xml'

                            inv.xml_comprobante = base64.encodestring(xml_firmado)
                            inv.tipo_documento = tipo_documento

                            if inv.state_send_invoice != 'procesando':

                                env = inv.company_id.frm_ws_ambiente
                                token_m_h = api_facturae.get_token_hacienda(
                                    inv, inv.company_id.frm_ws_ambiente)

                                response_json = api_facturae.send_message(
                                    inv, api_facturae.get_time_hacienda(),
                                    xml_firmado,
                                    token_m_h, env)
                                status = response_json.get('status')

                                if 200 <= status <= 299:
                                    inv.state_send_invoice = 'procesando'
                                else:
                                    inv.state_send_invoice = 'error'
                                    _logger.error(
                                        'E-INV CR - Invoice: %s  Error sending Acceptance Message: %s',
                                        inv.number_electronic,
                                        response_json.get('text'))

                                if inv.state_send_invoice == 'procesando':
                                    token_m_h = api_facturae.get_token_hacienda(
                                        inv, inv.company_id.frm_ws_ambiente)

                                    if not token_m_h:
                                        _logger.error(
                                            'E-INV CR - Send Acceptance Message - HALTED - Failed to get token')
                                        return

                                    _logger.error(
                                        'E-INV CR - send_mrs_to_hacienda - 013')

                                    response_json = api_facturae.consulta_clave(
                                        inv.number_electronic + '-' + inv.consecutive_number_receiver,
                                        token_m_h,
                                        inv.company_id.frm_ws_ambiente)
                                    status = response_json['status']

                                    if status == 200:
                                        inv.state_send_invoice = response_json.get(
                                            'ind-estado')
                                        inv.xml_respuesta_tributacion = response_json.get(
                                            'respuesta-xml')
                                        inv.fname_xml_respuesta_tributacion = 'ACH_' + \
                                                                              inv.number_electronic + '-' + inv.consecutive_number_receiver + '.xml'

                                        _logger.error(
                                            'E-INV CR - Estado Documento:%s',
                                            inv.state_send_invoice)

                                        message_description += '<p><b>Ha enviado Mensaje de Receptor</b>' + \
                                                               '<br /><b>Documento: </b>' + inv.number_electronic + \
                                                               '<br /><b>Consecutivo de mensaje: </b>' + \
                                                               inv.consecutive_number_receiver + \
                                                               '<br/><b>Mensaje indicado:</b>' \
                                                               + detalle_mensaje + '</p>'

                                        self.message_post(
                                            body=message_description,
                                            subtype='mail.mt_note',
                                            content_subtype='html')

                                        _logger.info(
                                            'E-INV CR - Estado Documento:%s',
                                            inv.state_send_invoice)

                                    elif status == 400:
                                        inv.state_send_invoice = 'ne'
                                        _logger.error(
                                            'MAB - Aceptacion Documento:%s no encontrado en Hacienda.',
                                            inv.number_electronic + '-' + inv.consecutive_number_receiver)
                                    else:
                                        _logger.error(
                                            'MAB - Error inesperado en Send Acceptance File - Abortando')
                                        return

    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None,
               journal_id=None, invoice_id=None,
               reference_code_id=None):
        if self.env.user.company_id.frm_ws_ambiente == 'disabled':
            new_invoices = super(AccountInvoiceElectronic, self).refund()
            return new_invoices
        else:
            new_invoices = self.browse()
            for invoice in self:
                # create the new invoice
                values = self._prepare_refund(
                    invoice, date_invoice=date_invoice, date=date,
                    description=description, journal_id=journal_id)
                values.update({'invoice_id': invoice_id,
                               'reference_code_id': reference_code_id})
                refund_invoice = self.create(values)
                invoice_type = {
                    'out_invoice': ('customer invoices refund'),
                    'in_invoice': ('vendor bill refund'),
                    'out_refund': ('customer refund refund'),
                    'in_refund': ('vendor refund refund')
                }
                message = _(
                    "This %s has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>") % (
                              invoice_type[invoice.type], invoice.id,
                              invoice.number)
                refund_invoice.message_post(body=message)
                refund_invoice.payment_methods_id = invoice.payment_methods_id
                new_invoices += refund_invoice
            return new_invoices

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        super(AccountInvoiceElectronic, self)._onchange_partner_id()
        self.payment_methods_id = self.partner_id.payment_methods_id

        if self.partner_id and self.partner_id.identification_id and self.partner_id.vat:
            if self.partner_id.country_id.code == 'CR':
                self.tipo_documento = 'FE'
            else:
                self.tipo_documento = 'FEE'
        else:
            self.tipo_documento = 'TE'

    @api.model
    # cron Job that verifies if the invoices are Validated at Tributación
    def _check_hacienda_for_invoices(self, max_invoices=10):
        out_invoices = self.env['account.invoice'].search(
            [('type', 'in', ('out_invoice', 'out_refund')),
             ('state', 'in', ('open', 'paid')),
             ('state_tributacion', 'in', ('recibido', 'procesando', 'ne', 'error'))])

        in_invoices = self.env['account.invoice'].search(
            [('type', '=', 'in_invoice'),
             ('tipo_documento', '=', 'FEC'),
             ('state', 'in', ('open', 'paid')),
             ('state_send_invoice', 'in', ('procesando', 'ne', 'error'))])

        invoices = out_invoices | in_invoices

        total_invoices = len(invoices)
        current_invoice = 0

        for i in invoices:
            current_invoice += 1

            token_m_h = api_facturae.get_token_hacienda(
                i, i.company_id.frm_ws_ambiente)
            if not token_m_h:
                _logger.error(
                    'E-INV CR - Consulta Hacienda - HALTED - Failed to get token')
                return

            if i.number_electronic and len(i.number_electronic) == 50:
                response_json = api_facturae.consulta_clave(
                    i.number_electronic, token_m_h,
                    i.company_id.frm_ws_ambiente)
                status = response_json['status']

                if status == 200:
                    estado_m_h = response_json.get('ind-estado')
                    _logger.info('E-INV CR - Estado Documento:%s', estado_m_h)
                elif status == 400:
                    estado_m_h = response_json.get('ind-estado')
                    i.state_tributacion = 'ne'
                    _logger.warning(
                        'E-INV CR - Documento:%s no encontrado en Hacienda.  Estado: %s',
                        i.number_electronic, estado_m_h)
                    continue
                else:
                    _logger.error(
                        'E-INV CR - Error inesperado en Consulta Hacienda - Abortando')
                    return
                if i.type == 'in_invoice':
                    i.state_send_invoice = estado_m_h
                else:
                    i.state_tributacion = estado_m_h

                if estado_m_h == 'aceptado':
                    i.fname_xml_respuesta_tributacion = 'AHC_' + i.number_electronic + '.xml'
                    i.xml_respuesta_tributacion = response_json.get(
                        'respuesta-xml')

                    if i.tipo_documento != 'FEC' and i.partner_id and i.partner_id.email:  # and not i.partner_id.opt_out:
                        email_template = self.env.ref(
                            'account.email_template_edi_invoice', False)
                        attachment = self.env['ir.attachment'].search(
                            [('res_model', '=', 'account.invoice'),
                             ('res_id', '=', i.id),
                             ('res_field', '=', 'xml_comprobante')], limit=1)
                        attachment.name = i.fname_xml_comprobante
                        attachment.datas_fname = i.fname_xml_comprobante
                        attachment.mimetype = 'text/xml'

                        attachment_resp = self.env['ir.attachment'].search(
                            [('res_model', '=', 'account.invoice'),
                             ('res_id', '=', i.id),
                             ('res_field', '=', 'xml_respuesta_tributacion')],
                            limit=1)
                        attachment_resp.name = i.fname_xml_respuesta_tributacion
                        attachment_resp.datas_fname = i.fname_xml_respuesta_tributacion
                        attachment_resp.mimetype = 'text/xml'

                        email_template.attachment_ids = [
                            (6, 0, [attachment.id, attachment_resp.id])]

                        email_template.with_context(type='binary',
                                                    default_type='binary').send_mail(
                            i.id,
                            raise_exception=False,
                            force_send=True)  # default_type='binary'

                        email_template.attachment_ids = [(5)]

                elif estado_m_h in ('firma_invalida'):
                    if i.error_count > 10:
                        i.fname_xml_respuesta_tributacion = 'AHC_' + i.number_electronic + '.xml'
                        i.xml_respuesta_tributacion = response_json.get('respuesta-xml')
                        i.state_email = 'fe_error'
                        _logger.info('email no enviado - factura rechazada')
                    else:
                        i.error_count += 1
                        i.state_tributacion = 'procesando'

                elif estado_m_h == 'rechazado':
                    i.state_email = 'fe_error'
                    i.state_tributacion = estado_m_h
                    i.fname_xml_respuesta_tributacion = 'AHC_' + i.number_electronic + '.xml'
                    i.xml_respuesta_tributacion = response_json.get(
                        'respuesta-xml')
                elif estado_m_h == 'error':
                    i.state_tributacion = estado_m_h

    @api.multi
    def action_check_hacienda(self):
        if self.company_id.frm_ws_ambiente != 'disabled':
            for inv in self:
                token_m_h = api_facturae.get_token_hacienda(
                    inv, inv.company_id.frm_ws_ambiente)
                api_facturae.consulta_documentos(
                    self, inv, self.company_id.frm_ws_ambiente, token_m_h,
                    False, False)

    @api.model
    def _check_hacienda_for_mrs(self, max_invoices=10):  # cron
        invoices = self.env['account.invoice'].search(
            [('type', 'in', ('in_invoice', 'in_refund')),
             ('state', 'in',
              ('open', 'paid')),
             ('xml_supplier_approval',
              '!=', False),
             ('state_invoice_partner',
              '!=', False),
             ('state_send_invoice', 'not in',
              ('aceptado', 'rechazado', 'error', 'na'))],
            limit=max_invoices)
        total_invoices = len(invoices)
        current_invoice = 0

        for inv in invoices:
            # CWong: esto no debe llamarse porque cargaría de nuevo los impuestos y ya se pusieron como debería
            # current_invoice += 1
            # if not i.amount_total_electronic_invoice:
            #     i.charge_xml_data()
            #     _logger.info(
            #         'MAB - Confirma Hacienda - Invoice %s / %s  -  number:%s',
            #         current_invoice,
            #         total_invoices, i.number_electronic)
            inv.send_mrs_to_hacienda()

    @api.multi
    def action_create_fec(self):
        self.generate_and_send_invoices(self)

    @api.model
    def _send_invoices_to_hacienda(self, max_invoices=10):  # cron
        _logger.info('FECR - Ejecutando Valida Hacienda')
        invoices = self.env['account.invoice'].search([('type', 'in', ('out_invoice', 'out_refund')),
                                                      ('state', 'in', ('open', 'paid')),
                                                      ('number_electronic', '!=', False),
                                                      ('date_invoice', '>=', '2018-10-01'),
                                                      '|', ('state_tributacion', '=', False),('state_tributacion', '=', 'ne')],
                                                      order='number', limit=max_invoices)
        self.generate_and_send_invoices(invoices)

    @api.multi
    def generate_and_send_invoices(self, invoices):
        total_invoices = len(invoices)
        current_invoice = 0

        for inv in invoices:
            current_invoice += 1

            if not inv.sequence.isdigit():  # or (len(inv.number) == 10):
                inv.state_tributacion = 'na'
                continue

            if not inv.xml_comprobante:
                date_cr = api_facturae.get_time_hacienda()

                numero_documento_referencia = ''
                fecha_emision_referencia = ''
                codigo_referencia = ''
                razon_referencia = ''
                currency = inv.currency_id
                invoice_comments = inv.comment

                # Es Factura de cliente o nota de débito
                if inv.type == 'out_invoice':
                    if inv.tipo_documento == 'ND':

                        numero_documento_referencia = inv.invoice_id.number_electronic
                        tipo_documento_referencia = inv.invoice_id.number_electronic[29:31]
                        fecha_emision_referencia = inv.invoice_id.date_issuance
                        codigo_referencia = inv.reference_code_id.code
                        razon_referencia = inv.reference_code_id.name
                    else:
                        tipo_documento_referencia = ''

                # Si es Nota de Crédito
                elif inv.tipo_documento == 'NC':
                    codigo_referencia = inv.reference_code_id.code
                    razon_referencia = inv.reference_code_id.name

                    if inv.invoice_id.number_electronic:
                        numero_documento_referencia = inv.invoice_id.number_electronic
                        tipo_documento_referencia = inv.invoice_id.number_electronic[29:31]
                        fecha_emision_referencia = inv.invoice_id.date_issuance
                    else:
                        numero_documento_referencia = inv.invoice_id and re.sub('[^0-9]+', '', inv.invoice_id.sequence).rjust(50, '0') or '0000000'
                        tipo_documento_referencia = '99'
                        date_invoice = datetime.datetime.strptime(inv.invoice_id and inv.invoice_id.date_invoice or '2018-08-30', "%Y-%m-%d")
                        fecha_emision_referencia = date_invoice.strftime("%Y-%m-%d") + "T12:00:00-06:00"

                if inv.payment_term_id:
                    sale_conditions = inv.payment_term_id.sale_conditions_id and inv.payment_term_id.sale_conditions_id.sequence or '01'
                else:
                    sale_conditions = '01'

                # Validate if invoice currency is the same as the company currency
                if currency.name == self.company_id.currency_id.name:
                    currency_rate = 1
                else:
                    currency_rate = round(1.0 / currency.rate, 5)

                # Generamos las líneas de la factura
                lines = dict()
                otros_cargos = dict()
                otros_cargos_id = 0
                line_number = 0
                total_otros_cargos = 0.0
                total_servicio_gravado = 0.0
                total_servicio_exento = 0.0
                total_servicio_exonerado = 0.0
                total_mercaderia_gravado = 0.0
                total_mercaderia_exento = 0.0
                total_mercaderia_exonerado = 0.0
                total_descuento = 0.0
                total_impuestos = 0.0
                base_subtotal = 0.0
                for inv_line in inv.invoice_line_ids:
                    # Revisamos si está línea es de Otros Cargos
                    if inv_line.product_id.categ_id.name == 'Otros Cargos':
                        otros_cargos_id += 1
                        otros_cargos[otros_cargos_id]= {
                            'TipoDocumento': inv_line.product_id.default_code,
                            'Detalle': escape(inv_line.name[:150]),
                            'MontoCargo': inv_line.total_amount
                        }
                        if inv_line.third_party_id:
                            otros_cargos[otros_cargos_id]['NombreTercero'] = inv_line.third_party_id.name
                            
                            if inv_line.third_party_id.vat:
                                otros_cargos[otros_cargos_id]['NumeroIdentidadTercero'] = inv_line.third_party_id.vat

                        total_otros_cargos += inv_line.total_amount

                    else:

                        line_number += 1
                        price = inv_line.price_unit
                        quantity = inv_line.quantity
                        if not quantity:
                            continue

                        line_taxes = inv_line.invoice_line_tax_ids.compute_all(
                            price, currency, 1,
                            product=inv_line.product_id,
                            partner=inv_line.invoice_id.partner_id)

                        price_unit = round(line_taxes['total_excluded'], 5)

                        base_line = round(price_unit * quantity, 5)
                        descuento = inv_line.discount and round(
                            price_unit * quantity * inv_line.discount / 100.0,
                            5) or 0.0

                        subtotal_line = round(base_line - descuento, 5)

                        # Corregir error cuando un producto trae en el nombre "", por ejemplo: "disco duro"
                        # Esto no debería suceder, pero, si sucede, lo corregimos
                        if inv_line.name[:156].find('"'):
                            detalle_linea = inv_line.name[:160].replace(
                                '"', '')

                        line = {
                            "cantidad": quantity,
                            "detalle": escape(detalle_linea),
                            "precioUnitario": price_unit,
                            "montoTotal": base_line,
                            "subtotal": subtotal_line,
                            "BaseImponible": subtotal_line,
                        }

                        if inv_line.product_id:
                            line["unidadMedida"] = inv_line.product_id.uom_id.code or 'Sp'
                            line["codigo"] = inv_line.product_id.default_code or ''
                            line["codigoProducto"] = inv_line.product_id.code or ''
                        
                        if inv.tipo_documento == 'FEE' and inv_line.tariff_head:
                            line["partidaArancelaria"] = inv_line.tariff_head

                        if inv_line.discount:
                            # descuento = round(base_line - subtotal_line, 5)
                            total_descuento += descuento
                            line["montoDescuento"] = descuento
                            line[
                                "naturalezaDescuento"] = inv_line.discount_note or 'Descuento Comercial'

                        # Se generan los impuestos
                        taxes = dict()
                        _line_tax = 0.0
                        _tax_exoneration = False
                        _percentage_exoneration = 0
                        if inv_line.invoice_line_tax_ids:
                            tax_index = 0

                            taxes_lookup = {}
                            for i in inv_line.invoice_line_tax_ids:
                                if i.has_exoneration:
                                    _tax_exoneration = i.has_exoneration
                                    taxes_lookup[i.id] = {'tax_code': i.tax_root.tax_code,
                                                          'tarifa': i.tax_root.amount,
                                                          'iva_tax_desc': i.tax_root.iva_tax_desc,
                                                          'iva_tax_code': i.tax_root.iva_tax_code,
                                                          'exoneration_percentage': i.percentage_exoneration,
                                                          'amount_exoneration': i.amount}
                                else:
                                    taxes_lookup[i.id] = {'tax_code': i.tax_code,
                                                          'tarifa': i.amount,
                                                          'iva_tax_desc': i.iva_tax_desc,
                                                          'iva_tax_code': i.iva_tax_code}

                            for i in line_taxes['taxes']:
                                if taxes_lookup[i['id']]['tax_code'] != '00':
                                    tax_index += 1
                                    # tax_amount = round(i['amount'], 5) * quantity
                                    tax_amount = round(
                                        subtotal_line * taxes_lookup[i['id']][
                                            'tarifa'] / 100, 5)
                                    _line_tax += tax_amount
                                    tax = {
                                        'codigo': taxes_lookup[i['id']][
                                            'tax_code'],
                                        'tarifa': taxes_lookup[i['id']][
                                            'tarifa'],
                                        'monto': tax_amount,
                                        'iva_tax_desc': taxes_lookup[i['id']][
                                            'iva_tax_desc'],
                                        'iva_tax_code': taxes_lookup[i['id']][
                                            'iva_tax_code'],
                                    }
                                    # Se genera la exoneración si existe para este impuesto
                                    if _tax_exoneration:
                                        _tax_amount_exoneration = round(
                                            subtotal_line * taxes_lookup[i['id']][
                                                'amount_exoneration'] / 100, 5)

                                        if _tax_amount_exoneration == 0.0 :
                                            _tax_amount_exoneration = tax_amount

                                        _line_tax -= _tax_amount_exoneration
                                        _percentage_exoneration = int(
                                                taxes_lookup[i['id']]['exoneration_percentage'])/100
                                        tax["exoneracion"] = {
                                            "montoImpuesto": _tax_amount_exoneration,
                                            "porcentajeCompra": int(
                                                taxes_lookup[i['id']]['exoneration_percentage'])
                                        }

                                    taxes[tax_index] = tax

                            line["impuesto"] = taxes
                            line["impuestoNeto"] = _line_tax

                        # Si no hay product_id se asume como mercaderia
                        if inv_line.product_id and inv_line.product_id.type == 'service':
                            if taxes:
                                if _tax_exoneration:
                                    if _percentage_exoneration < 1:
                                        total_servicio_gravado += (base_line * _percentage_exoneration)
                                    total_servicio_exonerado += (base_line * _percentage_exoneration)

                                else:
                                    total_servicio_gravado += base_line

                                total_impuestos += _line_tax
                            else:
                                total_servicio_exento += base_line
                        else:
                            if taxes:
                                if _tax_exoneration:
                                    if _percentage_exoneration < 1:
                                        total_mercaderia_gravado += (base_line * _percentage_exoneration)
                                    total_mercaderia_exonerado += (base_line * _percentage_exoneration)

                                else:
                                    total_mercaderia_gravado += base_line

                                total_impuestos += _line_tax
                            else:
                                total_mercaderia_exento += base_line

                        base_subtotal += subtotal_line

                        line[
                            "montoTotalLinea"] = round(subtotal_line + _line_tax, 5)

                        lines[line_number] = line

                # convertir el monto de la factura a texto
                inv.invoice_amount_text = extensions.text_converter.number_to_text_es(
                    base_subtotal + total_impuestos)
                inv.date_issuance = date_cr

                # TODO: CORREGIR BUG NUMERO DE FACTURA NO SE GUARDA EN LA REFERENCIA DE LA NC CUANDO SE CREA MANUALMENTE
                if not inv.origin:
                    inv.origin = inv.invoice_id.display_name

                if inv.tipo_documento == 'FE':
                    # ESTE METODO GENERA EL XML DIRECTAMENTE DESDE PYTHON
                    if inv.company_id.version_hacienda == '4.2':
                        xml_string_builder = api_facturae.gen_xml_fe_v42(inv,
                                                                         sale_conditions,
                                                                         round(
                                                                             total_servicio_gravado,
                                                                             5),
                                                                         round(
                                                                             total_servicio_exento,
                                                                             5),
                                                                         round(
                                                                             total_mercaderia_gravado,
                                                                             5),
                                                                         round(
                                                                             total_mercaderia_exento,
                                                                             5),
                                                                         base_subtotal,
                                                                         total_impuestos,
                                                                         total_descuento,
                                                                         json.dumps(
                                                                             lines,
                                                                             ensure_ascii=False),
                                                                         currency_rate,
                                                                         invoice_comments)
                    else:
                        xml_string_builder = api_facturae.gen_xml_fe_v43(
                            inv=inv,
                            sale_conditions=sale_conditions,
                            total_servicio_gravado=round(
                                total_servicio_gravado, 5),
                            total_servicio_exento=round(
                                total_servicio_exento, 5),
                            totalServExonerado=total_servicio_exonerado,
                            total_mercaderia_gravado=round(
                                total_mercaderia_gravado, 5),
                            total_mercaderia_exento=round(
                                total_mercaderia_exento, 5),
                            totalMercExonerada=total_mercaderia_exonerado,
                            totalOtrosCargos=total_otros_cargos,
                            base_total=base_subtotal,
                            total_impuestos=total_impuestos,
                            total_descuento=total_descuento,
                            lines=json.dumps(
                                lines, ensure_ascii=False),
                            otrosCargos=otros_cargos,
                            currency_rate=currency_rate,
                            invoice_comments=invoice_comments)

                elif inv.tipo_documento == 'FEC':            
                    xml_string_builder = api_facturae.gen_xml_fec_v43(
                            inv=inv,
                            sale_conditions=sale_conditions,
                            total_servicio_gravado=round(
                                total_servicio_gravado, 5),
                            total_servicio_exento=round(
                                total_servicio_exento, 5),
                            totalServExonerado=total_servicio_exonerado,
                            total_mercaderia_gravado=round(
                                total_mercaderia_gravado, 5),
                            total_mercaderia_exento=round(
                                total_mercaderia_exento, 5),
                            totalMercExonerada=total_mercaderia_exonerado,
                            totalOtrosCargos=total_otros_cargos,
                            base_total=base_subtotal,
                            total_impuestos=total_impuestos,
                            total_descuento=total_descuento,
                            lines=json.dumps(
                                lines, ensure_ascii=False),
                            otrosCargos=otros_cargos,
                            currency_rate=currency_rate,
                            invoice_comments=invoice_comments)

                elif inv.tipo_documento == 'FEE':
                    xml_string_builder = api_facturae.gen_xml_fee_v43(
                            inv=inv,
                            sale_conditions=sale_conditions,
                            total_servicio_gravado=round(
                                total_servicio_gravado, 5),
                            total_servicio_exento=round(
                                total_servicio_exento, 5),
                            totalServExonerado=total_servicio_exonerado,
                            total_mercaderia_gravado=round(
                                total_mercaderia_gravado, 5),
                            total_mercaderia_exento=round(
                                total_mercaderia_exento, 5),
                            totalMercExonerada=total_mercaderia_exonerado,
                            totalOtrosCargos=total_otros_cargos,
                            base_total=base_subtotal,
                            total_impuestos=total_impuestos,
                            total_descuento=total_descuento,
                            lines=json.dumps(
                                lines, ensure_ascii=False),
                            otrosCargos=otros_cargos,
                            currency_rate=currency_rate,
                            invoice_comments=invoice_comments)

                elif inv.tipo_documento == 'TE':
                    if inv.company_id.version_hacienda == '4.2':
                        xml_string_builder = api_facturae.gen_xml_te_42(inv,
                                                                     sale_conditions,
                                                                     round(
                                                                         total_servicio_gravado,
                                                                         5),
                                                                     round(
                                                                         total_servicio_exento,
                                                                         5),
                                                                     round(
                                                                         total_mercaderia_gravado,
                                                                         5),
                                                                     round(
                                                                         total_mercaderia_exento,
                                                                         5),
                                                                     base_subtotal,
                                                                     total_impuestos,
                                                                     total_descuento,
                                                                     json.dumps(
                                                                         lines,
                                                                         ensure_ascii=False),
                                                                     currency_rate,
                                                                     invoice_comments)
                    else:
                        xml_string_builder = api_facturae.gen_xml_te_43(inv,
                                                                     sale_conditions,
                                                                     round(
                                                                         total_servicio_gravado,
                                                                         5),
                                                                     round(
                                                                         total_servicio_exento,
                                                                         5),
                                                                         total_servicio_exonerado,
                                                                     round(
                                                                         total_mercaderia_gravado,
                                                                         5),
                                                                     round(
                                                                         total_mercaderia_exento,
                                                                         5),
                                                                         total_mercaderia_exonerado,
                                                                         total_otros_cargos,
                                                                     base_subtotal,
                                                                     total_impuestos,
                                                                     total_descuento,
                                                                     json.dumps(
                                                                         lines,
                                                                         ensure_ascii=False),
                                                                     currency_rate,
                                                                     invoice_comments,
                                                                        otros_cargos)


                elif inv.tipo_documento == 'NC':

                    if inv.company_id.version_hacienda == '4.2':
                        xml_string_builder = api_facturae.gen_xml_nc(inv,
                                                                     sale_conditions,
                                                                     round(
                                                                         total_servicio_gravado,
                                                                         5),
                                                                     round(
                                                                         total_servicio_exento,
                                                                         5),
                                                                     round(
                                                                         total_mercaderia_gravado,
                                                                         5),
                                                                     round(
                                                                         total_mercaderia_exento,
                                                                         5),
                                                                     base_subtotal,
                                                                     total_impuestos,
                                                                     total_descuento,
                                                                     json.dumps(
                                                                         lines,
                                                                         ensure_ascii=False),
                                                                     tipo_documento_referencia,
                                                                     numero_documento_referencia,
                                                                     fecha_emision_referencia,
                                                                     codigo_referencia,
                                                                     razon_referencia,
                                                                     currency_rate,
                                                                     invoice_comments)
                    else:
                        xml_string_builder = api_facturae.gen_xml_nc_v43(inv,
                                                                         sale_conditions,
                                                                         round(
                                                                             total_servicio_gravado,
                                                                             5),
                                                                         round(
                                                                             total_servicio_exento,
                                                                             5),
                                                                             total_servicio_exonerado,
                                                                         round(
                                                                             total_mercaderia_gravado,
                                                                             5),
                                                                         round(
                                                                             total_mercaderia_exento,
                                                                             5),
                                                                         total_mercaderia_exonerado,
                                                                         total_otros_cargos,
                                                                         base_subtotal,
                                                                         total_impuestos,
                                                                         total_descuento,
                                                                         json.dumps(
                                                                             lines,
                                                                             ensure_ascii=False),
                                                                         tipo_documento_referencia,
                                                                         numero_documento_referencia,
                                                                         fecha_emision_referencia,
                                                                         codigo_referencia,
                                                                         razon_referencia,
                                                                         currency_rate,
                                                                         invoice_comments,
                                                                         otros_cargos)

                else:
                    if inv.company_id.version_hacienda == '4.2':
                        xml_string_builder = api_facturae.gen_xml_nd(inv,
                                                                     sale_conditions,
                                                                     round(
                                                                         total_servicio_gravado,
                                                                         5),
                                                                     round(
                                                                         total_servicio_exento,
                                                                         5),
                                                                     round(
                                                                         total_mercaderia_gravado,
                                                                         5),
                                                                     round(
                                                                         total_mercaderia_exento,
                                                                         5),
                                                                     base_subtotal,
                                                                     total_impuestos,
                                                                     total_descuento,
                                                                     json.dumps(
                                                                         lines,
                                                                         ensure_ascii=False),
                                                                     tipo_documento_referencia,
                                                                     numero_documento_referencia,
                                                                     fecha_emision_referencia,
                                                                     codigo_referencia,
                                                                     razon_referencia,
                                                                     currency_rate,
                                                                     invoice_comments)
                    else:
                        xml_string_builder = api_facturae.gen_xml_nd_v43(inv,
                                                                         sale_conditions,
                                                                         round(
                                                                             total_servicio_gravado,
                                                                             5),
                                                                         round(
                                                                             total_servicio_exento,
                                                                             5),
                                                                             total_servicio_exonerado,
                                                                         round(
                                                                             total_mercaderia_gravado,
                                                                             5),
                                                                         round(
                                                                             total_mercaderia_exento,
                                                                             5),
                                                                         total_mercaderia_exonerado,
                                                                         total_otros_cargos,
                                                                         base_subtotal,
                                                                         total_impuestos,
                                                                         total_descuento,
                                                                         json.dumps(
                                                                             lines,
                                                                             ensure_ascii=False),
                                                                         tipo_documento_referencia,
                                                                         numero_documento_referencia,
                                                                         fecha_emision_referencia,
                                                                         codigo_referencia,
                                                                         razon_referencia,
                                                                         currency_rate,
                                                                         invoice_comments)

                inv.fname_xml_comprobante = inv.tipo_documento + '_' + inv.number_electronic + '.xml'

                xml_to_sign = str(xml_string_builder)
                xml_firmado = api_facturae.sign_xml(
                    inv.company_id.signature, inv.company_id.frm_pin,
                    xml_to_sign)

                inv.xml_comprobante = base64.encodestring(xml_firmado)
                _logger.info('E-INV CR - SIGNED XML:%s',
                             inv.fname_xml_comprobante)
            else:
                xml_firmado = inv.xml_comprobante.decode("UTF-8")

            # Get token from Hacienda
            token_m_h = api_facturae.get_token_hacienda(
                inv, inv.company_id.frm_ws_ambiente)

            response_json = api_facturae.send_xml_fe(inv, token_m_h,
                                                     inv.date_issuance,
                                                     xml_firmado,
                                                     inv.company_id.frm_ws_ambiente)

            response_status = response_json.get('status')
            response_text = response_json.get('text')

            if 200 <= response_status <= 299:
                if inv.tipo_documento == 'FEC':
                    inv.state_send_invoice = 'procesando' 
                else:
                    inv.state_tributacion = 'procesando'
                inv.electronic_invoice_return_message = response_text
            else:
                if response_text.find('ya fue recibido anteriormente') != -1:
                    if inv.tipo_documento == 'FEC':
                        inv.state_send_invoice = 'procesando' 
                    else:
                        inv.state_tributacion = 'procesando'
                    inv.message_post(
                        subject='Error',
                        body='Ya recibido anteriormente, se pasa a consultar')
                elif inv.error_count > 10:
                    inv.message_post(subject='Error', body=response_text)
                    inv.electronic_invoice_return_message = response_text
                    inv.state_tributacion = 'error'
                else:
                    inv.error_count += 1
                    if inv.tipo_documento == 'FEC':
                        inv.state_send_invoice = 'procesando' 
                    else:
                        inv.state_tributacion = 'procesando'
                    inv.message_post(subject='Error', body=response_text)

    @api.multi
    def action_invoice_open(self):
        super(AccountInvoiceElectronic, self).action_invoice_open()

        # Revisamos si el ambiente para Hacienda está habilitado
        if self.company_id.frm_ws_ambiente != 'disabled':

            for inv in self:
                currency = inv.currency_id

                # Digital Invoice or ticket
                if inv.type == 'out_invoice':

                    # Verificar si es nota DEBITO
                    # if inv.invoice_id and inv.journal_id and (
                    #         inv.journal_id.code == 'NDV'):
                    #     tipo_documento = 'ND'
                    #     sequence = inv.journal_id.ND_sequence_id.next_by_id()
                    #
                    # else:
                    
                    if inv.tipo_documento in ('FE', 'TE'):
                        if inv.company_id.version_hacienda == '4.2':
                            inv.tipo_documento = 'FE'
                            sequence = inv.journal_id.FE_sequence_id.next_by_id()
                        elif inv.partner_id.vat:
                            inv.tipo_documento = 'FE'
                            sequence = inv.journal_id.FE_sequence_id.next_by_id()
                        else:
                            inv.tipo_documento = 'TE'
                            sequence = inv.journal_id.TE_sequence_id.next_by_id()
                            
                    elif inv.tipo_documento == 'FEE':
                        sequence = inv.journal_id.FEE_sequence_id.next_by_id()

                # Credit Note
                elif inv.type == 'out_refund':
                    inv.tipo_documento = 'NC'
                    sequence = inv.journal_id.NC_sequence_id.next_by_id()

                # Digital Supplier Invoice
                elif inv.type == 'in_invoice' and inv.partner_id.country_id and \
                    inv.partner_id.country_id.code == 'CR' and inv.partner_id.identification_id and \
                    inv.partner_id.vat and inv.xml_supplier_approval == False:
                    inv.tipo_documento = 'FEC'
                    sequence = inv.company_id.FEC_sequence_id.next_by_id()
                else:
                    continue

                # tipo de identificación
                if not self.company_id.identification_id:
                    raise UserError(
                        'Seleccione el tipo de identificación del emisor en el perfil de la compañía')

                if inv.partner_id and inv.partner_id.vat:
                    identificacion = re.sub(
                        '[^0-9]', '', inv.partner_id.vat)
                    id_code = inv.partner_id.identification_id and inv.partner_id.identification_id.code
                    if not id_code:
                        if len(identificacion) == 9:
                            id_code = '01'
                        elif len(identificacion) == 10:
                            id_code = '02'
                        elif len(identificacion) in (11, 12):
                            id_code = '03'
                        else:
                            id_code = '05'

                    if id_code == '01' and len(identificacion) != 9:
                        raise UserError(
                            'La Cédula Física del emisor debe de tener 9 dígitos')
                    elif id_code == '02' and len(identificacion) != 10:
                        raise UserError(
                            'La Cédula Jurídica del emisor debe de tener 10 dígitos')
                    elif id_code == '03' and len(
                            identificacion) not in (11, 12):
                        raise UserError(
                            'La identificación DIMEX del emisor debe de tener 11 o 12 dígitos')
                    elif id_code == '04' and len(identificacion) != 10:
                        raise UserError(
                            'La identificación NITE del emisor debe de tener 10 dígitos')

                    if inv.payment_term_id and not inv.payment_term_id.sale_conditions_id:
                        raise UserError(
                            'No se pudo Crear la factura electrónica: \n Debe configurar condiciones de pago para' +
                            inv.payment_term_id.name)

                    # Validate if invoice currency is the same as the company currency
                    if currency.name != self.company_id.currency_id.name and (
                            not currency.rate_ids or not (
                            len(currency.rate_ids) > 0)):
                        raise UserError(
                            'No hay tipo de cambio registrado para la moneda ' + currency.name)

                # Generamos los datos utilizando el API de CRLIBRE
                response_json = api_facturae.get_clave_hacienda(self,
                                                                inv.tipo_documento,
                                                                sequence,
                                                                inv.journal_id.sucursal,
                                                                inv.journal_id.terminal)

                inv.number_electronic = response_json.get('clave')
                inv.sequence = response_json.get('consecutivo')
                inv.state_send_invoice = False
