# -*- coding: utf-8 -*-
import requests
import logging
import re
import datetime
import pytz
import base64
import json
import xml.etree.ElementTree as ET
from lxml import etree
from xml.sax.saxutils import escape
from dateutil.parser import parse
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import functions

_logger = logging.getLogger(__name__)


class IdentificationType(models.Model):
    _name = "identification.type"

    code = fields.Char(string="Código", required=False,)
    name = fields.Char(string="Nombre", required=False,)
    notes = fields.Text(string="Notas", required=False,)

class CompanyElectronic(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'mail.thread', 'ir.needaction_mixin']

    commercial_name = fields.Char(string="Nombre comercial", required=False,)
    phone_code = fields.Char(string="Código de teléfono", required=False, size=3, default="506",help="Sin espacios ni guiones")
    signature = fields.Binary(string="Llave Criptográfica",)
    identification_id = fields.Many2one(comodel_name="identification.type", string="Tipo de identificacion", required=False,)
    district_id = fields.Many2one(comodel_name="res.country.district", string="Distrito", required=False,)
    county_id = fields.Many2one(comodel_name="res.country.county", string="Cantón", required=False,)
    neighborhood_id = fields.Many2one(comodel_name="res.country.neighborhood", string="Barrios", required=False,)
    frm_ws_identificador = fields.Char(string="Usuario de Factura Electrónica", required=False,)
    frm_ws_password = fields.Char(string="Password de Factura Electrónica", required=False,)
    frm_ws_ambiente = fields.Selection(
        selection=[('disabled', 'Deshabilitado'), ('api-stag', 'Pruebas'), ('api-prod', 'Producción'), ], string="Ambiente",
        required=True, default='disabled',
        help='Es el ambiente en al cual se le está actualizando el certificado. Para el ambiente de calidad (stag) c3RhZw==, '
             'para el ambiente de producción (prod) '
             'cHJvZA==. Requerido.')
    frm_pin = fields.Char(string="Pin", required=False, help='Es el pin correspondiente al certificado. Requerido')
    frm_callback_url = fields.Char(string="Callback Url", required=False, default="https://url_callback/repuesta.php?",
                                   help='Es la URL en a la cual se reenviarán las respuestas de Hacienda.')
    #Template de correo electronico para las FE por compañia
    template_email_fe = fields.Many2one("email.template",string="Plantilla de correo electronico FE", required=False)

    frm_apicr_username = fields.Char(string="Usuario de Api", required=False,)
    frm_apicr_password = fields.Char(string="Password de Api", required=False,)
    frm_apicr_signaturecode = fields.Char(string="Codigo para Firmar API", required=False,)



class PartnerElectronic(models.Model):
    _inherit = "res.partner"

    commercial_name = fields.Char(string="Nombre comercial", required=False,)
    phone_code = fields.Char(string="Código de teléfono", required=False, default="506")
    state_id = fields.Many2one(comodel_name="res.country.state", string="Provincia", required=False,)
    district_id = fields.Many2one(comodel_name="res.country.district", string="Distrito", required=False,)
    county_id = fields.Many2one(comodel_name="res.country.county", string="Cantón", required=False,)
    neighborhood_id = fields.Many2one(comodel_name="res.country.neighborhood", string="Barrios", required=False,)
    identification_id = fields.Many2one(comodel_name="identification.type", string="Tipo de identificacion",
                                        required=False,)
    payment_methods_id = fields.Many2one(comodel_name="payment.methods", string="Métodos de Pago", required=False,)

    #_sql_constraints = [
    #    ('vat_uniq', 'unique (vat)', "La cédula debe ser única"),
    #]
    @api.onchange('phone')
    def _onchange_phone(self):
        if self.phone:
            self.phone = re.sub(r"[^0-9]+", "", self.phone)
            if not self.phone.isdigit():
                alert = {
                    'title': 'Atención',
                    'message': 'Favor no introducir letras, espacios ni guiones en los números telefónicos.'
                }
                return {'value': {'phone': ''}, 'warning': alert}

    @api.onchange('mobile')
    def _onchange_mobile(self):
        if self.mobile:
            self.mobile = re.sub(r"[^0-9]+", "", self.mobile)
            if not self.mobile.isdigit():
                alert = {
                    'title': 'Atención',
                    'message': 'Favor no introducir letras, espacios ni guiones en los números telefónicos.'
                }
                return {'value': {'mobile': ''}, 'warning': alert}

    @api.onchange('email')
    def _onchange_email(self):
        if self.email:
            if not re.match(r'^(\s?[^\s,]+@[^\s,]+\.[^\s,]+\s?,)*(\s?[^\s,]+@[^\s,]+\.[^\s,]+)$', self.email.lower()):
                vals = {'email': False}
                alerta = {
                    'title': 'Atención',
                    'message': 'El correo electrónico no cumple con una estructura válida. ' + str(self.email)
                }
                return {'value': vals, 'warning': alerta}

    @api.onchange('vat')
    def _onchange_vat(self):
        if self.identification_id and self.vat:
            if self.identification_id.code == '05':
                if len(self.vat) == 0 or len(self.vat) > 20:
                    raise UserError('La identificación debe tener menos de 20 carateres.')
            else:
                # Remove leters, dashes, dots or any other special character.
                self.vat = re.sub(r"[^0-9]+", "", self.vat)
                if self.identification_id.code == '01' and len(self.vat) != 9:
                    raise UserError(
                        'La identificación tipo Cédula física debe de contener 9 dígitos, sin cero al inicio y sin guiones.')
                elif self.identification_id.code == '02' and len(self.vat) != 10:
                    raise UserError(
                        'La identificación tipo Cédula jurídica debe contener 10 dígitos, sin cero al inicio y sin guiones.')
                elif self.identification_id.code == '03' and len(self.vat) < 11 or len(self.vat) > 12:
                    raise UserError(
                        'La identificación tipo DIMEX debe contener 11 o 12 dígitos, sin ceros al inicio y sin guiones.')
                elif self.identification_id.code == '04' and len(self.vat) != 9:
                    raise UserError(
                        'La identificación tipo NITE debe contener 10 dígitos, sin ceros al inicio y sin guiones.')

class CodeTypeProduct(models.Model):
    _name = "code.type.product"

    code = fields.Char(string="Código", required=False,)
    name = fields.Char(string="Nombre", required=False,)


class ProductElectronic(models.Model):
    _inherit = "product.template"

    @api.model
    def _default_code_type_id(self):
        code_type_id = self.env['code.type.product'].search([('code', '=', '04')], limit=1)
        return code_type_id or False

    commercial_measurement = fields.Char(string="Unidad de Medida Comercial", required=False,)
    code_type_id = fields.Many2one(comodel_name="code.type.product", string="Tipo de código", required=False,
                                   default=_default_code_type_id)


class InvoiceTaxElectronic(models.Model):
    _inherit = "account.tax"

    tax_code = fields.Char(string="Código de impuesto", required=False,)


class Exoneration(models.Model):
    _name = "exoneration"

    name = fields.Char(string="Nombre", required=False,)
    code = fields.Char(string="Código", required=False,)
    type = fields.Char(string="Tipo", required=False,)
    exoneration_number = fields.Char(string="Número de exoneración", required=False,)
    name_institution = fields.Char(string="Nombre de institución", required=False,)
    date = fields.Date(string="Fecha", required=False,)
    percentage_exoneration = fields.Float(string="Porcentaje de exoneración", required=False,)

class PaymentMethods(models.Model):
    _name = "payment.methods"

    active = fields.Boolean(string="Activo", required=False, default=True)
    sequence = fields.Char(string="Secuencia", required=False,)
    name = fields.Char(string="Nombre", required=False,)
    notes = fields.Text(string="Notas", required=False,)


class SaleConditions(models.Model):
    _name = "sale.conditions"

    active = fields.Boolean(string="Activo", required=False, default=True)
    sequence = fields.Char(string="Secuencia", required=False,)
    name = fields.Char(string="Nombre", required=False,)
    notes = fields.Text(string="Notas", required=False,)

class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"
    sale_conditions_id = fields.Many2one(comodel_name="sale.conditions", string="Condiciones de venta")


class ReferenceDocument(models.Model):
    _name = "reference.document"

    active = fields.Boolean(string="Activo", required=False, default=True)
    code = fields.Char(string="Código", required=False,)
    name = fields.Char(string="Nombre", required=False,)


class ReferenceCode(models.Model):
    _name = "reference.code"

    active = fields.Boolean(string="Activo", required=False, default=True)
    code = fields.Char(string="Código", required=False,)
    name = fields.Char(string="Nombre", required=False,)


class Resolution(models.Model):
    _name = "resolution"

    active = fields.Boolean(string="Activo", required=False, default=True)
    name = fields.Char(string="Nombre", required=False,)
    date_resolution = fields.Date(string="Fecha de resolución", required=False,)


class ProductUom(models.Model):
    _inherit = "product.uom"
    code = fields.Char(string="Código", required=False,)


class AccountJournal(models.Model):
    _inherit = "account.journal"
    nd = fields.Boolean(string="Nota de Débito", required=False,)


class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    @api.model
    def _get_invoice_id(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            return active_id
        return ''

    reference_code_id = fields.Many2one(comodel_name="reference.code", string="Código de referencia", required=True,)
    invoice_id = fields.Many2one(comodel_name="account.invoice", string="Documento de referencia",
                                 default=_get_invoice_id, required=False,)

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
                        raise UserError(_('Cannot refund draft/proforma/cancelled invoice.'))
                    if inv.reconciled and mode in ('cancel', 'modify'):
                        raise UserError(_(
                            'Cannot refund invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.'))

                    date = form.date or False
                    description = form.description or inv.name
                    refund = inv.refund(form.date_invoice, date, description, inv.journal_id.id, form.invoice_id.id,
                                        form.reference_code_id.id)

                    created_inv.append(refund.id)
                    if mode in ('cancel', 'modify'):
                        movelines = inv.move_id.line_ids
                        to_reconcile_ids = {}
                        to_reconcile_lines = self.env['account.move.line']
                        for line in movelines:
                            if line.account_id.id == inv.account_id.id:
                                to_reconcile_lines += line
                                to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                            if line.reconciled:
                                line.remove_move_reconcile()
                        refund.action_invoice_open()
                        for tmpline in refund.move_id.line_ids:
                            if tmpline.account_id.id == inv.account_id.id:
                                to_reconcile_lines += tmpline
                        to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                        if mode == 'modify':
                            invoice = inv.read(inv_obj._get_refund_modify_read_fields())
                            invoice = invoice[0]
                            del invoice['id']
                            invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
                            invoice_lines = inv_obj.with_context(mode='modify')._refund_cleanup_lines(invoice_lines)
                            tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
                            tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
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
                                'reference_code_id': form.reference_code_id.id,  # agregado
                            })
                            for field in inv_obj._get_refund_common_fields():
                                if inv_obj._fields[field].type == 'many2one':
                                    invoice[field] = invoice[field] and invoice[field][0]
                                else:
                                    invoice[field] = invoice[field] or False
                            inv_refund = inv_obj.create(invoice)
                            if inv_refund.payment_term_id.id:
                                inv_refund._onchange_payment_term_date_invoice()
                            created_inv.append(inv_refund.id)
                    xml_id = (inv.type in ['out_refund', 'out_invoice']) and 'action_invoice_tree1' or \
                             (inv.type in ['in_refund', 'in_invoice']) and 'action_invoice_tree2'
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

    exoneration_id = fields.Many2one(comodel_name="exoneration", string="Exoneración", required=False,)


class AccountInvoiceElectronic(models.Model):
    _inherit = "account.invoice"

    number_electronic = fields.Char(string="Número electrónico", required=False, copy=False, index=True)
    date_issuance = fields.Char(string="Fecha de emisión", required=False, copy=False)
    consecutive_number_receiver = fields.Char(string="Número Consecutivo Receptor", required=False, copy=False, readonly=True, index=True)
    currency_rate_save = fields.Float(required=False, string="Valor del dolar")
    state_send_invoice = fields.Selection([('aceptado', 'Aceptado'),
                                           ('rechazado', 'Rechazado'),
                                           ('error', 'Error'),
                                           ('ne', 'No Encontrado'),
                                           ('procesando', 'Procesando')],
                                          'Estado FE Proveedor')
    state_tributacion = fields.Selection(
        [('aceptado', 'Aceptado'), ('rechazado', 'Rechazado'), ('recibido', 'Recibido'),
         ('error', 'Error'), ('procesando', 'Procesando'), ('na', 'No Aplica'), ('ne', 'No Encontrado')], 'Estado FE',
        copy=False)
    state_invoice_partner = fields.Selection([('1', 'Aceptado'), ('3', 'Rechazado'), ('2', 'Aceptacion parcial')],
                                             'Respuesta del Cliente')
    reference_code_id = fields.Many2one(comodel_name="reference.code", string="Código de referencia", required=False,)
    payment_methods_id = fields.Many2one(comodel_name="payment.methods", string="Métodos de Pago", required=False,)
    invoice_id = fields.Many2one(comodel_name="account.invoice", string="Documento de referencia", required=False,
                                 copy=False)
    xml_respuesta_tributacion = fields.Binary(string="Respuesta Tributación XML", required=False, copy=False,
                                              attachment=True)
    fname_xml_respuesta_tributacion = fields.Char(string="Nombre de archivo XML Respuesta Tributación", required=False,
                                                  copy=False)
    xml_comprobante = fields.Binary(string="Comprobante XML", required=False, copy=False, attachment=True)
    fname_xml_comprobante = fields.Char(string="Nombre de archivo Comprobante XML", required=False, copy=False,
                                        attachment=True)
    xml_supplier_approval = fields.Binary(string="XML Proveedor", required=False, copy=False, attachment=True)
    fname_xml_supplier_approval = fields.Char(string="Nombre de archivo Comprobante XML proveedor", required=False,
                                              copy=False, attachment=True)
    amount_tax_electronic_invoice = fields.Monetary(string='Total de impuestos FE', readonly=True,)
    amount_total_electronic_invoice = fields.Monetary(string='Total FE', readonly=True,)
    state_email = fields.Selection([('no_email', 'Sin cuenta de correo'), ('sent', 'Enviado'), ('fe_error', 'Error FE')], 'Estado email', copy=False)

    _sql_constraints = [
        ('number_electronic_uniq', 'unique (number_electronic)', "La clave de comprobante debe ser única"),
    ]

    @api.onchange('xml_supplier_approval')
    def _onchange_xml_supplier_approval(self):
        if self.xml_supplier_approval:
            root = ET.fromstring(re.sub(' xmlns="[^"]+"', '', base64.b64decode(self.xml_supplier_approval).decode("utf-8"), count=1))  # quita el namespace de los elementos

            if not root.findall('Clave'):
                return {'value': {'xml_supplier_approval': False}, 'warning': {'title': 'Atención',
                                                                               'message': 'El archivo xml no contiene el nodo Clave. Por favor cargue un archivo con el formato correcto.'}}
            if not root.findall('FechaEmision'):
                return {'value': {'xml_supplier_approval': False}, 'warning': {'title': 'Atención',
                                                                               'message': 'El archivo xml no contiene el nodo FechaEmision. Por favor cargue un archivo con el formato correcto.'}}
            if not root.findall('Emisor'):
                return {'value': {'xml_supplier_approval': False}, 'warning': {'title': 'Atención',
                                                                               'message': 'El archivo xml no contiene el nodo Emisor. Por favor cargue un archivo con el formato correcto.'}}
            if not root.findall('Emisor')[0].findall('Identificacion'):
                return {'value': {'xml_supplier_approval': False}, 'warning': {'title': 'Atención',
                                                                               'message': 'El archivo xml no contiene el nodo Identificacion. Por favor cargue un archivo con el formato correcto.'}}
            if not root.findall('Emisor')[0].findall('Identificacion')[0].findall('Tipo'):
                return {'value': {'xml_supplier_approval': False}, 'warning': {'title': 'Atención',
                                                                               'message': 'El archivo xml no contiene el nodo Tipo. Por favor cargue un archivo con el formato correcto.'}}
            if not root.findall('Emisor')[0].findall('Identificacion')[0].findall('Numero'):
                return {'value': {'xml_supplier_approval': False}, 'warning': {'title': 'Atención',
                                                                               'message': 'El archivo xml no contiene el nodo Numero. Por favor cargue un archivo con el formato correcto.'}}
            # if not (root.findall('ResumenFactura') and root.findall('ResumenFactura')[0].findall('TotalImpuesto')):
            #     return {'value': {'xml_supplier_approval': False}, 'warning': {'title': 'Atención',
            #                                                                    'message': 'No se puede localizar el nodo TotalImpuesto. Por favor cargue un archivo con el formato correcto.'}}
            if not (root.findall('ResumenFactura') and root.findall('ResumenFactura')[0].findall('TotalComprobante')):
                return {'value': {'xml_supplier_approval': False}, 'warning': {'title': 'Atención',
                                                                               'message': 'No se puede localizar el nodo TotalComprobante. Por favor cargue un archivo con el formato correcto.'}}
        # self.fname_xml_supplier_approval = 'comrpobante_proveedor.xml'

    @api.multi
    def charge_xml_data(self):
        if self.xml_supplier_approval:

            xml_decoded = base64.b64decode(self.xml_supplier_approval)
            try:
                factura = etree.fromstring(xml_decoded)
            except Exception, e:
                # raise UserError(_(
                #    "This XML file is not XML-compliant. Error: %s") % e)
                _logger.info('MAB - This XML file is not XML-compliant.  Exception %s' % e)
                return {'status': 400, 'text': 'Excepción de conversión de XML'}
            pretty_xml_string = etree.tostring(
                factura, pretty_print=True, encoding='UTF-8',
                xml_declaration=True)

            _logger.error('MAB - send_file XML: %s' % pretty_xml_string)

            namespaces = factura.nsmap
            inv_xmlns = namespaces.pop(None)
            namespaces['inv'] = inv_xmlns

            # factura = etree.tostring(etree.fromstring(xml_decoded)).decode()
            # factura = etree.fromstring(re.sub(' xmlns="[^"]+"', '', factura, count=1))

            self.number_electronic = factura.xpath("inv:Clave", namespaces=namespaces)[0].text
            self.date_issuance = factura.xpath("inv:FechaEmision", namespaces=namespaces)[0].text
            emisor = factura.xpath("inv:Emisor/inv:Identificacion/inv:Numero", namespaces=namespaces)[0].text
            receptor = factura.xpath("inv:Receptor/inv:Identificacion/inv:Numero", namespaces=namespaces)[0].text

            if receptor != self.company_id.vat:
                raise UserError('El receptor no corresponde con la compañía actual con identificación ' + receptor + '. Por favor active la compañía correcta.')

            self.date_invoice = parse(self.date_issuance)

            partner = self.env['res.partner'].search(
                [('vat', '=', emisor)])
            if partner:
                self.partner_id = partner.id
            else:
                raise UserError('El proveedor con identificación ' + emisor + ' no existe. Por favor creelo primero en el sistema.')

            self.reference = self.number_electronic[21:41]
            tax_node = factura.xpath("inv:ResumenFactura/inv:TotalImpuesto", namespaces=namespaces)
            if tax_node:
                self.amount_tax_electronic_invoice = tax_node[0].text
            self.amount_total_electronic_invoice = factura.xpath("inv:ResumenFactura/inv:TotalComprobante", namespaces=namespaces)[0].text

    @api.multi
    def send_acceptance_message(self):
        for inv in self:
            if inv.state_send_invoice and inv.state_send_invoice != 'procesando':
                raise UserError('Aviso!.\n La factura de proveedor ya fue confirmada')
            elif abs(self.amount_total_electronic_invoice-self.amount_total) > 1:
                continue
                raise UserError('Aviso!.\n Monto total no concuerda con monto del XML')
            elif not inv.xml_supplier_approval:
                raise UserError('Aviso!.\n No se ha cargado archivo XML')
            elif not inv.journal_id.sucursal or not inv.journal_id.terminal:
                raise UserError('Aviso!.\nPor favor configure el diario de compras, terminal y sucursal')
            #elif not inv.journal_id.sequence_electronic_invoice_provider:
            #    raise UserError('Aviso!.\nPor favor configure la secuencia para la FE de proveedor')
            url = self.company_id.frm_callback_url
            #root = ET.fromstring(re.sub(' xmlns="[^"]+"', '', base64.b64decode(inv.xml_supplier_approval).decode("utf-8"), count=1))
            if not inv.state_invoice_partner:
                raise UserError('Aviso!.\nDebe primero seleccionar el tipo de respuesta para el archivo cargado.')

            if inv.company_id.frm_ws_ambiente != 'disabled' and inv.state_invoice_partner:
                if not inv.xml_comprobante:
                    if inv.state_invoice_partner == '1':
                        detalle_mensaje = 'Aceptado'
                        tipo = 1
                        tipo_documento = 'CCE'
                        sequence = inv.env['ir.sequence'].next_by_code('sequece.electronic.doc.confirmation')
                    elif inv.state_invoice_partner == '2':
                        detalle_mensaje = 'Aceptado parcial'
                        tipo = 2
                        tipo_documento = 'CPCE'
                        sequence = inv.env['ir.sequence'].next_by_code('sequece.electronic.doc.partial.confirmation')
                    else:
                        detalle_mensaje = 'Rechazado'
                        tipo = 3
                        tipo_documento = 'RCE'
                        sequence = inv.env['ir.sequence'].next_by_code('sequece.electronic.doc.reject')

                    now_utc = datetime.datetime.now(pytz.timezone('UTC'))
                    now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
                    date_cr = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")
                    payload = {}
                    headers = {}

                    # usamos un consecutivo único por tipo de confirmación/rechazo para TODA la empresa
                    #response_json = functions.get_clave(self, url, tipo_documento, sequence, inv.journal_id.sucursal, inv.journal_id.terminal)
                    response_json = functions.get_clave(self, tipo_documento, sequence, 1, 1)
                    inv.consecutive_number_receiver = response_json.get('consecutivo')

                    payload['w'] = 'genXML'
                    payload['r'] = 'gen_xml_mr'
                    payload['clave'] = inv.number_electronic
                    #payload['numero_cedula_emisor'] = root.findall('Emisor')[0].find('Identificacion')[1].text
                    #payload['fecha_emision_doc'] = root.findall('FechaEmision')[0].text
                    payload['numero_cedula_emisor'] = inv.partner_id.vat
                    payload['fecha_emision_doc'] = inv.date_issuance
                    payload['mensaje'] = tipo
                    payload['detalle_mensaje'] = detalle_mensaje
                    #tax_node = root.findall('ResumenFactura')[0].findall('TotalImpuesto')
                    #if tax_node:
                    #    payload['monto_total_impuesto'] = tax_node[0].text
                    if inv.amount_tax_electronic_invoice:
                        payload['monto_total_impuesto'] = inv.amount_tax_electronic_invoice
                    payload['total_factura'] = inv.amount_total_electronic_invoice
                    payload['numero_cedula_receptor'] = inv.company_id.vat
                    payload['numero_consecutivo_receptor'] = inv.consecutive_number_receiver

                    response = requests.request("POST", url, data=payload, headers=headers)
                    response_json = response.json()

                    xml = response_json.get('resp').get('xml')

                    response_json = functions.sign_xml(inv, tipo_documento, url, xml)
                    if response_json['status'] != 200:
                        _logger.error('MAB - API Error signing XML:%s', response_json['text'])
                        inv.state_send_invoice = 'error'
                        continue

                    xml_firmado = response_json.get('xmlFirmado')

                    inv.fname_xml_comprobante = tipo_documento + '_' + inv.number_electronic + '.xml'
                    inv.xml_comprobante = xml_firmado
                    #inv.date_issuance = date_cr
                    _logger.error('MAB - SIGNED XML:%s', inv.fname_xml_comprobante)

                    env = inv.company_id.frm_ws_ambiente
                    response_json = functions.token_hacienda(inv.company_id)
                    if response_json['status'] != 200:
                        _logger.error('MAB - Send Acceptance Message - HALTED - Failed to get token')
                        return

                    #                    response_json = functions.send_file(inv, token_m_h, date_cr, xml_firmado, env, url)
                    headers = {}
                    payload = {}
                    payload['w'] = 'send'
                    payload['r'] = 'sendMensaje'
                    payload['token'] = response_json['token']
                    payload['clave'] = inv.number_electronic
                    payload['fecha'] = date_cr
                    payload['emi_tipoIdentificacion'] = inv.partner_id.identification_id.code
                    payload['emi_numeroIdentificacion'] = inv.partner_id.vat
                    payload['recp_tipoIdentificacion'] = inv.company_id.identification_id.code
                    payload['recp_numeroIdentificacion'] = inv.company_id.vat
                    payload['comprobanteXml'] = xml_firmado
                    payload['client_id'] = env
                    payload['consecutivoReceptor'] = inv.consecutive_number_receiver

                    response = requests.request("POST", url, data=payload, headers=headers)
                    response_json = response.json()
                    status = response_json.get('resp').get('Status')
                    if  status == 202:
                        inv.state_send_invoice = 'procesando'
                        #functions.consulta_documentos(self, inv, env, token_m_h, url, date_cr, xml_firmado)
                    else:
                        inv.state_send_invoice = 'error'
                        _logger.error('MAB - Invoice: %s  Error sending Acceptance Message: %s', inv.number_electronic,
                                      response_json.get('resp').get('text'))

                if inv.state_send_invoice == 'procesando':
                    response_json = functions.token_hacienda(inv.company_id)
                    if response_json['status'] != 200:
                        _logger.error('MAB - Send Acceptance Message - HALTED - Failed to get token')
                        return

                    response_json = functions.consulta_clave(inv.number_electronic+'-'+inv.consecutive_number_receiver,
                                                             response_json['token'],
                                                             inv.company_id.frm_ws_ambiente)
                    status = response_json['status']
                    if status == 200:
                        inv.state_send_invoice = response_json.get('ind-estado')
                        inv.xml_respuesta_tributacion = response_json.get('respuesta-xml')
                        inv.fname_xml_respuesta_tributacion = 'Aceptacion_' + inv.number_electronic+'-'+inv.consecutive_number_receiver + '.xml'
                        _logger.error('MAB - Estado Documento:%s', inv.state_send_invoice)
                    elif status == 400:
                        inv.state_send_invoice = 'ne'
                        _logger.error('MAB - Aceptacion Documento:%s no encontrado en Hacienda.',
                                      inv.number_electronic+'-'+inv.consecutive_number_receiver)
                    else:
                        _logger.error('MAB - Error inesperado en Send Acceptance File - Abortando')
                        return


    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None, invoice_id=None,
               reference_code_id=None):
        if self.env.user.company_id.frm_ws_ambiente == 'disabled':
            new_invoices = super(AccountInvoiceElectronic, self).refund()
            return new_invoices
        else:
            new_invoices = self.browse()
            for invoice in self:
                # create the new invoice
                values = self._prepare_refund(invoice, date_invoice=date_invoice, date=date, description=description, journal_id=journal_id)
                values.update({'invoice_id': invoice_id, 'reference_code_id': reference_code_id})
                refund_invoice = self.create(values)
                invoice_type = {
                    'out_invoice': ('customer invoices refund'),
                    'in_invoice': ('vendor bill refund'),
                    'out_refund': ('customer refund refund'),
                    'in_refund': ('vendor refund refund')
                }
                message = _("This %s has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>") % (
                              invoice_type[invoice.type], invoice.id, invoice.number)
                refund_invoice.message_post(body=message)
                refund_invoice.payment_methods_id = invoice.payment_methods_id
                new_invoices += refund_invoice
            return new_invoices

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        super(AccountInvoiceElectronic, self)._onchange_partner_id()
        self.payment_methods_id = self.partner_id.payment_methods_id

    @api.model
    def _consultahacienda(self, max_invoices=10):  # cron
        invoices = self.env['account.invoice'].search([('type', 'in', ('out_invoice', 'out_refund')),
                                                       ('state', 'in', ('open', 'paid')),
                                                       ('state_tributacion', 'in', ('recibido', 'procesando'))],
                                                      limit=max_invoices)
        total_invoices=len(invoices)
        current_invoice=0
        _logger.error('MAB - Consulta Hacienda - Invoices to check: %s', total_invoices)
        for i in invoices:
            current_invoice+=1
            _logger.error('MAB - Consulta Hacienda - Invoice %s / %s  -  number:%s', current_invoice, total_invoices, i.number_electronic)

            response_json = functions.token_hacienda(i.company_id)
            if response_json['status'] != 200:
                _logger.error('MAB - Consulta Hacienda - HALTED - Failed to get token')
                return
            if i.number_electronic and len(i.number_electronic) == 50:
                response_json = functions.consulta_clave(i.number_electronic, response_json['token'], i.company_id.frm_ws_ambiente)
                status = response_json['status']
                if status == 200:
                    estado_m_h = response_json.get('ind-estado')
                    _logger.error('MAB - Estado Documento:%s', estado_m_h)
                elif status == 400:
                    estado_m_h = response_json.get('ind-estado')
                    i.state_tributacion = 'ne'
                    _logger.error('MAB - Documento:%s no encontrado en Hacienda.  Estado: %s', i.number_electronic, estado_m_h)
                    continue
                else:
                    _logger.error('MAB - Error inesperado en Consulta Hacienda - Abortando')
                    return

                i.state_tributacion = estado_m_h
                if estado_m_h == 'aceptado':
                    i.fname_xml_respuesta_tributacion = 'AHC_' + i.number_electronic + '.xml'
                    i.xml_respuesta_tributacion = response_json.get('respuesta-xml')
                    if i.partner_id and i.partner_id.email and not i.partner_id.opt_out:
                        email_template = self.env.ref('account.email_template_edi_invoice', False)
                        attachment = self.env['ir.attachment'].search(
                            [('res_model', '=', 'account.invoice'), ('res_id', '=', i.id),
                             ('res_field', '=', 'xml_comprobante')], limit=1)
                        attachment.name = i.fname_xml_comprobante
                        attachment.datas_fname = i.fname_xml_comprobante

                        attachment_resp = self.env['ir.attachment'].search(
                            [('res_model', '=', 'account.invoice'), ('res_id', '=', i.id),
                             ('res_field', '=', 'xml_respuesta_tributacion')], limit=1)
                        attachment_resp.name = i.fname_xml_respuesta_tributacion
                        attachment_resp.datas_fname = i.fname_xml_respuesta_tributacion

                        email_template.attachment_ids = [(6, 0, [attachment.id, attachment_resp.id])]
                        email_template.with_context(type='binary', default_type='binary').send_mail(i.id,
                                                                                                    raise_exception=False,
                                                                                                    force_send=True)  # default_type='binary'

                        email_template.attachment_ids = [(5)]

                elif estado_m_h == 'rechazado':
                    i.state_email = 'fe_error'
                    i.fname_xml_respuesta_tributacion = 'AHC_' + i.number_electronic + '.xml'
                    i.xml_respuesta_tributacion = response_json.get('respuesta-xml')

    @api.multi
    def action_consultar_hacienda(self):
        if self.company_id.frm_ws_ambiente != 'disabled':

            for inv in self:
                token_m_h = functions.token_hacienda(inv.company_id)
                #reemplazar por consulta_clave
                #functions.consulta_documentos(self, inv, self.company_id.frm_ws_ambiente, token_m_h, inv.company_id.frm_callback_url, False, False)

    @api.model
    def _confirmahacienda(self, max_invoices=10):  # cron
        invoices = self.env['account.invoice'].search([('type', 'in', ('in_invoice', 'in_refund')),
                                                       ('state', 'in', ('open', 'paid')),
                                                       ('xml_supplier_approval', '!=', False),
                                                       ('state_invoice_partner', '!=', False),
                                                       ('state_send_invoice', 'not in', ('aceptado', 'rechazado', 'error'))],
                                                      limit=max_invoices)
        total_invoices=len(invoices)
        current_invoice=0
        _logger.error('MAB - Confirma Hacienda - Invoices to check: %s', total_invoices)
        for i in invoices:
            current_invoice+=1
            _logger.error('MAB - Confirma Hacienda - Invoice %s / %s  -  number:%s', current_invoice, total_invoices, i.number_electronic)

            if abs(i.amount_total_electronic_invoice - i.amount_total) > 1:
                continue   # xml de proveedor no se ha procesado, debemos llamar la carga

            i.send_acceptance_message()

            if i.state_send_invoice == 'aceptado':
                if i.partner_id and i.partner_id.email and not i.partner_id.opt_out:
                    email_template = self.env.ref('cr_electronic_invoice.email_template_invoice_vendor', False)
                    attachment = self.env['ir.attachment'].search(
                        [('res_model', '=', 'account.invoice'), ('res_id', '=', i.id),
                         ('res_field', '=', 'xml_comprobante')], limit=1)
                    attachment.name = i.fname_xml_comprobante
                    attachment.datas_fname = i.fname_xml_comprobante

                    attachment_resp = self.env['ir.attachment'].search(
                        [('res_model', '=', 'account.invoice'), ('res_id', '=', i.id),
                         ('res_field', '=', 'xml_respuesta_tributacion')], limit=1)
                    attachment_resp.name = i.fname_xml_respuesta_tributacion
                    attachment_resp.datas_fname = i.fname_xml_respuesta_tributacion

                    email_template.attachment_ids = [(6, 0, [attachment.id, attachment_resp.id])]
                    email_template.with_context(type='binary', default_type='binary').send_mail(i.id,
                                                                                                raise_exception=False,
                                                                                                force_send=True)  # default_type='binary'
                    email_template.attachment_ids = [(5)]

    @api.model
    def _validahacienda(self, max_invoices=10):  # cron
        invoices = self.env['account.invoice'].search([('type', 'in', ('out_invoice','out_refund')),
                                                       ('state', 'in', ('open', 'paid')),
                                                       #('number', '=', '0000000004'),
                                                       ('number_electronic', '!=', False),
                                                       ('date_invoice', '>=', '2018-10-01'),
                                                       ('state_tributacion','=',False)],
                                                       order='number',
                                                       limit=max_invoices)
        total_invoices = len(invoices)
        current_invoice = 0
        _logger.error('MAB - Valida Hacienda - Invoices to check: %s', total_invoices)
        for inv in invoices:
            current_invoice += 1
            _logger.error('MAB - Valida Hacienda - Invoice %s / %s  -  number:%s', current_invoice, total_invoices, inv.number_electronic)
            if not inv.number.isdigit(): # or (len(inv.number) == 10):
                _logger.error('MAB - Valida Hacienda - skipped Invoice %s', inv.number)
                inv.state_tributacion = 'na'
                continue

            if not inv.xml_comprobante:
                url = inv.company_id.frm_callback_url
                now_utc = datetime.datetime.now(pytz.timezone('UTC'))
                now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
                date_cr = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")

                tipo_documento = ''
                numero_documento_referencia = ''
                fecha_emision_referencia = ''
                codigo_referencia = ''
                razon_referencia = ''
                medio_pago = inv.payment_methods_id.sequence or '01'
                currency = inv.currency_id
                # Es Factura de cliente o nota de débito
                if inv.type == 'out_invoice':
                    if inv.invoice_id and inv.journal_id and inv.journal_id.nd:
                        tipo_documento = 'ND'
                        numero_documento_referencia = inv.invoice_id.number_electronic
                        tipo_documento_referencia = inv.invoice_id.number_electronic[29:31]
                        fecha_emision_referencia = inv.invoice_id.date_issuance
                        codigo_referencia = inv.reference_code_id.code
                        razon_referencia = inv.reference_code_id.name
                    else:
                        tipo_documento = 'FE'
                        tipo_documento_referencia = ''

                # Si es Nota de Crédito
                elif inv.type == 'out_refund':
                    tipo_documento = 'NC'
                    codigo_referencia = inv.reference_code_id.code
                    razon_referencia = inv.reference_code_id.name

                    if inv.invoice_id.number_electronic:
                        numero_documento_referencia = inv.invoice_id.number_electronic
                        tipo_documento_referencia = inv.invoice_id.number_electronic[29:31]
                        fecha_emision_referencia = inv.invoice_id.date_issuance
                    else:
                        numero_documento_referencia = inv.invoice_id and re.sub('[^0-9]+', '', inv.invoice_id.number).rjust(50, '0') or '0000000'
                        tipo_documento_referencia = '99'
                        date_invoice = datetime.datetime.strptime(inv.invoice_id and inv.invoice_id.date_invoice or '2018-08-30', "%Y-%m-%d")
                        fecha_emision_referencia = date_invoice.strftime("%Y-%m-%d") + "T12:00:00-06:00"

                if inv.payment_term_id:
                    sale_conditions = inv.payment_term_id.sale_conditions_id.sequence or '01'
                else:
                    sale_conditions = '01'

                # Validate if invoice currency is the same as the company currency
                if currency.name == self.company_id.currency_id.name:
                    currency_rate = 1
                else:
                    #currency_rate = currency.rate_ids[0].original_rate
                    currency_rate = round(1.0 / currency.rate,5)

                # Generamos las líneas de la factura
                lines = dict()
                line_number = 0
                total_servicio_gravado = 0.0
                total_servicio_exento = 0.0
                total_mercaderia_gravado = 0.0
                total_mercaderia_exento = 0.0
                total_descuento = 0.0
                total_impuestos = 0.0
                base_subtotal = 0.0
                for inv_line in inv.invoice_line_ids:
                    line_number += 1
                    price = inv_line.price_unit * (1 - inv_line.discount / 100.0)
                    quantity = inv_line.quantity
                    if not quantity:
                        continue

                    line_taxes = inv_line.invoice_line_tax_ids.compute_all(price, currency, 1, product=inv_line.product_id, partner=inv_line.invoice_id.partner_id)
                    price_unit = round(line_taxes['total_excluded'] / (1 - inv_line.discount / 100.0), 5)  #ajustar para IVI

                    base_line = round(price_unit * quantity, 5)
                    subtotal_line = round(price_unit * quantity * (1 - inv_line.discount / 100.0), 5)

                    line = {
                        "cantidad": quantity,
                        "unidadMedida": inv_line.product_id and inv_line.product_id.uom_id.code or 'Sp',
                        "detalle": escape(inv_line.name[:159]),
                        "precioUnitario": price_unit,
                        "montoTotal": base_line,
                        "subtotal": subtotal_line,
                    }
                    if inv_line.discount:
                        descuento = round(base_line - subtotal_line,5)
                        total_descuento += descuento
                        line["montoDescuento"] = descuento
                        line["naturalezaDescuento"] = 'Descuento Comercial'

                    # Se generan los impuestos
                    taxes = dict()
                    impuesto_linea = 0.0
                    if inv_line.invoice_line_tax_ids:
                        tax_index = 0

                        taxes_lookup = {}
                        for i in inv_line.invoice_line_tax_ids:
                            taxes_lookup[i.id] = {'tax_code': i.tax_code, 'tarifa': i.amount}
                        for i in line_taxes['taxes']:
                            if taxes_lookup[i['id']]['tax_code'] <> '00':
                                tax_index += 1
                                tax_amount = round(i['amount'], 5)*quantity
                                impuesto_linea += tax_amount
                                tax = {
                                    'codigo': taxes_lookup[i['id']]['tax_code'],
                                    'tarifa': taxes_lookup[i['id']]['tarifa'],
                                    'monto': tax_amount,
                                }
                                # Se genera la exoneración si existe para este impuesto
                                if inv_line.exoneration_id:
                                    tax["exoneracion"] = {
                                        "tipoDocumento" : inv_line.exoneration_id.type,
                                        "numeroDocumento" : inv_line.exoneration_id.exoneration_number,
                                        "nombreInstitucion" : inv_line.exoneration_id.name_institution,
                                        "fechaEmision" : str(inv_line.exoneration_id.date) + 'T00:00:00-06:00',
                                        "montoImpuesto" : round(tax_amount * inv_line.exoneration_id.percentage_exoneration / 100, 2),
                                        "porcentajeCompra" : int(inv_line.exoneration_id.percentage_exoneration)
                                    }

                                taxes[tax_index] = tax

                    line["impuesto"] = taxes

                    # Si no hay product_id se asume como mercaderia
                    if inv_line.product_id and inv_line.product_id.type == 'service':
                        if taxes:
                            total_servicio_gravado += base_line
                            total_impuestos += impuesto_linea
                        else:
                            total_servicio_exento += base_line
                    else:
                        if taxes:
                            total_mercaderia_gravado += base_line
                            total_impuestos += impuesto_linea
                        else:
                            total_mercaderia_exento += base_line

                    base_subtotal += subtotal_line

                    line["montoTotalLinea"] = subtotal_line + impuesto_linea

                    lines[line_number] = line

                response_json = functions.make_xml_invoice(inv, tipo_documento, inv.number, date_cr,
                                                           sale_conditions, medio_pago, total_servicio_gravado,
                                                           total_servicio_exento, total_mercaderia_gravado,
                                                           total_mercaderia_exento, base_subtotal,
                                                           total_impuestos, total_descuento, json.dumps(lines, ensure_ascii=False),
                                                           tipo_documento_referencia, numero_documento_referencia,
                                                           fecha_emision_referencia,
                                                           codigo_referencia, razon_referencia, url, currency_rate)
                if response_json['status'] != 200:
                    _logger.error('MAB - API Error creating XML:%s', response_json['text'])
                    inv.state_tributacion = 'error'
                    continue

                xml = response_json.get('xml')
                response_json = functions.sign_xml(inv, tipo_documento, url, xml)
                if response_json['status'] != 200:
                    _logger.error('MAB - API Error signing XML:%s', response_json['text'])
                    inv.state_tributacion = 'error'
                    continue

                inv.date_issuance = date_cr
                inv.fname_xml_comprobante = tipo_documento + '_' + inv.number_electronic + '.xml'
                inv.xml_comprobante = response_json.get('xmlFirmado')
                _logger.error('MAB - SIGNED XML:%s', inv.fname_xml_comprobante)

            # get token
            response_json = functions.token_hacienda(inv.company_id)
            if response_json['status'] == 200:
                response_json = functions.send_file(inv, response_json['token'], inv.xml_comprobante, inv.company_id.frm_ws_ambiente)
                response_status = response_json.get('status')
                if 200 <=  response_status <= 299:
                    inv.state_tributacion = 'procesando'
                    #functions.consulta_documentos(self, inv, inv.company_id.frm_ws_ambiente, token_m_h, url, date_cr, xml_firmado)
                else:
                    inv.state_tributacion = 'error'
                    #inv.number_electronic = inv.number_electronic + ' - ' + response_json.get('text')
                    _logger.error('MAB - Invoice: %s  Status: %s Error sending XML: %s', inv.number_electronic, response_status, response_json['text'])
            else:
                _logger.error('MAB - Error obteniendo token_hacienda')
        _logger.error('MAB - Valida Hacienda - Finalizado Exitosamente')

    @api.multi
    def action_invoice_open(self):
        super(AccountInvoiceElectronic, self).action_invoice_open()
        # Revisamos si el ambiente para Hacienda está habilitado
        if self.company_id.frm_ws_ambiente != 'disabled':

            now_utc = datetime.datetime.now(pytz.timezone('UTC'))
            now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
            date_cr = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")

            for inv in self:
                if inv.journal_id.type == 'sale':
                    if inv.number.isdigit() and (len(inv.number) == 10):
                        tipo_documento = ''
                        next_number = inv.number
                        currency = inv.currency_id
                        # Es Factura de cliente o nota de débito
                        if inv.type == 'out_invoice':
                            if inv.invoice_id and inv.journal_id and inv.journal_id.nd:
                                tipo_documento = 'ND'
                            else:
                                tipo_documento = 'FE'

                        # Si es Nota de Crédito
                        elif inv.type == 'out_refund':
                            tipo_documento = 'NC'

                        # tipo de identificación
                        if not self.company_id.identification_id:
                            raise UserError(
                                'Seleccione el tipo de identificación del emisor en el perfil de la compañía')

                        # identificación
                        if inv.partner_id and inv.partner_id.vat:
                            identificacion = re.sub('[^0-9]', '', inv.partner_id.vat)
                            id_code = inv.partner_id.identification_id and inv.partner_id.identification_id.code
                            if not id_code:
                                if len(identificacion)==9:
                                    id_code = '01'
                                elif len(identificacion)==10:
                                    id_code = '02'
                                elif len(identificacion) in (11,12):
                                    id_code = '03'
                                else:
                                    id_code = '05'

                            if id_code == '01' and len(identificacion) != 9:
                                raise UserError('La Cédula Física del emisor debe de tener 9 dígitos')
                            elif id_code == '02' and len(identificacion) != 10:
                                raise UserError('La Cédula Jurídica del emisor debe de tener 10 dígitos')
                            elif id_code == '03' and len(identificacion) not in (11,12):
                                raise UserError('La identificación DIMEX del emisor debe de tener 11 o 12 dígitos')
                            elif id_code == '04' and len(identificacion) != 10:
                                raise UserError('La identificación NITE del emisor debe de tener 10 dígitos')

                        if inv.payment_term_id and not inv.payment_term_id.sale_conditions_id:
                            raise UserError('No se pudo Crear la factura electrónica: \n Debe configurar condiciones de pago para' +
                                    inv.payment_term_id.name)

                        # Validate if invoice currency is the same as the company currency
                        if currency.name != self.company_id.currency_id.name and (not currency.rate_ids or not (len(currency.rate_ids) > 0)):
                            raise UserError('No hay tipo de cambio registrado para la moneda ' + currency.name)

                        # Generando la clave como la especifica Hacienda
                        response_json = functions.get_clave(self, tipo_documento, next_number, inv.journal_id.sucursal,
                                                            inv.journal_id.terminal)
                        _logger.error('MAB - JSON Clave:%s', response_json)

                        inv.number_electronic = response_json.get('clave')
                        inv.number = response_json.get('consecutivo')
                    else:
                        raise UserError('Debe configurar correctamente la secuencia del documento')


