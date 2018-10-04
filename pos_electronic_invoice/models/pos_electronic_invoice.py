# -*- coding: utf-8 -*-

import json
import requests
import logging
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import datetime
import pytz
import base64
import xml.etree.ElementTree as ET
from . import functions

_logger = logging.getLogger(__name__)


class OrderElectronic(models.Model):
    _inherit = 'pos.order'

    ticket_hacienda_number = fields.Char(
        'Clave',
        copy=False,
        oldname='ticket_hacienda',
    )

    state_tributacion = fields.Selection(
        [('aceptado', 'Aceptado'), ('rechazado', 'Rechazado'), ('recibido', 'Recibido'),
         ('error', 'Error'), ('procesando', 'Procesando')], 'Estado FE',
        copy=False)

    xml_respuesta_tributacion = fields.Binary(string="Respuesta Tributación XML", required=False, copy=False,
                                              attachment=True)
    fname_xml_respuesta_tributacion = fields.Char(string="Nombre de archivo XML Respuesta Tributación", required=False,
                                                  copy=False)
    xml_comprobante = fields.Binary(string="Comprobante XML", required=False, copy=False, attachment=True)
    fname_xml_comprobante = fields.Char(string="Nombre de archivo Comprobante XML", required=False, copy=False,
                                        attachment=True)

    consecutivo_number = fields.Char(
        'Consecutivo',
        copy=False,
        oldname='consecutivo',
    )

    @api.model
    def _order_fields(self, ui_order):
        res = super(OrderElectronic, self)._order_fields(ui_order)
        res.update({
            'ticket_hacienda_number': ui_order.get(
                'ticket_hacienda', ''),
            'consecutivo_number': ui_order.get(
                'consecutivo', ''),
        })
        return res

    @api.model
    def _process_order(self, order):
        pos_order = super(OrderElectronic, self)._process_order(order)
        if pos_order.company_id.frm_ws_ambiente != 'disabled':

            url = pos_order.company_id.frm_callback_url
            payload = {}
            headers = {}
            now_utc = datetime.datetime.now(pytz.timezone('UTC'))
            now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
            date_cr = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")
            medio_pago = '01'
            tipo_documento = 'TE'
            currency_rate = 1
            lines = '{'
            base_total = 0.0
            numero = 0
            indextax = 0
            total_servicio_gravado = 0.0
            total_servicio_exento = 0.0
            total_mercaderia_gravado = 0.0
            total_mercaderia_exento = 0.0

            clave = str(pos_order.ticket_hacienda_number)
            consecutivo = pos_order.consecutivo_number

            for line in pos_order.lines:
                impuestos_acumulados = 0.0
                numero += 1
                base_total += line.price_unit * line.qty
                impuestos = '{'
                for i in line.tax_ids:
                    indextax += 1
                    if i.tax_code != '00':
                        monto_impuesto = round(i.amount / 100 * line.price_subtotal, 2)
                        impuestos = (impuestos + '"' + str(indextax) + '":' + '{"codigo": "'
                                     + str(i.tax_code or '01') + '",' + '"tarifa": "' + str(i.amount) + '",' +
                                     '"monto": "' + str(monto_impuesto))
                        impuestos_acumulados += round(i.amount / 100 * line.price_subtotal, 2)
                        impuestos = impuestos + '"},'
                impuestos = impuestos[:-1] + '}'
                indextax = 0
                if line.product_id:
                    if line.product_id.type == 'service':
                        if impuestos_acumulados != 0.0:
                            total_servicio_gravado += line.qty * line.price_unit
                        else:
                            total_servicio_exento += line.qty * line.price_unit
                    else:
                        if impuestos_acumulados != 0.0:
                            total_mercaderia_gravado += line.qty * line.price_unit
                        else:
                            total_mercaderia_exento += line.qty * line.price_unit
                else:  # se asume que si no tiene producto setrata como un type product
                    if impuestos_acumulados != 0.0:
                        total_mercaderia_gravado += line.qty * line.price_unit
                    else:
                        total_mercaderia_exento += line.qty * line.price_unit
                unidad_medida = line.product_id.commercial_measurement or 'Sp'
                total = line.qty * line.price_unit
                total_linea = line.price_subtotal + impuestos_acumulados
                descuento = (round(line.qty * line.price_unit, 2)
                             - round(line.price_subtotal, 2)) or 0
                natu_descuento = ''
                _logger.info(impuestos)
                line_obj = ('{' +
                            '"cantidad": "' + str(int(line.qty)) + '",' +
                            '"unidadMedida": "' + unidad_medida + '",' +
                            '"detalle": "' + line.product_id.display_name + '",' +
                            '"precioUnitario": "' + str(line.price_unit) + '",' +
                            '"montoTotal": "' + str(total) + '",' +
                            '"subtotal": "' + str(line.price_subtotal) + '",')
                if descuento != 0:
                    line_obj = (line_obj + '"montoDescuento": "' + str(descuento) + '",' +
                                '"naturalezaDescuento": "' + natu_descuento + '",')
                line_obj = (line_obj + '"impuesto": ' + str(impuestos) + ',' +
                            '"montoTotalLinea": "' + str(total_linea) + '"' +
                            '}'
                            )

                lines = lines + '"' + str(numero) + '":' + line_obj + ","
            lines = lines[:-1] + "}"
            amount_untaxed = pos_order.amount_total - pos_order.amount_tax
            payload = {}
            # Generar FE payload
            payload['w'] = 'genXML'
            if tipo_documento == 'TE':
                payload['r'] = 'gen_xml_te'
            payload['clave'] = clave
            payload['consecutivo'] = consecutivo
            payload['fecha_emision'] = date_cr
            payload['emisor_nombre'] = pos_order.company_id.name
            payload['emisor_tipo_indetif'] = pos_order.company_id.identification_id.code
            payload['emisor_num_identif'] = pos_order.company_id.vat
            payload['nombre_comercial'] = pos_order.company_id.commercial_name or ''
            payload['emisor_provincia'] = pos_order.company_id.state_id.code
            payload['emisor_canton'] = pos_order.company_id.county_id.code
            payload['emisor_distrito'] = pos_order.company_id.district_id.code
            payload['emisor_barrio'] = pos_order.company_id.neighborhood_id.code
            payload['emisor_otras_senas'] = pos_order.company_id.street
            payload['emisor_cod_pais_tel'] = pos_order.company_id.phone_code
            payload['emisor_tel'] = pos_order.company_id.phone
            payload['emisor_email'] = pos_order.company_id.email
            payload['omitir_receptor'] = 'true'
            payload['condicion_venta'] = '01'
            payload['plazo_credito'] = ''
            payload['medio_pago'] = medio_pago
            payload['cod_moneda'] = 'CRC'
            payload['tipo_cambio'] = 1
            payload['total_serv_gravados'] = total_servicio_gravado
            payload['total_serv_exentos'] = total_servicio_exento
            payload['total_merc_gravada'] = total_mercaderia_gravado
            payload['total_merc_exenta'] = total_mercaderia_exento
            payload['total_gravados'] = total_servicio_gravado + total_mercaderia_gravado
            payload['total_exentos'] = total_servicio_exento + total_mercaderia_exento
            payload['total_ventas'] = total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento
            payload['total_descuentos'] = round(base_total, 2) - round(amount_untaxed, 2)
            payload['total_ventas_neta'] = (total_servicio_gravado + total_mercaderia_gravado
                                            + total_servicio_exento + total_mercaderia_exento) \
                                           - (base_total - amount_untaxed)
            payload['total_impuestos'] = pos_order.amount_tax
            payload['total_comprobante'] = pos_order.amount_total
            payload['otros'] = ''
            payload['detalles'] = lines

            response = requests.request("POST", url, data=payload, headers=headers)
            response_json = json.loads(response._content)
            _logger.info('XML Sin Firmar')

            # firmar Comprobante
            payload = {}
            payload['w'] = 'signXML'
            payload['r'] = 'signFE'
            payload['p12Url'] = pos_order.company_id.frm_apicr_signaturecode
            payload['inXml'] = response_json.get('resp').get('xml')
            payload['pinP12'] = pos_order.company_id.frm_pin
            payload['tipodoc'] = tipo_documento

            response = requests.request("POST", url, data=payload, headers=headers)
            response_json = json.loads(response._content)
            xml_firmado = response_json.get('resp').get('xmlFirmado')
            _logger.info('Firmado XML')

            if pos_order.company_id.frm_ws_ambiente == 'stag':
                env = 'api-stag'
            else:
                env = 'api-prod'
            # get token
            payload = {}
            payload['w'] = 'token'
            payload['r'] = 'gettoken'
            payload['grant_type'] = 'password'
            payload['client_id'] = env
            payload['username'] = pos_order.company_id.frm_ws_identificador
            payload['password'] = pos_order.company_id.frm_ws_password

            response = requests.request("POST", url, data=payload, headers=headers)
            response_json = json.loads(response._content)
            _logger.info('Token MH')
            token_m_h = response_json.get('resp').get('access_token')

            payload = {}
            payload['w'] = 'send'
            payload['r'] = 'json'
            payload['token'] = token_m_h
            payload['clave'] = pos_order.ticket_hacienda_number
            payload['fecha'] = date_cr
            payload['emi_tipoIdentificacion'] = pos_order.company_id.identification_id.code
            payload['emi_numeroIdentificacion'] = pos_order.company_id.vat
            payload['recp_tipoIdentificacion'] = ''
            payload['recp_numeroIdentificacion'] = ''
            payload['comprobanteXml'] = xml_firmado
            payload['client_id'] = env

            response = requests.request("POST", url, data=payload, headers=headers)
            response_json = json.loads(response._content)

            if response_json.get('resp').get('Status') == 202:
                payload = {}
                payload['w'] = 'consultar'
                payload['r'] = 'consultarCom'
                payload['client_id'] = env
                payload['token'] = token_m_h
                payload['clave'] = pos_order.ticket_hacienda_number
                response = requests.request("POST", url, data=payload, headers=headers)
                response_json = json.loads(response._content)
                estado_m_h = response_json.get('resp').get('ind-estado')

                _logger.error('MAB - MH response:%s', response_json)

                if estado_m_h == 'aceptado':
                    pos_order.state_tributacion = estado_m_h
                    pos_order.fname_xml_respuesta_tributacion = 'respuesta_' + pos_order.ticket_hacienda_number + '.xml'
                    pos_order.xml_respuesta_tributacion = response_json.get('resp').get('respuesta-xml')
                    pos_order.fname_xml_comprobante = 'comprobante_' + pos_order.ticket_hacienda_number + '.xml'
                    pos_order.xml_comprobante = xml_firmado
                elif estado_m_h == 'recibido':
                    pos_order.state_tributacion = estado_m_h;
                    pos_order.fname_xml_comprobante = 'comprobante_' + pos_order.ticket_hacienda_number + '.xml'
                    pos_order.xml_comprobante = xml_firmado
                elif estado_m_h == 'procesando':
                    pos_order.state_tributacion = estado_m_h;
                    pos_order.fname_xml_comprobante = 'comprobante_' + pos_order.ticket_hacienda_number + '.xml'
                    pos_order.xml_comprobante = xml_firmado
                elif estado_m_h == 'rechazado':
                    pos_order.state_tributacion = estado_m_h;
                    pos_order.fname_xml_comprobante = 'comprobante_' + pos_order.ticket_hacienda_number + '.xml'
                    pos_order.xml_comprobante = xml_firmado
                    pos_order.fname_xml_respuesta_tributacion = 'respuesta_' + pos_order.ticket_hacienda_number + '.xml'
                    pos_order.xml_respuesta_tributacion = response_json.get('resp').get('respuesta-xml')
                elif estado_m_h == 'error':
                    pos_order.state_tributacion = estado_m_h
                    pos_order.fname_xml_comprobante = 'comprobante_' + pos_order.ticket_hacienda_number + '.xml'
                    pos_order.xml_comprobante = xml_firmado
                else:
                    raise UserError('No se pudo Crear la factura electrónica: \n' + str(response_json))
            else:
                raise UserError(
                    'No se pudo Crear la factura electrónica: \n' + str(response_json.get('resp').get('text')))

        return pos_order

    @api.model
    def _consul_hacienda_tiq(self):  # cron
        invoices = self.env['pos.order'].search([('state_tributacion', 'in', ('recibido', 'procesando'))])
        for i in invoices:
            url = i.company_id.frm_callback_url
            if i.company_id.frm_ws_ambiente == 'stag':
                env = 'api-stag'
            else:
                env = 'api-prod'
            response_json = functions.token_hacienda(i, env, url)
            _logger.info('Token MH')
            token_m_h = response_json.get('resp').get('access_token')
            if i.ticket_hacienda_number and len(i.ticket_hacienda_number) == 50:
                headers = {}
                payload = {}
                payload['w'] = 'consultar'
                payload['r'] = 'consultarCom'
                payload['client_id'] = env
                payload['token'] = token_m_h
                payload['clave'] = i.ticket_hacienda_number
                response = requests.request("POST", url, data=payload, headers=headers)
                responsejson = json.loads(response._content)
                estado_m_h = responsejson.get('resp').get('ind-estado')
                if estado_m_h == 'aceptado':
                    i.state_tributacion = estado_m_h
                    i.fname_xml_respuesta_tributacion = 'respuesta_' + i.ticket_hacienda_number + '.xml'
                    i.xml_respuesta_tributacion = responsejson.get('resp').get('respuesta-xml')
                elif estado_m_h == 'rechazado':
                    i.state_tributacion = estado_m_h
                    i.fname_xml_respuesta_tributacion = 'respuesta_' + i.ticket_hacienda_number + '.xml'
                    i.xml_respuesta_tributacion = responsejson.get('resp').get('respuesta-xml')
                elif estado_m_h == 'error':
                    i.state_tributacion = estado_m_h
