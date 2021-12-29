
import base64
import datetime
import json
import logging
import re
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import pytz
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.misc import get_lang

from odoo.http import request
from .qr_generator import generateQrCode
from odoo.tools import html2plaintext

from . import api_facturae
from .. import extensions

_logger = logging.getLogger(__name__)


class InvoiceLineElectronic(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _get_default_activity_id(self):
        for line in self:
            line.economic_activity_id = line.product_id and line.product_id.categ_id and line.product_id.categ_id.economic_activity_id and line.product_id.categ_id.economic_activity_id.id

    discount_note = fields.Char(string="Discount note", required=False)
    total_tax = fields.Float(string="Total tax", required=False)

    third_party_id = fields.Many2one("res.partner", string="Third - other charges")

    tariff_head = fields.Char(string="Tariff item for export invoice", required=False)

    categ_name = fields.Char(
        related='product_id.categ_id.name',
    )
    product_code = fields.Char(
        related='product_id.default_code',
    )
    economic_activity_id = fields.Many2one("economic.activity", string="Economic activity",
                                           required=False, store=True,
                                           context={'active_test': False},
                                           # default=_get_default_activity_id)
                                           default=False)
    non_tax_deductible = fields.Boolean(string='Indicates if this invoice is non-tax deductible',)

    @api.onchange('product_id')
    def product_changed(self):
        # Check if the product is non deductible to use a non_deductible tax
        if self.product_id.non_tax_deductible:
            taxes = []
            self.non_tax_deductible = True
            for tax in self.tax_ids:
                new_tax = self.env['account.tax'].search(
                                                [('tax_code', '=', tax.tax_code),
                                                ('amount', '=', tax.amount),
                                                ('type_tax_use', '=', 'purchase'),
                                                ('non_tax_deductible', '=', True),
                                                ('active', '=', True)],
                                                limit=1)
                if new_tax:
                    taxes.append((3, tax.id))
                    taxes.append((4, new_tax.id))
                else:
                    raise UserError(_('There is no "Non tax deductible" tax with the tax percentage of this product'))
            
            self.tax_ids = taxes
        else:
            self.non_tax_deductible = False

        # Check for the economic activity in the product or product category or company respectively (already set in the invoice when partner selected)
        if self.product_id and self.product_id.economic_activity_id:
            self.economic_activity_id = self.product_id.economic_activity_id
        elif self.product_id and self.product_id.categ_id and self.product_id.categ_id.economic_activity_id:
            self.economic_activity_id = self.product_id.categ_id.economic_activity_id
        else:
            self.economic_activity_id = self.move_id.economic_activity_id
    

class AccountInvoiceElectronic(models.Model):
    _inherit = "account.move"

    number_electronic = fields.Char(string="Electronic number", required=False, copy=False, index=True)
    date_issuance = fields.Char(string="Date of issue", required=False, copy=False)
    consecutive_number_receiver = fields.Char(string="Consecutive Receiver Number", required=False, copy=False, readonly=True, index=True)
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
        [('1', 'Aceptado'), 
            ('2', 'Aceptacion parcial'),
            ('3', 'Rechazado')], 
            'Respuesta del Cliente')

    reference_code_id = fields.Many2one("reference.code", string="Reference code", required=False, )

    reference_document_id = fields.Many2one("reference.document", string="Reference Document Type", required=False, )

    payment_methods_id = fields.Many2one("payment.methods", string="Payment methods", required=False, )

    invoice_id = fields.Many2one("account.move", string="Reference document", required=False, copy=False)

    xml_respuesta_tributacion = fields.Binary( string="XML Tributación Response", required=False, copy=False, attachment=True)

    electronic_invoice_return_message = fields.Char(
        string='Hacienda answer', readonly=True, )

    fname_xml_respuesta_tributacion = fields.Char(
        string="XML File Name Tributación Response", required=False,
        copy=False)
    xml_comprobante = fields.Binary(
        string="XML voucher", required=False, copy=False, attachment=True)
    fname_xml_comprobante = fields.Char(
        string="File name XML voucher", required=False, copy=False,
        attachment=True)
    xml_supplier_approval = fields.Binary(
        string="Vendor XML", required=False, copy=False, attachment=True)
    fname_xml_supplier_approval = fields.Char(
        string="Vendor XML voucher file name", required=False,
        copy=False, attachment=True)
    amount_tax_electronic_invoice = fields.Monetary(
        string='Total FE taxes', readonly=True, )
    amount_total_iva_devuelto = fields.Monetary(
        string='IVA Devuelto', copy=False, readonly=True, )
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
                    ('FEC', 'Factura Electrónica de Compra')],
        string="Voucher Type",
        required=False, default='FE',
        help='Indicates the type of document according to the classification of the Ministerio de Hacienda')

    sequence = fields.Char(string='Consecutive', readonly=True, copy=False)

    state_email = fields.Selection([('no_email', 'Sin cuenta de correo'), (
        'sent', 'Enviado'), ('fe_error', 'Error FE')], 'Estado email', copy=False)

    invoice_amount_text = fields.Char(string='Amount in Letters', readonly=True, required=False, )

    ignore_total_difference = fields.Boolean(string="Ignore Difference in Totals", required=False, default=False)

    error_count = fields.Integer(string="Number of errors", required=False, default="0")

    economic_activity_id = fields.Many2one("economic.activity", string="Economic Activity", required=False, context={'active_test': False}, )

    economic_activities_ids = fields.Many2many('economic.activity', string=u'Economic activities', compute='_get_economic_activities', context={'active_test': False})

    not_loaded_invoice = fields.Char(string='Original Invoice Number not loaded', readonly=True, )

    not_loaded_invoice_date = fields.Date(string='Original Invoice Date not loaded', readonly=True, )

    _sql_constraints = [
        ('number_electronic_uniq', 'unique (company_id, number_electronic)',
            "La clave de comprobante debe ser única"),
    ]

    
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')
    partner_vat = fields.Char(string='Partner Tax ID',related="partner_id.vat",store=True, index=True, help="The Parnter Tax Identification Number.")
    company_vat = fields.Char(string='Company Tax ID',related="partner_id.vat",store=True, index=True, help="Your Company Tax Identification Number.")

    def _generate_qr_code(self):
        qr_info = ''
        if self.env.user.company_id.invoice_qr_type != 'by_info':
            qr_info = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            qr_info += self.get_portal_url()
        else:   
            if self.env.user.company_id.invoice_field_ids:
                result = self.search_read([('id', 'in', self.ids)],
                self.env.user.company_id.invoice_field_ids.mapped('field_id.name'))
                dict_result = {}   
                for ffild in self.env.user.company_id.invoice_field_ids.mapped('field_id'):
                    if ffild.ttype == 'many2one':
                        dict_result[ffild.field_description] = self[ffild.name].display_name
                    else:
                        dict_result[ffild.field_description] = self[ffild.name]
                for key,value in dict_result.items():
                    if str(key).__contains__('Partner') or str(key).__contains__(_('Partner')):
                        if self.move_type in ['out_invoice','out_refund']:
                            key = str(key).replace(_('Partner'),_('Customer'))    
                        elif self.move_type in ['in_invoice','in_refund']:
                            key = str(key).replace(_('Partner'),_('Vendor'))   
                    qr_info += f"{key} : {value} <br/>" 
                qr_info = html2plaintext(qr_info)                                                                                                                                 
        self.qr_image = generateQrCode.generate_qr_code(qr_info)


    @api.onchange('partner_id', 'company_id')
    def _get_economic_activities(self):
        for inv in self:
            if inv.move_type in ('in_invoice', 'in_refund'):
                if inv.partner_id:
                    if inv.partner_id.economic_activities_ids:
                        inv.economic_activities_ids = inv.partner_id.economic_activities_ids
                        inv.economic_activity_id = inv.partner_id.activity_id
                    else:
                        raise UserError(_('The partner %s has no defined economic activity, please validate the information in the business partner before placing it!') % inv.partner_id.name)
                else:
                    inv.economic_activities_ids = self.env['economic.activity'].search([])
            else:
                inv.economic_activities_ids = self.env['economic.activity'].search([('active', '=', True)])

    
    @api.onchange('partner_id')
    def _partner_changed(self):
        if self.partner_id.export:
            self.tipo_documento = 'FEE'

        if self.move_type in ('in_invoice', 'in_refund'):
            if self.partner_id:
                if self.partner_id.payment_methods_id:
                    self.payment_methods_id = self.partner_id.payment_methods_id
                else:
                    raise UserError(_('Partner does not have a default payment method'))

    def action_invoice_sent_mass(self):

        if self.invoice_id.move_type == 'in_invoice' or self.invoice_id.move_type == 'in_refund':
            email_template = self.env.ref('cr_electronic_invoice.email_template_invoice_vendor', raise_if_not_found=False)
        else:
            email_template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)

        email_template.attachment_ids = [(5, 0, 0)]

        lang = False
        if email_template:
            lang = email_template._render_lang(self.ids)[self.id]
        if not lang:
            lang = get_lang(self.env).code

        if self.env.user.company_id.frm_ws_ambiente == 'disabled':
            pass
            #email_template.with_context(type='binary', default_type='binary').send_mail(self.id, raise_exception=False, force_send=True)  # default_type='binary'
        elif self.partner_id and self.partner_id.email:  # and not i.partner_id.opt_out:

            domain = [('res_model', '=', 'account.move'), ('res_id', '=', self.id), ('name', 'like', self.tipo_documento + '_'+ self.number_electronic)]
            attachment = self.env['ir.attachment'].sudo().search(domain, limit=1)

            if attachment:
                attachment.name = self.fname_xml_comprobante

                domain_resp = [('res_model', '=', 'account.move'), ('res_id', '=', self.id),
                               ('name', 'like', 'AHC_' + self.number_electronic)]
                attachment_resp = self.env['ir.attachment'].sudo().search(domain_resp, limit=1)

                if attachment_resp:
                    attachment_resp.name = self.fname_xml_respuesta_tributacion

                    email_template.attachment_ids = [
                        (6, 0, [attachment.id, attachment_resp.id])]
                    email_template.with_context(type='binary',
                                                default_type='binary').send_mail(
                        self.id,
                        raise_exception=False,
                        force_send=True)

                    email_template.attachment_ids = [(5)]
                else:
                    raise UserError(_('Response XML from Hacienda has not been received'))
            else:
                raise UserError(_('Invoice XML has not been generated for id:' + str(self.id)))

        else:
            raise UserError(_('Partner is not assigne to this invoice'))

    def action_invoice_sent(self):
        self.ensure_one()

        if self.invoice_id.move_type == 'in_invoice' or self.invoice_id.move_type == 'in_refund':
            email_template = self.env.ref('cr_electronic_invoice.email_template_invoice_vendor', raise_if_not_found=False)
        else:
            email_template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)

        email_template.attachment_ids = [(5, 0, 0)]

        lang = False
        if email_template:
            lang = email_template._render_lang(self.ids)[self.id]
        if not lang:
            lang = get_lang(self.env).code

        if self.env.user.company_id.frm_ws_ambiente == 'disabled':
            pass
            #email_template.with_context(type='binary', default_type='binary').send_mail(self.id, raise_exception=False, force_send=True)  # default_type='binary'
        elif self.partner_id and self.partner_id.email:  # and not i.partner_id.opt_out:

            domain = [('res_model', '=', 'account.move'), ('res_id', '=', self.id), ('name', 'like', self.tipo_documento + '_'+ self.number_electronic)]
            attachment = self.env['ir.attachment'].sudo().search(domain, limit=1)

            if attachment:
                attachment.name = self.fname_xml_comprobante

                domain_resp = [('res_model', '=', 'account.move'), ('res_id', '=', self.id),
                               ('name', 'like', 'AHC_' + self.number_electronic)]
                attachment_resp = self.env['ir.attachment'].sudo().search(domain_resp, limit=1)

                if attachment_resp:
                    attachment_resp.name = self.fname_xml_respuesta_tributacion

                    email_template.attachment_ids = [
                        (6, 0, [attachment.id, attachment_resp.id])]
                else:
                    raise UserError(_('Response XML from Hacienda has not been received'))
            else:
                raise UserError(_('Invoice XML has not been generated for id:' + str(self.id)))

        else:
            raise UserError(_('Partner is not assigne to this invoice'))

        compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False).sudo()
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            default_res_model='account.move',
            default_use_template=bool(email_template),
            default_template_id=email_template and email_template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            custom_layout="mail.mail_notification_paynow",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True
        )
        return {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

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
            self.xml_supplier_approval = False
            self.fname_xml_supplier_approval = False
            self.xml_respuesta_tributacion = False
            self.fname_xml_respuesta_tributacion = False
            self.date_issuance = False
            self.number_electronic = False
            self.state_invoice_partner = False

    
    def load_xml_data(self):
        account = False
        analytic_account = False
        product = False        

        purchase_journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        default_account_id = purchase_journal.expense_account_id.id

        load_lines = purchase_journal.load_lines

        if default_account_id:
            account = self.env['account.account'].search([('id', '=', default_account_id)], limit=1)
        else:
            default_account_id = self.env['ir.config_parameter'].sudo().get_param('expense_account_id')
            if default_account_id:
                account = self.env['account.account'].search([('id', '=', default_account_id)], limit=1)

        analytic_account_id = purchase_journal.expense_analytic_account_id.id


        if analytic_account_id:
            analytic_account = self.env['account.analytic.account'].search([('id', '=', analytic_account_id)], limit=1)
        else:
            analytic_account_id = self.env['ir.config_parameter'].sudo().get_param('expense_analytic_account_id')
            if analytic_account_id:
                analytic_account = self.env['account.analytic.account'].search([('id', '=', analytic_account_id)], limit=1)
            
        product_id = purchase_journal.expense_product_id.id

        if product_id:
            product = self.env['product.product'].search([('id', '=', product_id)], limit=1)
        else:
            product_id = self.env['ir.config_parameter'].sudo().get_param('expense_product_id')
            if product_id:
                product = self.env['product.product'].search([('id', '=', product_id)], limit=1)
            
        api_facturae.load_xml_data(self, load_lines, account, product, analytic_account)

    
    def action_send_mrs_to_hacienda(self):
        if self.state_invoice_partner:
            self.state_tributacion = False
            self.send_mrs_to_hacienda()
        else:
            raise UserError(_('You must select the aceptance state: Accepted, Parcial Accepted or Rejected'))

    
    def send_mrs_to_hacienda(self):
        for inv in self:
            if inv.xml_supplier_approval:

                '''Verificar si el MR ya fue enviado y estamos esperando la confirmación'''
                if inv.state_tributacion == 'procesando':

                    token_m_h = api_facturae.get_token_hacienda(
                        inv, inv.company_id.frm_ws_ambiente)

                    api_facturae.consulta_documentos(inv, inv,
                                                        inv.company_id.frm_ws_ambiente,
                                                        token_m_h,
                                                        api_facturae.get_time_hacienda(),
                                                        False)
                else:

                    if inv.state_tributacion and inv.state_tributacion in ('aceptado', 'rechazado', 'na'):
                        raise UserError('Aviso!.\n La factura de proveedor ya fue confirmada')
                    if not inv.amount_total_electronic_invoice and inv.xml_supplier_approval:
                        try:
                            inv.load_xml_data()
                        except UserError as error:
                            inv.state_tributacion='error'
                            inv.message_post(
                                subject='Error',
                                body='Aviso!.\n Error en carga del XML del proveedor'+str(error))
                            continue

                    if abs(
                            inv.amount_total_electronic_invoice - inv.amount_total) > 1:
                        inv.state_tributacion = 'error'
                        inv.message_post(
                            subject='Error',
                            body='Aviso!.\n Monto total no concuerda con monto del XML')
                        continue

                    elif not inv.xml_supplier_approval:
                        inv.state_tributacion = 'error'
                        inv.message_post(
                            subject='Error',
                            body='Aviso!.\n No se ha cargado archivo XML')
                        continue

                    elif not inv.company_id.sucursal_MR or not inv.company_id.terminal_MR:
                        inv.state_tributacion = 'error'
                        inv.message_post(subject='Error',
                                            body='Aviso!.\nPor favor configure el diario de compras, terminal y sucursal')
                        continue

                    if not inv.state_invoice_partner:
                        inv.state_tributacion = 'error'
                        inv.message_post(subject='Error',
                                            body='Aviso!.\nDebe primero seleccionar el tipo de respuesta para el archivo cargado.')
                        continue

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
                            if inv.state_tributacion == 'rechazado' or inv.state_tributacion == 'error':
                                message_description += '<p><b>Cambiando consecutivo del Mensaje de Receptor</b> <br />' \
                                                        '<b>Consecutivo anterior: </b>' + inv.consecutive_number_receiver + \
                                                        '<br/>' \
                                                        '<b>Estado anterior: </b>' + inv.state_tributacion + '</p>'

                            '''Solicitamos la clave para el Mensaje Receptor'''
                            response_json = api_facturae.get_clave_hacienda(
                                inv, tipo_documento, sequence,
                                inv.company_id.sucursal_MR,
                                inv.company_id.terminal_MR)

                            inv.consecutive_number_receiver = response_json.get(
                                'consecutivo')
                            '''Generamos el Mensaje Receptor'''
                            if inv.amount_total_electronic_invoice is None or inv.amount_total_electronic_invoice == 0:
                                inv.state_tributacion = 'error'
                                inv.message_post(subject='Error',
                                                body='El monto Total de la Factura para el Mensaje Receptro es inválido')
                                continue

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

                            if inv.state_tributacion != 'procesando':

                                env = inv.company_id.frm_ws_ambiente
                                token_m_h = api_facturae.get_token_hacienda(
                                    inv, inv.company_id.frm_ws_ambiente)

                                response_json = api_facturae.send_message(
                                    inv, api_facturae.get_time_hacienda(),
                                    xml_firmado,
                                    token_m_h, env)
                                status = response_json.get('status')

                                if 200 <= status <= 299:
                                    inv.state_tributacion = 'procesando'
                                else:
                                    inv.state_tributacion = 'error'
                                    _logger.error(
                                        'E-INV CR - Invoice: %s  Error sending Acceptance Message: %s',
                                        inv.number_electronic,
                                        response_json.get('text'))

                                if inv.state_tributacion == 'procesando':
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
                                        inv.state_tributacion = response_json.get(
                                            'ind-estado')
                                        inv.xml_respuesta_tributacion = response_json.get(
                                            'respuesta-xml')
                                        inv.fname_xml_respuesta_tributacion = 'ACH_' + \
                                                                                inv.number_electronic + '-' + inv.consecutive_number_receiver + '.xml'

                                        _logger.error(
                                            'E-INV CR - Estado Documento:%s',
                                            inv.state_tributacion)

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
                                            inv.state_tributacion)

                                    elif status == 400:
                                        inv.state_tributacion = 'ne'
                                        _logger.error(
                                            'MAB - Aceptacion Documento:%s no encontrado en Hacienda.',
                                            inv.number_electronic + '-' + inv.consecutive_number_receiver)
                                    else:
                                        _logger.error(
                                            'MAB - Error inesperado en Send Acceptance File - Abortando')
                                        return

    

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        super(AccountInvoiceElectronic, self)._onchange_partner_id()
        self.payment_methods_id = self.partner_id.payment_methods_id

        if self.move_type == 'out_refund':
            self.tipo_documento = 'NC'
        elif self.partner_id and self.partner_id.vat:
            if self.partner_id.country_id and self.partner_id.country_id.code != 'CR':
                self.tipo_documento = 'TE'
            elif self.partner_id.identification_id and self.partner_id.identification_id.code == '05':
                self.tipo_documento = 'TE'
            else:
                self.tipo_documento = 'FE'
        else:
            self.tipo_documento = 'TE'

        if self.move_type in ('in_invoice', 'in_refund'):
            self.economic_activity_id = self.partner_id.activity_id
        else:
            self.economic_activity_id = self.company_id.activity_id

    @api.model
    # cron Job that verifies if the invoices are Validated at Tributación
    def _check_hacienda_for_invoices(self, max_invoices=10):
        out_invoices = self.env['account.move'].search(
            [('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', ('posted')),
                ('state_tributacion', 'in', ('recibido', 'procesando', 'ne'))],  # , 'error'
            limit=max_invoices)

        in_invoices = self.env['account.move'].search(
            [('move_type', '=', 'in_invoice'),
                ('tipo_documento', '=', 'FEC'),
                ('state', 'in', ('open', 'paid')),
                ('state_tributacion', 'in', ('procesando', 'ne', 'error'))],
            limit=max_invoices)

        invoices = out_invoices | in_invoices

        total_invoices = len(invoices)
        current_invoice = 0

        _logger.info('E-INV CR - Consulta Hacienda - Facturas a Verificar: %s', total_invoices)

        for i in invoices:
            current_invoice += 1
            _logger.info('E-INV CR - Consulta Hacienda - Invoice %s / %s  -  number:%s', current_invoice, total_invoices, i.number_electronic)

            token_m_h = api_facturae.get_token_hacienda(
                i, i.company_id.frm_ws_ambiente)
            if not token_m_h:
                _logger.error(
                    'E-INV CR - Consulta Hacienda - HALTED - Failed to get token')
                return

            if not i.xml_comprobante:
                i.state_tributacion = 'error'
                _logger.warning(
                    u'E-INV CR - Documento:%s no tiene documento XML.  Estado: %s',
                    i.number_electronic, 'error')
                continue

            if not i.number_electronic or len(i.number_electronic) != 50:
                i.state_tributacion = 'error'
                _logger.warning(
                    u'E-INV CR - Documento:%s no cumple con formato de número electrónico.  Estado: %s',
                    i.number, 'error')
                continue

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

            i.state_tributacion = estado_m_h

            if estado_m_h == 'aceptado':
                i.fname_xml_respuesta_tributacion = 'AHC_' + i.number_electronic + '.xml'
                i.xml_respuesta_tributacion = response_json.get(
                    'respuesta-xml')
                if i.tipo_documento != 'FEC' and i.partner_id and i.partner_id.email:  # and not i.partner_id.opt_out:
                    email_template = self.env.ref(
                        'account.email_template_edi_invoice', False)
                    attachment = self.env['ir.attachment'].create(
                        {'name': i.fname_xml_comprobante,
                         'type': 'binary',
                         'datas': i.xml_comprobante,
                         'res_model': self._name,
                         'mimetype': 'text/xml',
                         'res_id': i.id
                         })
                    attachment_resp = self.env['ir.attachment'].create(
                        {'name': i.fname_xml_respuesta_tributacion,
                         'type': 'binary',
                         'datas': i.xml_respuesta_tributacion,
                         'res_model': self._name,
                         'mimetype': 'text/xml',
                         'res_id': i.id
                         })


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
                i.xml_respuesta_tributacion = response_json.get('respuesta-xml')
            else:
                if i.error_count > 10:
                    i.state_tributacion = 'error'
                elif i.error_count < 4:
                    i.error_count += 1
                    i.state_tributacion = 'procesando'
                else:
                    i.error_count += 1
                    i.state_tributacion = ''
                # doc.state_tributacion = 'no_encontrado'
                _logger.error('MAB - Consulta Hacienda - Invoice not found: %s  -  Estado Hacienda: %s', i.number_electronic, estado_m_h)

    
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
        invoices = self.env['account.move'].search(
            [('move_type', 'in', ('in_invoice', 'in_refund')),
                ('tipo_documento', '!=', 'FEC'),
                ('state', 'in', ('open', 'paid')),
                ('xml_supplier_approval', '!=', False),
                ('state_invoice_partner', '!=', False),
                ('state_tributacion', 'not in', ('aceptado', 'rechazado', 'error', 'na'))],
            limit=max_invoices)
        total_invoices = len(invoices)
        current_invoice = 0

        for inv in invoices:
            # CWong: esto no debe llamarse porque cargaría de nuevo los impuestos y ya se pusieron como debería
            # if not i.amount_total_electronic_invoice:
            #     i.charge_xml_data()
            current_invoice += 1
            _logger.info(
                '_check_hacienda_for_mrs - Invoice %s / %s  -  number:%s',
                current_invoice, total_invoices, inv.number_electronic)
            inv.send_mrs_to_hacienda()

    
    def action_create_fec(self):
        if self.company_id.frm_ws_ambiente == 'disabled':
            raise UserError(_('Hacienda API is disabled in company'))
        else:
            self.generate_and_send_invoices(self)

    @api.model
    def _send_invoices_to_hacienda(self, max_invoices=10):  # cron
        days_left = self.env.user.company_id.get_days_left()
        _logger.debug('E-INV CR - Ejecutando _send_invoices_to_hacienda')
        invoices = self.env['account.move'].search([('move_type', 'in', ['out_invoice', 'out_refund']),
                                                        ('state', '=', 'posted'),
                                                        ('number_electronic', '!=', False),
                                                        ('invoice_date', '>=', '2019-07-01'),
                                                        '|', ('state_tributacion', '=', False), ('state_tributacion', '=', 'ne')],
                                                        order='id asc', limit=max_invoices)

        if days_left >= 0:
            self.generate_and_send_invoices(invoices)
        else:
            message = self.env.user.company_id.get_message_to_send()
            for inv in invoices:
                inv.message_post(
                    body=message,
                    subject='NOTIFICACIÓN IMPORTANTE!!',
                    message_type='notification',
                    subtype=None,
                    parent_id=False,
                )
        _logger.info('E-INV CR - _send_invoices_to_hacienda - Finalizado Exitosamente')

    def generate_and_send_invoice(self):
        days_left = self.env.user.company_id.get_days_left()
        if days_left >= 0:
            self.generate_and_send_invoices(self)
        else:
            message = self.env.user.company_id.get_message_to_send()
            self.message_post(
                    body=message,
                    subject='NOTIFICACIÓN IMPORTANTE!!',
                    message_type='notification',
                    subtype=None,
                    parent_id=False,
                )
        _logger.info('E-INV CR - _send_invoices_to_hacienda - Finalizado Exitosamente')


    def generate_and_send_invoices(self, invoices):
        total_invoices = len(invoices)
        current_invoice = 0

        days_left = self.env.user.company_id.get_days_left()
        message = self.env.user.company_id.get_message_to_send()

        for inv in invoices:
            current_invoice += 1

            if days_left <= self.env.user.company_id.range_days:
                inv.message_post(
                    body=message,
                    subject='NOTIFICACIÓN IMPORTANTE!!',
                    message_type='notification',
                    subtype=None,
                    parent_id=False,
                )


            if not inv.sequence or not inv.sequence.isdigit():  # or (len(inv.number) == 10):
                inv.state_tributacion = 'na'
                _logger.info('E-INV CR - Ignored invoice:%s', inv.number)
                continue

            _logger.debug('generate_and_send_invoices - Invoice %s / %s  -  number:%s',
                            current_invoice, total_invoices, inv.number_electronic)

            if not inv.xml_comprobante or (inv.tipo_documento == 'FEC' and inv.state_tributacion == 'rechazado'):

                if inv.tipo_documento == 'FEC' and inv.state_tributacion == 'rechazado':
                    inv.message_post(body='Se está enviando otra FEC porque la anterior fue rechazada por Hacienda. Adjuntos los XMLs anteriores. Clave anterior: ' + inv.number_electronic,
                                        subject='Envío de una segunda FEC',
                                        message_type='notification',
                                        subtype=None,
                                        parent_id=False,
                                        attachments=[[inv.fname_xml_respuesta_tributacion, inv.fname_xml_respuesta_tributacion],
                                                    [inv.fname_xml_comprobante, inv.fname_xml_comprobante]],)

                    sequence = inv.company_id.FEC_sequence_id.next_by_id()
                    response_json = api_facturae.get_clave_hacienda(self,
                                                                    inv.tipo_documento,
                                                                    sequence,
                                                                    inv.journal_id.sucursal,
                                                                    inv.journal_id.terminal)

                    inv.number_electronic = response_json.get('clave')
                    inv.sequence = response_json.get('consecutivo')

                now_utc = datetime.datetime.now(pytz.timezone('UTC'))
                now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
                dia = '%02d' % now_cr.day
                mes = '%02d' % now_cr.month
                anno = str(now_cr.year)[2:4]
                # date_cr = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")
                # date_cr = api_facturae.get_time_hacienda()
                date_cr = now_cr.strftime("20" + anno + "-" + mes + "-" + dia + "T%H:%M:%S-06:00")

                inv.date_issuance = date_cr

                numero_documento_referencia = False
                fecha_emision_referencia = False
                codigo_referencia = False
                tipo_documento_referencia = False
                razon_referencia = False
                currency = inv.currency_id
                invoice_comments = escape(inv.narration)

                if (inv.invoice_id or inv.not_loaded_invoice) and inv.reference_code_id and inv.reference_document_id:
                    if inv.invoice_id:
                        if inv.invoice_id.number_electronic:
                            numero_documento_referencia = inv.invoice_id.number_electronic
                            fecha_emision_referencia = inv.invoice_id.date_issuance
                        else:
                            numero_documento_referencia = inv.invoice_id and re.sub('[^0-9]+', '', inv.invoice_id.sequence).rjust(50, '0') or '0000000'
                            invoice_date = datetime.datetime.strptime(inv.invoice_id and inv.invoice_id.invoice_date or '2018-08-30', "%Y-%m-%d")
                            fecha_emision_referencia = invoice_date.strftime("%Y-%m-%d") + "T12:00:00-06:00"
                    else:
                        numero_documento_referencia = inv.not_loaded_invoice
                        fecha_emision_referencia = inv.not_loaded_invoice_date.strftime("%Y-%m-%d") + "T12:00:00-06:00"
                    tipo_documento_referencia = inv.reference_document_id.code
                    codigo_referencia = inv.reference_code_id.code
                    razon_referencia = inv.reference_code_id.name

                if inv.invoice_payment_term_id:
                    sale_conditions = inv.invoice_payment_term_id.sale_conditions_id and inv.invoice_payment_term_id.sale_conditions_id.sequence or '01'
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
                total_servicio_salon = 0.0
                total_servicio_gravado = 0.0
                total_servicio_exento = 0.0
                total_servicio_exonerado = 0.0
                total_mercaderia_gravado = 0.0
                total_mercaderia_exento = 0.0
                total_mercaderia_exonerado = 0.0
                total_descuento = 0.0
                total_impuestos = 0.0
                base_subtotal = 0.0
                _old_rate_exoneration = False
                _no_CABYS_code = False

                # Revisamos si existe IVA Devuelto
                if inv.amount_total_iva_devuelto:
                    total_iva_devuelto = inv.amount_total_iva_devuelto
                    inv.amount_total -= inv.amount_total_iva_devuelto
                else:
                    total_iva_devuelto = 0.0

                for inv_line in inv.invoice_line_ids:
                    # Revisamos si está línea es de Otros Cargos
                    if inv_line.product_id and inv_line.product_id.id == self.env.ref('cr_electronic_invoice.product_iva_devuelto').id:
                        total_iva_devuelto = -inv_line.price_total

                    elif inv_line.product_id and inv_line.product_id.categ_id.name == 'Otros Cargos':
                        otros_cargos_id += 1
                        otros_cargos[otros_cargos_id] = {
                            'TipoDocumento': inv_line.product_id.default_code,
                            'Detalle': escape(inv_line.name[:150]),
                            'MontoCargo': inv_line.price_total
                        }
                        if inv_line.third_party_id:
                            otros_cargos[otros_cargos_id]['NombreTercero'] = inv_line.third_party_id.name

                            if inv_line.third_party_id.vat:
                                otros_cargos[otros_cargos_id]['NumeroIdentidadTercero'] = inv_line.third_party_id.vat

                        total_otros_cargos += inv_line.price_total

                    else:
                        line_number += 1
                        price = inv_line.price_unit
                        quantity = inv_line.quantity
                        if not quantity:
                            continue

                        line_taxes = inv_line.tax_ids.compute_all(
                            price, currency, 1,
                            product=inv_line.product_id,
                            partner=inv_line.move_id.partner_id)

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
                            "unidadMedida": inv_line.product_uom_id and inv_line.product_uom_id.code or 'Sp'
                        }

                        if inv_line.product_id:
                            line["codigo"] = inv_line.product_id.default_code or ''
                            line["codigoProducto"] = inv_line.product_id.code or ''

                            if inv_line.product_id.cabys_code:
                                line["codigoCabys"] = inv_line.product_id.cabys_code
                            elif inv_line.product_id.categ_id and inv_line.product_id.categ_id.cabys_code:
                                line["codigoCabys"] = inv_line.product_id.categ_id.cabys_code
                            else:
                                _no_CABYS_code = 'Aviso!.\nLinea sin código CABYS: %s' % inv_line.name
                                continue
                        else:
                            _no_CABYS_code = 'Aviso!.\nLinea sin código CABYS: %s' % inv_line.name
                            continue

                        if inv.tipo_documento == 'FEE' and inv_line.tariff_head:
                            line["partidaArancelaria"] = inv_line.tariff_head

                        if inv_line.discount and price_unit > 0:
                            total_descuento += descuento
                            line["montoDescuento"] = descuento
                            line["naturalezaDescuento"] = inv_line.discount_note or 'Descuento Comercial'

                        # Se generan los impuestos
                        taxes = dict()
                        _line_tax = 0.0
                        _tax_exoneration = False
                        _percentage_exoneration = 0
                        if inv_line.tax_ids:
                            tax_index = 0

                            taxes_lookup = {}
                            for i in inv_line.tax_ids:
                                if i.has_exoneration:
                                    _tax_exoneration = True
                                    _tax_rate = i.tax_root.amount
                                    _tax_exoneration_rate = min(i.percentage_exoneration, _tax_rate)
                                    _percentage_exoneration = _tax_exoneration_rate / _tax_rate
                                    if i.percentage_exoneration > 13:
                                        _old_rate_exoneration = True
                                    taxes_lookup[i.id] = {'tax_code': i.tax_root.tax_code,
                                                            'tarifa': _tax_rate,
                                                            'iva_tax_desc': i.tax_root.iva_tax_desc,
                                                            'iva_tax_code': i.tax_root.iva_tax_code,
                                                            'exoneration_percentage': _tax_exoneration_rate,
                                                            'amount_exoneration': i.amount}
                                else:
                                    _tax_rate = i.amount
                                    taxes_lookup[i.id] = {'tax_code': i.tax_code,
                                                            'tarifa': _tax_rate,
                                                            'iva_tax_desc': i.iva_tax_desc,
                                                            'iva_tax_code': i.iva_tax_code}

                            for i in line_taxes['taxes']:
                                if taxes_lookup[i['id']]['tax_code'] == 'service':
                                    total_servicio_salon += round(
                                        subtotal_line * taxes_lookup[i['id']]['tarifa'] / 100, 5)

                                elif taxes_lookup[i['id']]['tax_code'] != '00':
                                    tax_index += 1
                                    product_amount = round(i['base']*quantity)
                                    tax_amount = round((product_amount - descuento) * taxes_lookup[i['id']]['tarifa'] / 100, 5)
                                    _line_tax += tax_amount
                                    tax = {
                                        'codigo': taxes_lookup[i['id']]['tax_code'],
                                        'tarifa': taxes_lookup[i['id']]['tarifa'],
                                        'monto': tax_amount,
                                        'iva_tax_desc': taxes_lookup[i['id']]['iva_tax_desc'],
                                        'iva_tax_code': taxes_lookup[i['id']]['iva_tax_code'],
                                    }
                                    # Se genera la exoneración si existe para este impuesto
                                    if _tax_exoneration:
                                        _tax_amount_exoneration = round(
                                            tax_amount - subtotal_line * taxes_lookup[i['id']]['amount_exoneration'] / 100, 5)

                                        if _tax_amount_exoneration == 0.0:
                                            _tax_amount_exoneration = tax_amount

                                        _line_tax -= _tax_amount_exoneration
                                        
                                        tax["exoneracion"] = {
                                            "montoImpuesto": _tax_amount_exoneration,
                                            "porcentajeCompra": int(taxes_lookup[i['id']]['exoneration_percentage'])
                                        }

                                    taxes[tax_index] = tax

                            line["impuesto"] = taxes
                            line["impuestoNeto"] = round(_line_tax, 5)

                        # Si no hay product_uom_id se asume como Servicio
                        if not inv_line.product_uom_id or inv_line.product_uom_id.category_id.name in ('Services', 'Servicios'):  # inv_line.product_id.move_type == 'service'
                            if taxes:
                                if _tax_exoneration:
                                    if _percentage_exoneration < 1:
                                        total_servicio_gravado += (base_line *  (1-_percentage_exoneration))
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
                                        total_mercaderia_gravado += (base_line *  (1-_percentage_exoneration))
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
                if total_servicio_salon:
                    total_servicio_salon = round(total_servicio_salon, 5)
                    total_otros_cargos += total_servicio_salon
                    otros_cargos_id += 1
                    otros_cargos[otros_cargos_id] = {
                        'TipoDocumento': '06',
                        'Detalle': escape('Servicio salon 10%'),
                        'MontoCargo': total_servicio_salon
                    }

                # TODO: CORREGIR BUG NUMERO DE FACTURA NO SE GUARDA EN LA REFERENCIA DE LA NC CUANDO SE CREA MANUALMENTE
                if not inv.invoice_origin:
                    inv.invoice_origin = inv.invoice_id.display_name

                if _no_CABYS_code and inv.tipo_documento != 'NC':  # CAByS is not required for financial NCs
                    inv.message_post(
                        subject='Error',
                        body=_no_CABYS_code)
                    if inv.tipo_documento == 'FEC':
                        raise UserError(_no_CABYS_code)
                    continue

                if _old_rate_exoneration:
                    inv.state_tributacion = 'error'
                    inv.message_post(
                        subject='Error',
                        body='Revisar definición de impuesto con exoneración, está en base 100 y debe ser base 13')
                    continue

                if abs(base_subtotal + total_impuestos + total_otros_cargos - total_iva_devuelto - inv.amount_total) > 0.5:
                    inv.state_tributacion = 'error'
                    inv.message_post(
                        subject='Error',
                        body='Monto factura no concuerda con monto para XML. Factura: %s XML:%s base:%s impuestos:%s otros_cargos:%s iva_devuelto:%s' % (
                            inv.amount_total, (base_subtotal + total_impuestos + total_otros_cargos - total_iva_devuelto), base_subtotal, total_impuestos, total_otros_cargos, total_iva_devuelto))
                    continue
                total_servicio_gravado = round(total_servicio_gravado, 5)
                total_servicio_exento = round(total_servicio_exento, 5)
                total_servicio_exonerado = round(total_servicio_exonerado,5)
                total_mercaderia_gravado = round(total_mercaderia_gravado, 5)
                total_mercaderia_exento = round(total_mercaderia_exento, 5)
                total_mercaderia_exonerado = round(total_mercaderia_exonerado, 5)
                total_otros_cargos = round(total_otros_cargos, 5)
                total_iva_devuelto = round(total_iva_devuelto, 5)
                base_subtotal = round(base_subtotal, 5)
                total_impuestos = round(total_impuestos, 5)
                total_descuento = round(total_descuento, 5)
                # ESTE METODO GENERA EL XML DIRECTAMENTE DESDE PYTHON
                xml_string_builder = api_facturae.gen_xml_v43(
                    inv, sale_conditions, total_servicio_gravado,
                    total_servicio_exento, total_servicio_exonerado,
                    total_mercaderia_gravado, total_mercaderia_exento,
                    total_mercaderia_exonerado, total_otros_cargos, total_iva_devuelto, base_subtotal,
                    total_impuestos, total_descuento, lines,
                    otros_cargos, currency_rate, invoice_comments,
                    tipo_documento_referencia, numero_documento_referencia,
                    fecha_emision_referencia, codigo_referencia, razon_referencia)

                xml_to_sign = str(xml_string_builder)
                xml_firmado = api_facturae.sign_xml(
                    inv.company_id.signature,
                    inv.company_id.frm_pin,
                    xml_to_sign)

                inv.xml_comprobante = base64.encodestring(xml_firmado)
                inv.fname_xml_comprobante = inv.tipo_documento + '_' + inv.number_electronic + '.xml'

                _logger.info('E-INV CR - SIGNED XML:%s', inv.fname_xml_comprobante)
            else:
                xml_firmado = inv.xml_comprobante

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
                    inv.state_tributacion = 'procesando'
                else:
                    inv.state_tributacion = 'procesando'
                inv.electronic_invoice_return_message = response_text
            else:
                if response_text.find('ya fue recibido anteriormente') != -1:
                    if inv.tipo_documento == 'FEC':
                        inv.state_tributacion = 'procesando'
                    else:
                        inv.state_tributacion = 'procesando'
                    inv.message_post(subject='Error', body='Ya recibido anteriormente, se pasa a consultar')
                elif inv.error_count > 10:
                    inv.message_post(subject='Error', body=response_text)
                    inv.electronic_invoice_return_message = response_text
                    inv.state_tributacion = 'error'
                    _logger.error('E-INV CR  - Invoice: %s  Status: %s Error sending XML: %s' % (inv.number_electronic, response_status, response_text))
                else:
                    inv.error_count += 1
                    if inv.tipo_documento == 'FEC':
                        inv.state_tributacion = 'procesando'
                    else:
                        inv.state_tributacion = 'procesando'
                    inv.message_post(subject='Error', body=response_text)
                    _logger.error('E-INV CR  - Invoice: %s  Status: %s Error sending XML: %s' % (inv.number_electronic, response_status, response_text))

    
    def action_post(self):
        # Revisamos si el ambiente para Hacienda está habilitado
        for inv in self:
            if inv.company_id.frm_ws_ambiente == 'disabled':
                super(AccountInvoiceElectronic, inv).action_post()
                inv.tipo_documento = None
                continue

            if inv.partner_id.has_exoneration and inv.partner_id.date_expiration and (inv.partner_id.date_expiration < datetime.date.today()):
                raise UserError('La exoneración de este cliente se encuentra vencida')

            currency = inv.currency_id
            sequence = False
            if (inv.invoice_id ) and not (inv.invoice_id and inv.reference_code_id and inv.reference_document_id):
                raise UserError('Datos incompletos de referencia para nota de crédito')
            elif (inv.not_loaded_invoice or inv.not_loaded_invoice_date) and not (inv.not_loaded_invoice and inv.not_loaded_invoice_date and inv.reference_code_id and inv.reference_document_id):
                raise UserError('Datos incompletos de referencia para nota de crédito no cargada')

            # Digital Invoice or ticket
            if inv.move_type in ('out_invoice', 'out_refund') and inv.number_electronic:  # Keep original Number Electronic
                pass   
            elif inv.move_type == 'out_invoice':
                # tipo de identificación
                if inv.partner_id and inv.partner_id.vat and not inv.partner_id.identification_id:
                    raise UserError('Seleccione el tipo de identificación del cliente en su perfil')
                # Verificar si es nota DEBITO
                # if inv.invoice_id and inv.journal_id and (
                #         inv.journal_id.code == 'NDV'):
                #     tipo_documento = 'ND'
                #     sequence = inv.journal_id.ND_sequence_id.next_by_id()
                #
                # else:

                if inv.tipo_documento == 'FE' and (not inv.partner_id.vat or inv.partner_id.identification_id.code == '05'):
                    inv.tipo_documento = 'TE'

                if inv.tipo_documento == 'FE':
                    sequence = inv.journal_id.FE_sequence_id.next_by_id()
                elif inv.tipo_documento == 'TE':
                    sequence = inv.journal_id.TE_sequence_id.next_by_id()
                elif inv.tipo_documento == 'FEE':
                    sequence = inv.journal_id.FEE_sequence_id.next_by_id()
                elif inv.tipo_documento == 'ND':
                    sequence = inv.journal_id.ND_sequence_id.next_by_id()

            # Digital Supplier Invoice
            elif inv.move_type == 'in_invoice' and inv.partner_id.country_id and \
                inv.partner_id.country_id.code == 'CR' and inv.partner_id.identification_id and inv.partner_id.vat and not inv.xml_supplier_approval:
                if inv.tipo_documento == 'FEC':
                    sequence = inv.company_id.FEC_sequence_id.next_by_id()

            if not inv.tipo_documento or (inv.move_type in ('in_invoice', 'in_refund') and inv.tipo_documento in ("CCE", "CPCE", "RCE", "FE", "NC")):
                super(AccountInvoiceElectronic, inv).action_post()
                continue

            # tipo de identificación
            if not inv.company_id.identification_id:
                raise UserError('Seleccione el tipo de identificación del emisor en el perfil de la compañía')

            if inv.partner_id and inv.partner_id.vat:
                identificacion = re.sub('[^0-9]', '', inv.partner_id.vat)
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
                    raise UserError('La Cédula Física del receptor debe de tener 9 dígitos')
                elif id_code == '02' and len(identificacion) != 10:
                    raise UserError('La Cédula Jurídica del receptor debe de tener 10 dígitos')
                elif id_code == '03' and len(identificacion) not in (11, 12):
                    raise UserError('La identificación DIMEX del receptor debe de tener 11 o 12 dígitos')
                elif id_code == '04' and len(identificacion) != 10:
                    raise UserError('La identificación NITE del receptor debe de tener 10 dígitos')

            if inv.invoice_payment_term_id and not inv.invoice_payment_term_id.sale_conditions_id:
                raise UserError('No se pudo Crear la factura electrónica: \n Debe configurar condiciones de pago para %s' % (inv.invoice_payment_term_id.name))

            # Validate if invoice currency is the same as the company currency
            if currency.name != inv.company_id.currency_id.name and (not currency.rate_ids or not (len(currency.rate_ids) > 0)):
                raise UserError(_('No hay tipo de cambio registrado para la moneda %s' % (currency.name)))

            #Devolucion del IVA   
            # Inicializamos las variables que controlan los montos de cada impuesto
            inv.amount_total_iva_devuelto =  0.0

            for i in inv.invoice_line_ids:
                # Revisamos si aplica para la devolucion del IVA: Servicio de Salud Privado, Pago con medio electronico e IVA Reducido 4%
                if api_facturae.has_iva_devuelto(inv, i):
                    inv.amount_total_iva_devuelto += round(i.price_tax, 5)
                    #inv.amount_total = inv.amount_total - inv.amount_total_iva_devuelto   

            super(AccountInvoiceElectronic, inv).action_post()
            if not inv.number_electronic:
                # if journal doesn't have sucursal use default from company
                sucursal_id = inv.journal_id.sucursal
                if not sucursal_id:
                    sucursal_id = self.env.user.company_id.sucursal_MR

                # if journal doesn't have terminal use default from company
                terminal_id = inv.journal_id.terminal
                if not terminal_id:
                    sucursal_id = self.env.user.company_id.terminal_MR

                response_json = api_facturae.get_clave_hacienda(inv,
                                                            inv.tipo_documento,
                                                            sequence,
                                                            sucursal_id,
                                                            terminal_id)

                inv.number_electronic = response_json.get('clave')
                inv.sequence = response_json.get('consecutivo')
            
            inv.name = inv.sequence
            #inv.move_name = inv.sequence
            #inv.move_id.name = inv.sequence
            inv.state_tributacion = False

    
    @api.onchange('amount_total')
    def update_text_amount(self):
        for inv in self:
            inv.invoice_amount_text = extensions.text_converter.number_to_text_es(inv.amount_total)
    
    def _reverse_moves(self, default_values_list=None, cancel=False):
        ''' Reverse a recordset of account.move.
        If cancel parameter is true, the reconcilable or liquidity lines
        of each original move will be reconciled with its reverse's.
        :param default_values_list: A list of default values to consider per move.
                                    ('type' & 'reversed_entry_id' are computed in the method).
        :return:                    An account.move recordset, reverse of the current self.
        '''
        if not default_values_list:
            default_values_list = [{} for move in self]

        if cancel:
            lines = self.mapped('line_ids')
            # Avoid maximum recursion depth.
            if lines:
                lines.remove_move_reconcile()

        reverse_type_map = {
            'entry': 'entry',
            'out_invoice': 'out_refund',
            'out_refund': 'entry',
            'in_invoice': 'in_refund',
            'in_refund': 'entry',
            'out_receipt': 'entry',
            'in_receipt': 'entry',
        }

        move_vals_list = []
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'move_type': reverse_type_map[move.move_type],
                'reversed_entry_id': move.id,
            })
            move_vals_list.append(move.with_context(move_reverse_cancel=cancel)._reverse_move_vals(default_values, cancel=cancel))
        reverse_moves = self.env['account.move'].create(move_vals_list)
        for move, reverse_move in zip(self, reverse_moves.with_context(check_move_validity=False)):
            # Update amount_currency if the date has changed.
            if move.date != reverse_move.date:
                for line in reverse_move.line_ids:
                    if line.currency_id:
                        line._onchange_currency()
            reverse_move._recompute_dynamic_lines(recompute_all_taxes=False)
        reverse_moves._check_balanced()

        # Reconcile moves together to cancel the previous one.
        if cancel:
            reverse_moves.with_context(move_reverse_cancel=cancel).action_post()
            for move, reverse_move in zip(self, reverse_moves):
                lines = move.line_ids.filtered(
                    lambda x: (x.account_id.reconcile or x.account_id.internal_type == 'liquidity')
                              and not x.reconciled
                )
                for line in lines:
                    counterpart_lines = reverse_move.line_ids.filtered(
                        lambda x: x.account_id == line.account_id
                                  and x.currency_id == line.currency_id
                                  and not x.reconciled
                    )
                    (line + counterpart_lines).with_context(move_reverse_cancel=cancel).reconcile()

        return reverse_moves

    def create_partner_from_xml(self):

        if not self.partner_id and self.xml_supplier_approval:
            info = {}

            invoice_xml = etree.fromstring(base64.b64decode(self.xml_supplier_approval))
            namespaces = invoice_xml.nsmap
            inv_xmlns = namespaces.pop(None)
            namespaces['inv'] = inv_xmlns

            info['vat'] = invoice_xml.xpath("inv:Emisor/inv:Identificacion/inv:Numero", namespaces=namespaces)[0].text

            partner = self.env['res.partner'].search([('vat', '=', info['vat']), ('type', '=', 'contact')], limit=1)
            if len(partner) > 0:
                self.partner_id = partner.id
            else:
                info['name'] = invoice_xml.xpath("inv:Emisor/inv:Nombre", namespaces=namespaces)[0].text
                info['phone'] = invoice_xml.xpath("inv:Emisor/inv:Telefono/inv:NumTelefono", namespaces=namespaces)[0].text or False
                info['email'] = invoice_xml.xpath("inv:Emisor/inv:CorreoElectronico", namespaces=namespaces)[0].text or False
                info['lang'] = 'es_CR'

                # Se agrega manualmente la información ya que no se puede obtener del XML
                info['property_payment_term_id'] = 1
                info['payment_methods_id'] = 1
                info['property_product_pricelist'] = 1
                info['property_supplier_payment_term_id'] = 1

                # Ubicacion

                # País
                info['country_id'] = self.env['res.country'].search([('code', '=', 'CR')], limit=1).id

                # Provincia
                provincia = invoice_xml.xpath("inv:Emisor/inv:Ubicacion/inv:Provincia", namespaces=namespaces)[0].text
                state_id = self.env['res.country.state'].search([('code', '=', provincia)], limit=1).id
                info['state_id'] = state_id

                # Cantón
                canton = invoice_xml.xpath("inv:Emisor/inv:Ubicacion/inv:Canton", namespaces=namespaces)[0].text
                county_id = self.env['res.country.county'].search([('code', '=', canton), ('state_id', '=', state_id)], limit=1).id
                info['county_id'] = county_id

                # Distrito
                distrito = invoice_xml.xpath("inv:Emisor/inv:Ubicacion/inv:Distrito", namespaces=namespaces)[0].text
                district_id = self.env['res.country.district'].search([('code', '=', distrito), ('county_id', '=', county_id)], limit=1).id
                info['district_id'] = district_id


                actividad_economica = invoice_xml.xpath("inv:CodigoActividad", namespaces=namespaces)[0].text
                info['activity_id'] = self.env['economic.activity'].search([('code', '=', actividad_economica)], limit=1).id

                cliente = self.env['res.partner'].create(info)
                cliente.onchange_vat()
                self.partner_id = cliente.id