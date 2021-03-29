"""
from __future__ import print_function
import functools
import traceback
import sys

INDENT = 4*' '

def stacktrace(func):
    @functools.wraps(func)
    def wrapped(*args, **kwds):
        # Get all but last line returned by traceback.format_stack()
        # which is the line below.
        callstack = '\n'.join([INDENT+line.strip() for line in traceback.format_stack()][:-1])
        _logger.error('MAB - {}() called:'.format(func.__name__))
        _logger.error(callstack)
        return func(*args, **kwds)

    return wrapped
"""
import base64
import json
import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import odoo.addons.cr_electronic_invoice.models.api_facturae as api_facturae
from xml.sax.saxutils import escape
import datetime
import pytz
from threading import Lock
lock = Lock()

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    #@stacktrace
    @api.model
    def create(self, vals):
        return super(StockPicking, self).create(vals)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    payment_method_id = fields.Many2one(
        "payment.methods", string="Payment Methods", required=False, )

class PosConfig(models.Model):
    _inherit = 'pos.config'
    sucursal = fields.Integer(string="Branch", required=False, default="1")
    terminal = fields.Integer(string="Terminal", required=False, default="1")
    FE_sequence_id = fields.Many2one("ir.sequence",
                                     string="Electronic Invoice Sequence",
                                     required=False)
    NC_sequence_id = fields.Many2one("ir.sequence",
                                     oldname='return_sequence_id',
                                     string="Electronic Credit Note Sequence",
                                     required=False)
    TE_sequence_id = fields.Many2one("ir.sequence",
                                     string="Electronic Ticket Sequence",
                                     required=False)
class PosOrder(models.Model):
    _name = "pos.order"
    _inherit = ["pos.order", "mail.thread"]

    @api.multi
    def action_invoice_sent(self):
        email_template = self.env.ref(
            'cr_electronic_invoice_pos.email_template_pos_invoice', False)
        attachment = self.env['ir.attachment'].search(
            [('res_model', '=', 'pos.order'), ('res_id', '=', self.id),
             ('res_field', '=', 'xml_comprobante')], limit=1)
        attachment.name = self.fname_xml_comprobante
        attachment.datas_fname = self.fname_xml_comprobante
        attachment_resp = self.env['ir.attachment'].search(
            [('res_model', '=', 'pos.order'), ('res_id', '=', self.id),
             ('res_field', '=', 'xml_respuesta_tributacion')], limit=1)
        attachment_resp.name = self.fname_xml_respuesta_tributacion
        attachment_resp.datas_fname = self.fname_xml_respuesta_tributacion
        email_template.attachment_ids = [
            (6, 0, [attachment.id, attachment_resp.id])]
        email_template.with_context(type='binary', default_type='binary').send_mail(self.id,
             raise_exception=False,
             force_send=True)  # default_type='binary'
        email_template.attachment_ids = [(5)]

    @api.model
    def sequence_number_sync(self, vals):
        tipo_documento = vals.get('tipo_documento', False)
        sequence = vals.get('sequence', False)
        sequence = int(sequence) if sequence else False
        if vals.get('session_id') and sequence:
            session = self.env['pos.session'].sudo().browse(vals['session_id'])
            if tipo_documento == 'FE' and sequence >= session.config_id.FE_sequence_id.number_next_actual:
                    session.config_id.FE_sequence_id.number_next_actual = sequence + 1
            elif tipo_documento == 'TE' and sequence >= session.config_id.TE_sequence_id.number_next_actual:
                    session.config_id.TE_sequence_id.number_next_actual = sequence + 1

    @api.model
    def _order_fields(self, ui_order):
        vals = super(PosOrder, self)._order_fields(ui_order)
        vals['tipo_documento'] = ui_order.get('tipo_documento')
        vals['sequence'] = ui_order.get('sequence')
        vals['number_electronic'] = ui_order.get('number_electronic')
        return vals

    @api.model
    def create(self, vals):
        number_electronic = vals.get('number_electronic', False)
        if vals.get('pos_order_id', False):
            vals['number_electronic'] = '/'
        elif number_electronic:
            self.sequence_number_sync(vals)
            if self.env['pos.order'].search([('number_electronic', 'like', number_electronic[21:41])]):
                vals['number_electronic'] = self.env['ir.sequence'].next_by_code(
                    'pos.order.recovery')
        order = super(PosOrder, self).create(vals)
        return order

    number_electronic = fields.Char(
        string="Electronic Number", required=False, copy=False, index=True)
    date_issuance = fields.Char(
        string="Issue date", required=False, copy=False)
    state_tributacion = fields.Selection([('aceptado', 'Accepted'),
                                          ('rechazado', 'Rejected'),
                                          ('rejected', 'Rejected2'),
                                          ('no_encontrado', 'Not found'),
                                          ('no_aplica', 'No apply'),
                                          ('recibido', 'Received'),
                                          ('firma_invalida', 'Invalid Sign'),
                                          ('error', 'Error'),
                                          ('procesando', 'Procesing')], 'FE State', copy=False)

    reference_code_id = fields.Many2one(
        "reference.code", string="Reference code", required=False)
    pos_order_id = fields.Many2one(
        "pos.order", string="Reference document", required=False, copy=False)
    xml_respuesta_tributacion = fields.Binary(
        string="Taxation XML response", required=False, copy=False, attachment=True)
    fname_xml_respuesta_tributacion = fields.Char(
        string="Taxation XML response filename", required=False, copy=False)
    xml_comprobante = fields.Binary(
        string="XML receipt", required=False, copy=False, attachment=True)
    fname_xml_comprobante = fields.Char(
        string="XML receipt filename", required=False, copy=False)
    state_email = fields.Selection([('no_email', 'Without email'), (
        'sent', 'Sent'), ('fe_error', 'Error FE')], 'Email state', copy=False)
    error_count = fields.Integer(
        string="Amount of errors", required=False, default="0")
    tipo_documento = fields.Selection(
        oldname='doc_type',
        selection=[('FE', 'Electronic Invoice'),
                   ('TE', 'Electronic Ticket'),
                   ('NC', 'Electronic Credit Note')],
        string="Document Type",
        required=False, default='FE',
        help='Show document type in concordance with '
             'Ministerio de Hacienda classification')

    sequence = fields.Char(string='Consecutive', readonly=True, )

    economic_activity_id = fields.Many2one("economic.activity", string="Economic Activity", required=False, )

    _sql_constraints = [
        ('number_electronic_uniq', 'unique (number_electronic)',
         "La clave de comprobante debe ser única"),
    ]

    @api.multi
    def action_pos_order_paid(self):
        for order in self:
            if not order.pos_order_id:
                continue
            if order.tipo_documento == 'FE':
                order.number_electronic = order.session_id.config_id.FE_sequence_id._next()
            elif order.tipo_documento == 'TE':
                order.number_electronic = order.session_id.config_id.TE_sequence_id._next()
            else:
                order.tipo_documento = 'NC'
                order.number_electronic = order.session_id.config_id.NC_sequence_id._next()
            order.sequence = order.number_electronic[21:41]
        return super(PosOrder, self).action_pos_order_paid()

    @api.multi
    def refund(self):
        """Create a copy of order  for refund order"""
        PosOrder = self.env['pos.order']
        reference_code_id = self.env['reference.code'].search(
            [('code', '=', '01')], limit=1)
        current_session = self.env['pos.session'].search([('state', '!=', 'closed'),
                                                          ('user_id', '=',
                                                           self.env.uid),
                                                          ('name', 'not like',
                                                           'RESCUE')
                                                          ],
                                                         limit=1)
        if not current_session:
            raise UserError(
                _('To return product(s), you need to open a session that will be used to register the refund.'))
        for order in self:
            if order.tipo_documento in ('FE', 'TE'):
                tipo_documento = 'NC'
                referenced_order = order.id
            elif order.partner_id and order.partner_id.vat:
                tipo_documento = 'FE'
                referenced_order = order.pos_order_id and order.pos_order_id.id or order.id
            else:
                tipo_documento = 'TE'
                referenced_order = order.pos_order_id and order.pos_order_id.id or order.id

            clone = order.copy({
                'name': order.name + (tipo_documento == 'NC' and _(' REFUND') or ''),
                'session_id': current_session.id,
                'date_order': fields.Datetime.now(),
                'pos_order_id': referenced_order,
                'reference_code_id': reference_code_id.id,
                'tipo_documento': tipo_documento,
                'pos_reference': order.pos_reference,
                'lines': False,
                'amount_tax': -order.amount_tax,
                'amount_total': -order.amount_total,
                'amount_paid': 0,
            })
            for line in order.lines:
                clone_line = line.copy({
                    'name': line.name + _(' REFUND'),
                    'order_id': clone.id,
                    'qty': -line.qty,
                    'price_subtotal': -line.price_subtotal,
                    'price_subtotal_incl': -line.price_subtotal_incl,
                })
            PosOrder += clone
        return {
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id': PosOrder.ids[0],
            'view_id': False,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.model
    def _consultahacienda_pos(self, max_orders=10):  # cron
        pos_orders = self.env['pos.order'].search([('state', 'in', ('paid', 'done', 'invoiced')),
                                                   ('number_electronic', '!=', False),
                                                   ('state_tributacion', 'in', ('recibido', 'procesando'))],
                                                  limit=max_orders)
        total_orders = len(pos_orders)
        current_order = 0
        _logger.info(
            'MAB - Consulta Hacienda - POS Orders to check: %s', total_orders)
        for doc in pos_orders:
            current_order += 1
            _logger.error(
                'MAB - Consulta Hacienda - POS Order %s / %s number: %s', current_order, total_orders, doc.name)

            token_m_h = api_facturae.get_token_hacienda(
                doc, doc.company_id.frm_ws_ambiente)
            if doc.number_electronic and len(doc.number_electronic) == 50:
                response_json = api_facturae.consulta_clave(
                    doc.number_electronic, token_m_h, doc.company_id.frm_ws_ambiente)

                status = response_json['status']
                if status == 200:
                    estado_m_h = response_json.get('ind-estado')
                elif status == 400:
                    estado_m_h = response_json.get('ind-estado')
                    _logger.error(
                        'MAB - Error: %s Documento:%s no encontrado en Hacienda', estado_m_h, doc.number_electronic)
                else:
                    _logger.error(
                        'MAB - Error inesperado en Consulta Hacienda - Abortando')
                    return
                if estado_m_h == 'aceptado':
                    doc.state_tributacion = estado_m_h
                    doc.fname_xml_respuesta_tributacion = 'AHC_' + doc.number_electronic + '.xml'
                    doc.xml_respuesta_tributacion = response_json.get(
                        'respuesta-xml')
                    if doc.partner_id and doc.partner_id.email:  # and not doc.partner_id.opt_out:
                        try:
                            email_template = self.env.ref(
                                'cr_electronic_invoice_pos.email_template_pos_invoice', False)
                            attachment = self.env['ir.attachment'].search(
                                [('res_model', '=', 'pos.order'), ('res_id', '=', doc.id),
                                ('res_field', '=', 'xml_comprobante')], limit=1)
                            attachment.name = doc.fname_xml_comprobante
                            attachment.datas_fname = doc.fname_xml_comprobante

                            attachment_resp = self.env['ir.attachment'].search(
                                [('res_model', '=', 'pos.order'), ('res_id', '=', doc.id),
                                ('res_field', '=', 'xml_respuesta_tributacion')], limit=1)
                            attachment_resp.name = doc.fname_xml_respuesta_tributacion
                            attachment_resp.datas_fname = doc.fname_xml_respuesta_tributacion

                            email_template.attachment_ids = [
                                (6, 0, [attachment.id, attachment_resp.id])]
                            email_template.with_context(type='binary', default_type='binary').send_mail(doc.id,
                                                                                                        raise_exception=False,
                                                                                                        force_send=True)  # default_type='binary'
                            email_template.attachment_ids = [(5)]
                            doc.state_email = 'sent'
                        except:
                            doc.state_email = 'fe_error'
                    else:
                        doc.state_email = 'no_email'
                        _logger.info('MAB - Email no enviado - Cliente no definido')

                elif estado_m_h in ('firma_invalida'):
                    if doc.error_count > 10:
                        doc.state_tributacion = estado_m_h
                        doc.fname_xml_respuesta_tributacion = 'AHC_' + doc.number_electronic + '.xml'
                        doc.xml_respuesta_tributacion = response_json.get(
                            'respuesta-xml')
                        doc.state_email = 'fe_error'
                        _logger.error('MAB - Email no enviado - Factura rechazada')
                    else:
                        doc.error_count += 1
                        doc.state_tributacion = 'procesando'
                elif estado_m_h in ('rechazado', 'rejected'):
                    doc.state_tributacion = estado_m_h
                    doc.fname_xml_respuesta_tributacion = 'AHC_' + doc.number_electronic + '.xml'
                    doc.xml_respuesta_tributacion = response_json.get(
                        'respuesta-xml')
                    doc.state_email = 'fe_error'
                    _logger.error('MAB - Email no enviado - Factura rechazada')
                elif estado_m_h == 'error':
                    doc.state_tributacion = estado_m_h
                    doc.state_email = 'fe_error'
                else:
                    if doc.error_count > 10:
                        doc.state_tributacion = 'error'
                    elif doc.error_count < 4:
                        doc.error_count += 1
                        doc.state_tributacion = 'procesando'
                    else:
                        doc.error_count += 1
                        doc.state_tributacion = ''
                    _logger.error(
                        'MAB - Consulta Hacienda - POS Order %s in state "%s" - Error count: %s', doc.number_electronic, estado_m_h, doc.error_count)
            else:
                doc.state_tributacion = 'error'
                _logger.error(
                    'MAB - POS Order %s - x Number Electronic: %s formato incorrecto', doc.name, doc.number_electronic)
        _logger.info('MAB - Consulta Hacienda POS - Finalizad Exitosamente')

    @api.model
    def _reenviacorreos_pos(self, max_orders=1):  # cron
        pos_orders = self.env['pos.order'].search([('state', 'in', ('paid', 'done', 'invoiced')),
                                                   ('date_order', '>=',
                                                    '2018-09-01'),
                                                   ('number_electronic',
                                                    '!=', False),
                                                   ('state_email', '=', False),
                                                   ('state_tributacion', '=', 'aceptado')],
                                                  limit=max_orders
                                                  )
        total_orders = len(pos_orders)
        current_order = 0
        _logger.info(
            'MAB - Reenvia Correos- POS Orders to send: %s', total_orders)
        for doc in pos_orders:
            current_order += 1
            _logger.info('MAB - Reenvia Correos- POS Order %s - %s / %s',
                          doc.name, current_order, total_orders)
            if doc.partner_id.email and not doc.partner_id.opt_out and doc.state_tributacion == 'aceptado':
                comprobante = self.env['ir.attachment'].search(
                    [('res_model', '=', 'pos.order'), ('res_id', '=', doc.id),
                     ('res_field', '=', 'xml_comprobante')], limit=1)
                if not comprobante:
                    _logger.error('MAB - Email no enviado - Tiquete sin xml')
                    continue
                try:
                    comprobante.name = doc.fname_xml_comprobante
                except:
                    comprobante.name = 'FE_'+doc.number_electronic+'.xml'
                comprobante.datas_fname = comprobante.name
                respuesta = self.env['ir.attachment'].search(
                    [('res_model', '=', 'pos.order'), ('res_id', '=', doc.id),
                     ('res_field', '=', 'xml_respuesta_tributacion')], limit=1)
                respuesta.name = doc.fname_xml_respuesta_tributacion
                respuesta.datas_fname = doc.fname_xml_respuesta_tributacion
                email_template = self.env.ref(
                    'cr_electronic_invoice_pos.email_template_pos_invoice', False)
                email_template.attachment_ids = [
                    (6, 0, [comprobante.id, respuesta.id])]  # [(4, attachment.id)]
                email_template.with_context(type='binary', default_type='binary').send_mail(doc.id,
                                                                                            raise_exception=False,
                                                                                            force_send=True)  # default_type='binary'
                doc.state_email = 'sent'
            elif doc.state_tributacion in ('rechazado', 'rejected'):
                doc.state_email = 'fe_error'
                _logger.error('MAB - Email no enviado - factura rechazada')
            else:
                doc.state_email = 'no_email'
                _logger.info('MAB - Email no enviado - Cuenta no definida')
        _logger.info('MAB - Reenvia Correos - Finalizado')

    @api.model
    def _validahacienda_pos(self, max_orders=10, no_partner=True):  # cron
        pos_orders = self.env['pos.order'].search([('state', 'in', ('paid', 'done', 'invoiced')),
                                                   '|', (no_partner, '=', True), 
                                                        '&', ('partner_id', '!=', False), ('partner_id.vat', '!=', False),
                                                   ('tipo_documento', 'in', ('TE','FE','NC')),
                                                   ('state_tributacion', '=', False)],
                                                  order="date_order",
                                                  limit=max_orders)
        total_orders = len(pos_orders)
        current_order = 0
        _logger.info(
            'MAB - Valida Hacienda - POS Orders to check: %s', total_orders)
        for doc in pos_orders:
            current_order += 1
            _logger.info('MAB - Valida Hacienda - POS Order: "%s"  -  %s / %s',
                          doc.number_electronic, current_order, total_orders)
            docName = doc.number_electronic
            if not docName or not docName.isdigit() or doc.company_id.frm_ws_ambiente == 'disabled':
                _logger.error(
                    'MAB - Valida Hacienda - skipped Invoice %s', docName)
                doc.state_tributacion = 'no_aplica'
                continue
            now_utc = datetime.datetime.now(pytz.timezone('UTC'))
            now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
            dia = docName[3:5]#'%02d' % now_cr.day,
            mes = docName[5:7]#'%02d' % now_cr.month,
            anno = docName[7:9]#str(now_cr.year)[2:4],
            date_cr = now_cr.strftime("20"+anno+"-"+mes+"-"+dia+"T%H:%M:%S-06:00")
            doc.name = doc.number_electronic[21:41]
            if not doc.xml_comprobante:
                numero_documento_referencia = False
                fecha_emision_referencia = False
                codigo_referencia = False
                razon_referencia = False
                invoice_comments = False
                tipo_documento_referencia = False
                if not doc.pos_order_id:   #.number_electronic:
                    if doc.amount_total < 0:
                        doc.state_tributacion = 'error'
                        _logger.error(
                            'MAB - Error documento %s tiene monto negativo pero no tiene documento referencia', doc.number_electronic)
                        continue
                else:
                    if doc.amount_total >= 0:
                        _logger.error(
                            'MAB - Valida Hacienda - skipped Invoice %s', docName)
                        doc.state_tributacion = 'no_aplica'
                        continue
                        doc.tipo_documento = 'ND'
                        razon_referencia = 'Reemplaza Factura'
                    else:
                        doc.tipo_documento = 'NC'
                        numero_documento_referencia = doc.pos_order_id.number_electronic
                        codigo_referencia = doc.reference_code_id.code
                        razon_referencia = 'nota credito'
                    tipo_documento_referencia = doc.pos_order_id.number_electronic[29:31]
                    numero_documento_referencia = doc.pos_order_id.number_electronic
                    fecha_emision_referencia = doc.pos_order_id.date_issuance
                    codigo_referencia = doc.reference_code_id.code
                sale_conditions = '01' #Contado !!   doc.sale_conditions_id.sequence,
                currency_rate = 1  # 1 / doc.currency_id.rate
                # Generamos las líneas de la factura
                lines = dict()
                otros_cargos = dict()
                otros_cargos_id = 0
                line_number = 0
                total_servicio_gravado = 0.0
                total_servicio_exento = 0.0
                total_servicio_exonerado = 0.0
                total_mercaderia_gravado = 0.0
                total_mercaderia_exento = 0.0
                total_mercaderia_exonerado = 0.0
                total_descuento = 0.0
                total_impuestos = 0.0
                base_subtotal = 0.0
                total_otros_cargos = 0.0
                total_iva_devuelto = 0.0
                _no_CABYS_code = False
                for line in doc.lines:
                    line_number += 1
                    price = line.price_unit * (1 - line.discount / 100.0)
                    qty = abs(line.qty)
                    if not qty:
                        continue
                    fpos = line.order_id.fiscal_position_id
                    tax_ids = fpos.map_tax(
                        line.tax_ids, line.product_id, line.order_id.partner_id) if fpos else line.tax_ids
                    line_taxes = tax_ids.compute_all(
                        price, line.order_id.pricelist_id.currency_id, 1, product=line.product_id, partner=line.order_id.partner_id)
                    if line.discount != 100:
                        price_unit = round(
                            line_taxes['total_excluded'] / (1 - line.discount / 100.0), 5)
                    else:
                        price_unit = 0
                    base_line = abs(round(price_unit * qty, 5))
                    subtotal_line = abs(
                        round(price_unit * qty * (1 - line.discount / 100.0), 5))
                    dline = {
                        "cantidad": qty,
                        "unidadMedida": line.product_id and line.product_id.uom_id.code or 'Sp',
                        "detalle": escape(line.product_id.name[:159]),
                        "precioUnitario": price_unit,
                        "montoTotal": base_line,
                        "subtotal": subtotal_line,
                    }

                    if line.product_id.cabys_code:
                        dline["codigoCabys"] = line.product_id.cabys_code
                    elif line.product_id.categ_id and line.product_id.categ_id.cabys_code:
                        dline["codigoCabys"] = line.product_id.categ_id.cabys_code
                    else:
                        _no_CABYS_code = 'Aviso!.\nLinea sin código CABYS: %s' % line.product_id.name
                        continue

                    if line.discount:
                        descuento = abs(round(base_line - subtotal_line, 5))
                        total_descuento += descuento
                        dline["montoDescuento"] = descuento
                        dline["naturalezaDescuento"] = 'Descuento Comercial'

                    taxes = dict()
                    _line_tax = 0.0
                    if tax_ids:
                        tax_index = 0
                        taxes_lookup = {}
                        for i in tax_ids:
                            taxes_lookup[i.id] = {
                                'tax_code': i.tax_code, 
                                'tarifa': i.amount,
                                'iva_tax_desc': i.iva_tax_desc,
                                'iva_tax_code': i.iva_tax_code}
                        for i in line_taxes['taxes']:
                            if taxes_lookup[i['id']]['tax_code'] == 'service':
                                total_otros_cargos += round(abs(i['amount'] * qty), 5)
                            elif taxes_lookup[i['id']]['tax_code'] != '00':
                                tax_index += 1
                                tax_amount = round(abs(i['amount'] * qty), 5)
                                _line_tax += tax_amount
                                taxes[tax_index] = {
                                    'codigo': taxes_lookup[i['id']]['tax_code'],
                                    'tarifa': taxes_lookup[i['id']]['tarifa'],
                                    'monto': tax_amount,
                                    'iva_tax_desc': taxes_lookup[i['id']]['iva_tax_desc'],
                                    'iva_tax_code': taxes_lookup[i['id']]['iva_tax_code'],
                                }
                    dline["impuesto"] = taxes
                    dline["impuestoNeto"] = _line_tax

                    # Si no hay product_id se asume como mercaderia
                    if line.product_id and line.product_id.type == 'service':
                        if taxes:
                            total_servicio_gravado += base_line
                            total_impuestos += _line_tax
                        else:
                            total_servicio_exento += base_line
                    else:
                        if taxes:
                            total_mercaderia_gravado += base_line
                            total_impuestos += _line_tax
                        else:
                            total_mercaderia_exento += base_line
                    base_subtotal += subtotal_line
                    dline["montoTotalLinea"] = round(subtotal_line + _line_tax, 5)
                    lines[line_number] = dline

                if _no_CABYS_code and doc.tipo_documento != 'NC':  # CAByS is not required for financial NCs
                    doc.message_post(
                        subject='Error',
                        body=_no_CABYS_code)
                    continue
                if total_otros_cargos:
                    total_otros_cargos = round( total_otros_cargos, 5)
                    otros_cargos_id = 1
                    otros_cargos[otros_cargos_id]= {
                        'TipoDocumento': '06',
                        'Detalle': escape('Servicio salon 10%'),
                        'MontoCargo': total_otros_cargos
                    }
                doc.date_issuance = date_cr
                invoice_comments = ''
                doc.economic_activity_id = doc.company_id.activity_id
                xml_string_builder = api_facturae.gen_xml_v43(
                    doc, sale_conditions, round(total_servicio_gravado, 5),
                    round(total_servicio_exento, 5), total_servicio_exonerado,
                    round(total_mercaderia_gravado, 5), round(total_mercaderia_exento, 5),
                    total_mercaderia_exonerado, total_otros_cargos, total_iva_devuelto, base_subtotal,
                    total_impuestos, total_descuento, json.dumps(lines, ensure_ascii=False),
                    otros_cargos, currency_rate, invoice_comments,
                    tipo_documento_referencia, numero_documento_referencia,
                    fecha_emision_referencia, codigo_referencia, razon_referencia)
                xml_to_sign = str(xml_string_builder)
                xml_firmado = api_facturae.sign_xml(
                    doc.company_id.signature, doc.company_id.frm_pin, xml_to_sign)
                doc.fname_xml_comprobante = doc.tipo_documento + '_' + docName + '.xml'
                doc.xml_comprobante = base64.encodestring(xml_firmado)
                _logger.info('MAB - SIGNED XML:%s', doc.fname_xml_comprobante)

            else:
                xml_firmado = doc.xml_comprobante
            # get token
            token_m_h = api_facturae.get_token_hacienda(
                doc, doc.company_id.frm_ws_ambiente)
            response_json = api_facturae.send_xml_fe(doc, token_m_h, date_cr,
                                                     xml_firmado, doc.company_id.frm_ws_ambiente)
            response_status = response_json.get('status')
            response_text = response_json.get('text')
            if 200 <= response_status <= 299:
                doc.state_tributacion = 'procesando'
            else:
                if response_text.find('ya fue recibido anteriormente') != -1:
                    doc.state_tributacion = 'procesando'
                    doc.message_post(
                        subject='Error', body='Ya recibido anteriormente, se pasa a consultar')
                elif doc.error_count > 10:
                    doc.message_post(subject='Error', body=response_text)
                    doc.state_tributacion = 'error'
                    _logger.error('MAB - Invoice: %s  Status: %s Error sending XML: %s', doc.name,
                                  response_status, response_text)
                else:
                    doc.error_count += 1
                    doc.state_tributacion = 'procesando'
                    doc.message_post(subject='Error', body=response_text)
                    _logger.error('MAB - Invoice: %s  Status: %s Error sending XML: %s', doc.name,
                                  response_status, response_text)
        _logger.info('MAB 014 - Valida Hacienda POS- Finalizado Exitosamente')
