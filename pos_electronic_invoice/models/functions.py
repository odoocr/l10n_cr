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

_logger = logging.getLogger(__name__)


def get_clave(self, url, tipo_documento, next_number):
    payload = {}
    headers = {}
    # get Clave MH
    payload['w'] = 'clave'
    payload['r'] = 'clave'
    if self.company_id.identification_id.id == 1:
        payload['tipoCedula'] = 'fisico'
    elif self.company_id.identification_id.id == 2:
        payload['tipoCedula'] = 'juridico'
    payload['tipoDocumento'] = tipo_documento
    payload['cedula'] = self.company_id.vat
    payload['codigoPais'] = self.company_id.phone_code
    payload['consecutivo'] = next_number
    payload['situacion'] = 'normal'
    payload['codigoSeguridad'] = self.company_id.security_code

    response = requests.request("POST", url, data=payload, headers=headers)
    response_json = json.loads(response._content)
    return response_json


def make_xml_invoice(inv, tipo_documento, consecutivo, date, sale_conditions, medio_pago, total_servicio_gravado,
                     total_servicio_exento, total_mercaderia_gravado, total_mercaderia_exento, base_total, lines,
                     tipo_documento_referencia, numero_documento_referencia, fecha_emision_referencia,
                     codigo_referencia, razon_referencia, url):
    headers = {}
    payload = {}
    # Generar FE payload
    payload['w'] = 'genXML'
    if tipo_documento == 'FE':
        payload['r'] = 'gen_xml_fe'
    elif tipo_documento == 'NC':
        payload['r'] = 'gen_xml_nc'
    payload['clave'] = inv.number_electronic
    payload['consecutivo'] = consecutivo
    payload['fecha_emision'] = date
    payload['emisor_nombre'] = inv.company_id.name
    payload['emisor_tipo_indetif'] = inv.company_id.identification_id.code
    payload['emisor_num_identif'] = inv.company_id.vat
    payload['nombre_comercial'] = inv.company_id.commercial_name or ''
    payload['emisor_provincia'] = inv.company_id.state_id.code
    payload['emisor_canton'] = inv.company_id.county_id.code
    payload['emisor_distrito'] = inv.company_id.district_id.code
    payload['emisor_barrio'] = inv.company_id.neighborhood_id.code
    payload['emisor_otras_senas'] = inv.company_id.street
    payload['emisor_cod_pais_tel'] = inv.company_id.phone_code
    payload['emisor_tel'] = inv.company_id.phone
    if inv.company_id.fax_code:
        payload['emisor_cod_pais_fax'] = inv.company_id.fax_code
    else:
        payload['emisor_cod_pais_fax'] = ''
    if inv.company_id.fax:
        payload['emisor_fax'] = inv.company_id.fax
    else:
        payload['emisor_fax'] = ''
    payload['emisor_email'] = inv.company_id.email
    payload['receptor_nombre'] = inv.partner_id.name[:80]
    payload['receptor_tipo_identif'] = inv.partner_id.identification_id.code
    payload['receptor_num_identif'] = inv.partner_id.vat
    payload['receptor_provincia'] = inv.partner_id.state_id.code
    payload['receptor_canton'] = inv.partner_id.county_id.code
    payload['receptor_distrito'] = inv.partner_id.district_id.code
    payload['receptor_barrio'] = inv.partner_id.neighborhood_id.code
    payload['receptor_cod_pais_tel'] = inv.partner_id.phone_code
    payload['receptor_tel'] = inv.partner_id.phone
    if inv.partner_id.fax_code:
        payload['receptor_cod_pais_fax'] = inv.partner_id.fax_code
    else:
        payload['receptor_cod_pais_fax'] = ''
    if inv.partner_id.fax:
        payload['receptor_fax'] = inv.partner_id.fax
    else:
        payload['receptor_fax'] = ''
    payload['receptor_email'] = inv.partner_id.email
    payload['condicion_venta'] = sale_conditions
    payload['plazo_credito'] = ''
    payload['medio_pago'] = medio_pago
    payload['cod_moneda'] = inv.currency_id.name
    payload['tipo_cambio'] = 1
    payload['total_serv_gravados'] = total_servicio_gravado
    payload['total_serv_exentos'] = total_servicio_exento
    payload['total_merc_gravada'] = total_mercaderia_gravado
    payload['total_merc_exenta'] = total_mercaderia_exento
    payload['total_gravados'] = total_servicio_gravado + total_mercaderia_gravado
    payload['total_exentos'] = total_servicio_exento + total_mercaderia_exento
    payload[
        'total_ventas'] = total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento
    payload['total_descuentos'] = round(base_total, 2) - round(inv.amount_untaxed, 2)
    payload['total_ventas_neta'] = (total_servicio_gravado + total_mercaderia_gravado
                                    + total_servicio_exento + total_mercaderia_exento) \
                                   - (base_total - inv.amount_untaxed)
    payload['total_impuestos'] = inv.amount_tax
    payload['total_comprobante'] = inv.amount_total
    payload['otros'] = ''
    payload['detalles'] = lines
    if tipo_documento == 'NC':
        payload['infoRefeTipoDoc'] = tipo_documento_referencia
        payload['infoRefeNumero'] = numero_documento_referencia
        payload['infoRefeFechaEmision'] = fecha_emision_referencia
        payload['infoRefeCodigo'] = codigo_referencia
        payload['infoRefeRazon'] = razon_referencia

    response = requests.request("POST", url, data=payload, headers=headers)
    response_json = json.loads(response._content)
    return response_json


def token_hacienda(inv, env, url):
    payload = {}
    headers = {}
    payload['w'] = 'token'
    payload['r'] = 'gettoken'
    payload['grant_type'] = 'password'
    payload['client_id'] = env
    payload['username'] = inv.company_id.frm_ws_identificador
    payload['password'] = inv.company_id.frm_ws_password

    response = requests.request("POST", url, data=payload, headers=headers)
    response_json = json.loads(response._content)
    return response_json


def sign_xml(inv, tipo_documento, url, xml):
    payload = {}
    headers = {}
    payload['w'] = 'signXML'
    payload['r'] = 'signFE'
    payload['p12Url'] = inv.company_id.frm_apicr_signaturecode
    payload['inXml'] = xml
    payload['pinP12'] = inv.company_id.frm_pin
    payload['tipodoc'] = tipo_documento

    response = requests.request("POST", url, data=payload, headers=headers)
    response_json = json.loads(response._content)
    return response_json


def send_file(inv, token, date, xml, env, url):
    headers = {}
    payload = {}
    payload['w'] = 'send'
    payload['r'] = 'json'
    payload['token'] = token
    payload['clave'] = inv.number_electronic
    payload['fecha'] = date
    payload['emi_tipoIdentificacion'] = inv.company_id.identification_id.code
    payload['emi_numeroIdentificacion'] = inv.company_id.vat
    payload['recp_tipoIdentificacion'] = inv.partner_id.identification_id.code
    payload['recp_numeroIdentificacion'] = inv.partner_id.vat
    payload['comprobanteXml'] = xml
    payload['client_id'] = env

    response = requests.request("POST", url, data=payload, headers=headers)
    response_json = json.loads(response._content)
    return response_json


def consulta_documentos(self, inv, env, token_m_h, url, date_cr, xml_firmado):
    payload = {}
    headers = {}
    payload['w'] = 'consultar'
    payload['r'] = 'consultarCom'
    payload['client_id'] = env
    payload['token'] = token_m_h
    payload['clave'] = inv.number_electronic
    response = requests.request("POST", url, data=payload, headers=headers)
    response_json = json.loads(response._content)
    estado_m_h = response_json.get('resp').get('ind-estado')

    _logger.error('MAB - MH response:%s', response_json)

    if estado_m_h == 'aceptado':
        inv.fname_xml_respuesta_tributacion = 'respuesta_' + inv.number_electronic + '.xml'
        inv.xml_respuesta_tributacion = response_json.get('resp').get('respuesta-xml')
        if inv.type == 'in_invoice':
            inv.state_send_invoice = estado_m_h
        elif inv.type == 'out_invoice':
            inv.state_tributacion = estado_m_h
            inv.date_issuance = date_cr
            inv.fname_xml_comprobante = 'comprobante_' + inv.number_electronic + '.xml'
            inv.xml_comprobante = xml_firmado
            if not inv.partner_id.opt_out:
                email_template = self.env.ref('account.email_template_edi_invoice', False)
                attachment = self.env['ir.attachment'].search(
                    [('res_model', '=', 'account.invoice'), ('res_id', '=', inv.id),
                     ('res_field', '=', 'xml_comprobante')], limit=1)
                attachment.name = inv.fname_xml_comprobante
                attachment.datas_fname = inv.fname_xml_comprobante
                email_template.attachment_ids = [(6, 0, [attachment.id])]  # [(4, attachment.id)]
                email_template.with_context(type='binary', default_type='binary').send_mail(inv.id,
                                                                                            raise_exception=False,
                                                                                            force_send=True)  # default_type='binary'
                email_template.attachment_ids = [(3, attachment.id)]
    elif estado_m_h == 'recibido':
        if inv.type == 'in_invoice':
            inv.state_send_invoice = estado_m_h
        elif inv.type == 'out_invoice':
            inv.state_tributacion = estado_m_h;
            inv.date_issuance = date_cr
            inv.fname_xml_comprobante = 'comprobante_' + inv.number_electronic + '.xml'
            inv.xml_comprobante = xml_firmado
    elif estado_m_h == 'procesando':
        if inv.type == 'in_invoice':
            inv.state_send_invoice = estado_m_h
        elif inv.type == 'out_invoice':
            inv.state_tributacion = estado_m_h;
            inv.date_issuance = date_cr
            inv.fname_xml_comprobante = 'comprobante_' + inv.number_electronic + '.xml'
            inv.xml_comprobante = xml_firmado
    elif estado_m_h == 'rechazado':
        if inv.type == 'in_invoice':
            inv.state_send_invoice = estado_m_h
        elif inv.type == 'out_invoice':
            inv.state_tributacion = estado_m_h;
            inv.date_issuance = date_cr
            inv.fname_xml_comprobante = 'comprobante_' + inv.number_electronic + '.xml'
            inv.xml_comprobante = xml_firmado
            inv.fname_xml_respuesta_tributacion = 'respuesta_' + inv.number_electronic + '.xml'
            inv.xml_respuesta_tributacion = response_json.get('resp').get('respuesta-xml')
    elif estado_m_h == 'error':
        if inv.type == 'in_invoice':
            inv.state_send_invoice = estado_m_h
        elif inv.type == 'out_invoice':
            inv.state_tributacion = estado_m_h
            inv.date_issuance = date_cr
            inv.fname_xml_comprobante = 'comprobante_' + inv.number_electronic + '.xml'
            inv.xml_comprobante = xml_firmado
    else:
        raise UserError('No se pudo crear el documento: \n' + str(response_json))
