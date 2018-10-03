from odoo.exceptions import UserError
import json
import requests
import re
import random

def get_clave(self, url, tipo_documento, next_number,sucursal_id,terminal_id):
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
    payload['codigoSeguridad'] = str(random.randint(1, 99999999))

    response = requests.request("POST", url, data=payload, headers=headers)
    response_json = response.json()
    return response_json


def make_xml_invoice(inv, tipo_documento, consecutivo, date, sale_conditions, medio_pago, total_servicio_gravado,
                     total_servicio_exento, total_mercaderia_gravado, total_mercaderia_exento, base_total, lines,
                     tipo_documento_referencia, numero_documento_referencia, fecha_emision_referencia,
                     codigo_referencia, razon_referencia, url, currency_rate):
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
    payload['emisor_barrio'] = inv.company_id.neighborhood_id.code or ''
    payload['emisor_otras_senas'] = inv.company_id.street
    payload['emisor_cod_pais_tel'] = inv.company_id.phone_code
    payload['emisor_tel'] = re.sub('[^0-9]+', '', inv.company_id.phone)
    payload['emisor_email'] = inv.company_id.email
    payload['receptor_nombre'] = inv.partner_id.name[:80]
    if inv.partner_id.identification_id.code == '05':
        payload['receptor_tipo_identif'] = inv.partner_id.identification_id.code
    else:
        payload['receptor_tipo_identif'] = inv.partner_id.identification_id.code
    payload['receptor_num_identif'] = inv.partner_id.vat
    payload['receptor_provincia'] = inv.partner_id.state_id.code or ''
    payload['receptor_canton'] = inv.partner_id.county_id.code or ''
    payload['receptor_distrito'] = inv.partner_id.district_id.code or ''
    payload['receptor_barrio'] = inv.partner_id.neighborhood_id.code or ''
    payload['receptor_cod_pais_tel'] = inv.partner_id.phone_code
    payload['receptor_tel'] = re.sub('[^0-9]+', '', inv.partner_id.phone)
    payload['receptor_email'] = inv.partner_id.email
    payload['condicion_venta'] = sale_conditions
    payload['plazo_credito'] = inv.partner_id.property_payment_term_id.line_ids[0].days or '0'
    payload['medio_pago'] = medio_pago
    payload['cod_moneda'] = inv.currency_id.name
    payload['tipo_cambio'] = currency_rate
    payload['total_serv_gravados'] = total_servicio_gravado
    payload['total_serv_exentos'] = total_servicio_exento
    payload['total_merc_gravada'] = total_mercaderia_gravado
    payload['total_merc_exenta'] = total_mercaderia_exento
    payload['total_gravados'] = total_servicio_gravado + total_mercaderia_gravado
    payload['total_exentos'] = total_servicio_exento + total_mercaderia_exento
    payload['total_ventas'] = total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento
    payload['total_descuentos'] = round(base_total - inv.amount_untaxed, 2)
    payload['total_ventas_neta'] = round((total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento) - \
                                   (base_total - inv.amount_untaxed), 2)
    payload['total_impuestos'] = round(inv.amount_tax, 2)
    payload['total_comprobante'] = round(inv.amount_total, 2)
    payload['otros'] = ''
    payload['detalles'] = lines

    if tipo_documento == 'NC':
        payload['infoRefeTipoDoc'] = tipo_documento_referencia
        payload['infoRefeNumero'] = numero_documento_referencia
        payload['infoRefeFechaEmision'] = fecha_emision_referencia
        payload['infoRefeCodigo'] = codigo_referencia
        payload['infoRefeRazon'] = razon_referencia

    response = requests.request("POST", url, data=payload, headers=headers)
    response_json = response.json()
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
    response_json = response.json()
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
    response_json = response.json()
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
    response_json = response.json()
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
    response_json = response.json()
    estado_m_h = response_json.get('resp').get('ind-estado')

    # Se actualiza el estado con el que devuelve Hacienda
    inv.state_tributacion = estado_m_h

    # Siempre sin importar el estado se actualiza la fecha de acuerdo a la devuelta por Hacienda y
    # se carga el xml devuelto por Hacienda
    if inv.type == 'out_invoice' or inv.type == 'out_refund':
        inv.date_issuance = date_cr
        inv.fname_xml_comprobante = 'comprobante_' + inv.number_electronic + '.xml'
        inv.xml_comprobante = xml_firmado

    # Si fue aceptado o rechazado por haciendo se carga la respuesta
    if (estado_m_h == 'aceptado' or estado_m_h == 'rechazado') or (inv.type == 'out_invoice'  or inv.type == 'out_refund'):
        inv.fname_xml_respuesta_tributacion = 'respuesta_' + inv.number_electronic + '.xml'
        inv.xml_respuesta_tributacion = response_json.get('resp').get('respuesta-xml')

    # Si fue aceptado por Hacienda y es un factura de cliente o nota de crédito, se envía el correo con los documentos
    if estado_m_h == 'aceptado' and (inv.type == 'out_invoice' or inv.type == 'out_refund'):
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

