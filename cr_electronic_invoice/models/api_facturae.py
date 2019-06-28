import requests
import datetime
import json
from . import fe_enums
import io
import re
import base64
import hashlib
import urllib
import logging
import pytz
import time
import logging
import xmlsig
import random

from odoo.exceptions import UserError
from xml.sax.saxutils import escape
from ..xades.context2 import XAdESContext2, PolicyId2, create_xades_epes_signature

try:
    from lxml import etree
except ImportError:
    from xml.etree import ElementTree

try:
    from OpenSSL import crypto
except(ImportError, IOError) as err:
    logging.info(err)

# PARA VALIDAR JSON DE RESPUESTA
from .. import extensions

_logger = logging.getLogger(__name__)


def sign_xml(cert, password, xml, policy_id='https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/'
             '2016/v4.2/ResolucionComprobantesElectronicosDGT-R-48-2016_4.2.pdf'):
    root = etree.fromstring(xml)
    signature = create_xades_epes_signature()

    policy = PolicyId2()
    policy.id = policy_id

    root.append(signature)
    ctx = XAdESContext2(policy)
    certificate = crypto.load_pkcs12(base64.b64decode(cert), password)
    ctx.load_pkcs12(certificate)
    ctx.sign(signature)

    return etree.tostring(root, encoding='UTF-8', method='xml', xml_declaration=True, with_tail=False)


def get_time_hacienda():
    now_utc = datetime.datetime.now(pytz.timezone('UTC'))
    now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
    date_cr = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")

    return date_cr


# Utilizada para establecer un limite de caracteres en la cedula del cliente, no mas de 20
# de lo contrario hacienda lo rechaza
def limit(str, limit):
    return (str[:limit - 3] + '...') if len(str) > limit else str


def get_mr_sequencevalue(inv):
    '''Verificamos si el ID del mensaje receptor es válido'''
    mr_mensaje_id = int(inv.state_invoice_partner)
    if mr_mensaje_id < 1 or mr_mensaje_id > 3:
        raise UserError('El ID del mensaje receptor es inválido.')
    elif mr_mensaje_id is None:
        raise UserError('No se ha proporcionado un ID válido para el MR.')

    if inv.state_invoice_partner == '1':
        detalle_mensaje = 'Aceptado'
        tipo = 1
        tipo_documento = fe_enums.TipoDocumento['CCE']
        sequence = inv.env['ir.sequence'].next_by_code(
            'sequece.electronic.doc.confirmation')

    elif inv.state_invoice_partner == '2':
        detalle_mensaje = 'Aceptado parcial'
        tipo = 2
        tipo_documento = fe_enums.TipoDocumento['CPCE']
        sequence = inv.env['ir.sequence'].next_by_code(
            'sequece.electronic.doc.partial.confirmation')
    else:
        detalle_mensaje = 'Rechazado'
        tipo = 3
        tipo_documento = fe_enums.TipoDocumento['RCE']
        sequence = inv.env['ir.sequence'].next_by_code(
            'sequece.electronic.doc.reject')

    return {'detalle_mensaje': detalle_mensaje, 'tipo': tipo, 'tipo_documento': tipo_documento, 'sequence': sequence}


def get_consecutivo_hacienda(tipo_documento, consecutivo, sucursal_id, terminal_id):

    tipo_doc = fe_enums.TipoDocumento[tipo_documento]

    inv_consecutivo = str(consecutivo).zfill(10)
    inv_sucursal = str(sucursal_id).zfill(3)
    inv_terminal = str(terminal_id).zfill(5)

    consecutivo_mh = inv_sucursal + inv_terminal + tipo_doc + inv_consecutivo

    return consecutivo_mh


def get_clave_hacienda(self, tipo_documento, consecutivo, sucursal_id, terminal_id, situacion='normal'):

    tipo_doc = fe_enums.TipoDocumento[tipo_documento]

    '''Verificamos si el consecutivo indicado corresponde a un numero'''
    inv_consecutivo = re.sub('[^0-9]', '', consecutivo)
    if len(inv_consecutivo) != 10:
        raise UserError('La numeración debe de tener 10 dígitos')

    '''Verificamos la sucursal y terminal'''
    inv_sucursal = re.sub('[^0-9]', '', str(sucursal_id)).zfill(3)
    inv_terminal = re.sub('[^0-9]', '', str(terminal_id)).zfill(5)

    '''Armamos el consecutivo pues ya tenemos los datos necesarios'''
    consecutivo_mh = inv_sucursal + inv_terminal + tipo_doc + inv_consecutivo

    if not self.company_id.identification_id:
        raise UserError(
            'Seleccione el tipo de identificación del emisor en el pérfil de la compañía')

    '''Obtenemos el número de identificación del Emisor y lo validamos númericamente'''
    inv_cedula = re.sub('[^0-9]', '', self.company_id.vat)

    '''Validamos el largo de la cadena númerica de la cédula del emisor'''
    if self.company_id.identification_id.code == '01' and len(inv_cedula) != 9:
        raise UserError('La Cédula Física del emisor debe de tener 9 dígitos')
    elif self.company_id.identification_id.code == '02' and len(inv_cedula) != 10:
        raise UserError(
            'La Cédula Jurídica del emisor debe de tener 10 dígitos')
    elif self.company_id.identification_id.code == '03' and (len(inv_cedula) != 11 or len(inv_cedula) != 12):
        raise UserError(
            'La identificación DIMEX del emisor debe de tener 11 o 12 dígitos')
    elif self.company_id.identification_id.code == '04' and len(inv_cedula) != 10:
        raise UserError(
            'La identificación NITE del emisor debe de tener 10 dígitos')

    inv_cedula = str(inv_cedula).zfill(12)

    '''Limitamos la cedula del emisor a 20 caracteres o nos dará error'''
    cedula_emisor = limit(inv_cedula, 20)

    '''Validamos la situación del comprobante electrónico'''
    situacion_comprobante = fe_enums.SituacionComprobante.get(situacion)
    if not situacion_comprobante:
        raise UserError(
            'La situación indicada para el comprobante electŕonico es inválida: ' + situacion)

    '''Creamos la fecha para la clave'''
    now_utc = datetime.datetime.now(pytz.timezone('UTC'))
    now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))

    cur_date = now_cr.strftime("%d%m%y")

    codigo_pais = self.company_id.phone_code

    '''Creamos un código de seguridad random'''
    codigo_seguridad = str(random.randint(1, 99999999)).zfill(8)

    clave_hacienda = codigo_pais + cur_date + cedula_emisor + \
        consecutivo_mh + situacion_comprobante + codigo_seguridad

    return {'length': len(clave_hacienda), 'clave': clave_hacienda, 'consecutivo': consecutivo_mh}


'''Variables para poder manejar el Refrescar del Token'''
last_tokens = {}
last_tokens_time = {}
last_tokens_expire = {}
last_tokens_refresh = {}


def get_token_hacienda(inv, tipo_ambiente):
    global last_tokens
    global last_tokens_time
    global last_tokens_expire
    global last_tokens_refresh
    
    token = last_tokens.get(inv.company_id.id, False)
    token_time = last_tokens_time.get(inv.company_id.id, False)
    token_expire = last_tokens_expire.get(inv.company_id.id, 0)
    current_time = time.time()

    if token and (current_time - token_time < token_expire-10):
        token_hacienda = token
    else:
        headers = {}
        data = {'client_id': tipo_ambiente,
                'client_secret': '',
                'grant_type': 'password',
                'username': inv.company_id.frm_ws_identificador,
                'password': inv.company_id.frm_ws_password
                }

        # establecer el ambiente al cual me voy a conectar
        endpoint = fe_enums.UrlHaciendaToken[tipo_ambiente]

        try:
            # enviando solicitud post y guardando la respuesta como un objeto json
            response = requests.request(
                "POST", endpoint, data=data, headers=headers)
            response_json = response.json()

            respuesta = extensions.response_validator.assert_valid_schema(
                response_json, 'token.json')

            if 200 <= response.status_code <= 299:
                token_hacienda = response_json.get('access_token')
                last_tokens[inv.company_id.id] = token
                last_tokens_time[inv.company_id.id] = time.time()
                last_tokens_expire[inv.company_id.id] = response_json.get('expires_in')
                last_tokens_refresh[inv.company_id.id] = response_json.get('refresh_expires_in')
            else:
                _logger.error(
                    'MAB - token_hacienda failed.  error: %s', response.status_code)

        except requests.exceptions.RequestException as e:
            raise Warning(
                'Error Obteniendo el Token desde MH. Excepcion %s' % e)

    return token_hacienda


def refresh_token_hacienda(tipo_ambiente, token):

    headers = {}
    data = {'client_id': tipo_ambiente,
            'client_secret': '',
            'grant_type': 'refresh_token',
            'refresh_token': token
            }

    # establecer el ambiente al cual me voy a conectar
    endpoint = fe_enums.UrlHaciendaToken[tipo_ambiente]

    try:
        # enviando solicitud post y guardando la respuesta como un objeto json
        response = requests.request(
            "POST", endpoint, data=data, headers=headers)
        response_json = response.json()
        token_hacienda = response_json.get('access_token')
        return token_hacienda
    except ImportError:
        raise Warning('Error Refrescando el Token desde MH')


def gen_xml_mr_42(clave, cedula_emisor, fecha_emision, id_mensaje, detalle_mensaje, cedula_receptor, consecutivo_receptor,
                  monto_impuesto=0, total_factura=0):
    '''Verificamos si la clave indicada corresponde a un numeros'''
    mr_clave = re.sub('[^0-9]', '', clave)
    if len(mr_clave) != 50:
        raise UserError(
            'La clave a utilizar es inválida. Debe contener al menos 50 digitos')

    '''Obtenemos el número de identificación del Emisor y lo validamos númericamente'''
    mr_cedula_emisor = re.sub('[^0-9]', '', cedula_emisor)
    if len(mr_cedula_emisor) != 12:
        mr_cedula_emisor = str(mr_cedula_emisor).zfill(12)
    elif mr_cedula_emisor is None:
        raise UserError('La cédula del Emisor en el MR es inválida.')

    mr_fecha_emision = fecha_emision
    if mr_fecha_emision is None:
        raise UserError('La fecha de emisión en el MR es inválida.')

    '''Verificamos si el ID del mensaje receptor es válido'''
    mr_mensaje_id = int(id_mensaje)
    if mr_mensaje_id < 1 and mr_mensaje_id > 3:
        raise UserError('El ID del mensaje receptor es inválido.')
    elif mr_mensaje_id is None:
        raise UserError('No se ha proporcionado un ID válido para el MR.')

    mr_cedula_receptor = re.sub('[^0-9]', '', cedula_receptor)
    if len(mr_cedula_receptor) != 12:
        mr_cedula_receptor = str(mr_cedula_receptor).zfill(12)
    elif mr_cedula_receptor is None:
        raise UserError(
            'No se ha proporcionado una cédula de receptor válida para el MR.')

    '''Verificamos si el consecutivo indicado para el mensaje receptor corresponde a numeros'''
    mr_consecutivo_receptor = re.sub('[^0-9]', '', consecutivo_receptor)
    if len(mr_consecutivo_receptor) != 20:
        raise UserError('La clave del consecutivo para el mensaje receptor es inválida. '
                        'Debe contener al menos 50 digitos')

    mr_monto_impuesto = monto_impuesto
    mr_detalle_mensaje = detalle_mensaje
    mr_total_factura = total_factura

    '''Iniciamos con la creación del mensaje Receptor'''
    sb = StringBuilder()
    sb.Append(
        '<MensajeReceptor xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append(
        'xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/mensajeReceptor" ')
    sb.Append(
        'xsi:schemaLocation="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/mensajeReceptor ')
    sb.Append(
        'https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/MensajeReceptor_4.2.xsd">')
    sb.Append('<Clave>' + mr_clave + '</Clave>')
    sb.Append('<NumeroCedulaEmisor>' +
              mr_cedula_emisor + '</NumeroCedulaEmisor>')
    sb.Append('<FechaEmisionDoc>' + mr_fecha_emision + '</FechaEmisionDoc>')
    sb.Append('<Mensaje>' + str(mr_mensaje_id) + '</Mensaje>')

    if mr_detalle_mensaje is not None:
        sb.Append('<DetalleMensaje>' +
                  escape(mr_detalle_mensaje) + '</DetalleMensaje>')

    if mr_monto_impuesto is not None and mr_monto_impuesto > 0:
        sb.Append('<MontoTotalImpuesto>' +
                  str(mr_monto_impuesto) + '</MontoTotalImpuesto>')

    if mr_total_factura is not None and mr_total_factura > 0:
        sb.Append('<TotalFactura>' + str(mr_total_factura) + '</TotalFactura>')
    else:
        raise UserError(
            'El monto Total de la Factura para el Mensaje Receptro es inválido')

    sb.Append('<NumeroCedulaReceptor>' +
              mr_cedula_receptor + '</NumeroCedulaReceptor>')
    sb.Append('<NumeroConsecutivoReceptor>' +
              mr_consecutivo_receptor + '</NumeroConsecutivoReceptor>')
    sb.Append('</MensajeReceptor>')

    mreceptor_bytes = str(sb)
    mr_to_base64 = stringToBase64(mreceptor_bytes)

    return base64UTF8Decoder(mr_to_base64)


def gen_xml_mr_43(clave, cedula_emisor, fecha_emision, id_mensaje,
                  detalle_mensaje, cedula_receptor,
                  consecutivo_receptor,
                  monto_impuesto=0, total_factura=0,
                  codigo_actividad=False,
                  monto_total_impuesto_acreditar=False,
                  monto_total_gasto_aplicable=False,
                  condicion_impuesto=False):
    '''Verificamos si la clave indicada corresponde a un numeros'''
    mr_clave = re.sub('[^0-9]', '', clave)
    if len(mr_clave) != 50:
        raise UserError(
            'La clave a utilizar es inválida. Debe contener al menos 50 digitos')

    '''Obtenemos el número de identificación del Emisor y lo validamos númericamente'''
    mr_cedula_emisor = re.sub('[^0-9]', '', cedula_emisor)
    if len(mr_cedula_emisor) != 12:
        mr_cedula_emisor = str(mr_cedula_emisor).zfill(12)
    elif mr_cedula_emisor is None:
        raise UserError('La cédula del Emisor en el MR es inválida.')

    mr_fecha_emision = fecha_emision
    if mr_fecha_emision is None:
        raise UserError('La fecha de emisión en el MR es inválida.')

    '''Verificamos si el ID del mensaje receptor es válido'''
    mr_mensaje_id = int(id_mensaje)
    if mr_mensaje_id < 1 and mr_mensaje_id > 3:
        raise UserError('El ID del mensaje receptor es inválido.')
    elif mr_mensaje_id is None:
        raise UserError('No se ha proporcionado un ID válido para el MR.')

    mr_cedula_receptor = re.sub('[^0-9]', '', cedula_receptor)
    if len(mr_cedula_receptor) != 12:
        mr_cedula_receptor = str(mr_cedula_receptor).zfill(12)
    elif mr_cedula_receptor is None:
        raise UserError(
            'No se ha proporcionado una cédula de receptor válida para el MR.')

    '''Verificamos si el consecutivo indicado para el mensaje receptor corresponde a numeros'''
    mr_consecutivo_receptor = re.sub('[^0-9]', '', consecutivo_receptor)
    if len(mr_consecutivo_receptor) != 20:
        raise UserError('La clave del consecutivo para el mensaje receptor es inválida. '
                        'Debe contener al menos 50 digitos')

    mr_monto_impuesto = monto_impuesto
    mr_detalle_mensaje = detalle_mensaje
    mr_total_factura = total_factura

    '''Iniciamos con la creación del mensaje Receptor'''
    sb = StringBuilder()
    sb.Append(
        '<MensajeReceptor xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append(
        'xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/mensajeReceptor" ')
    sb.Append(
        'xsi:schemaLocation="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/mensajeReceptor ')
    sb.Append(
        'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/MensajeReceptor_V4.3.xsd">')
    sb.Append('<Clave>' + mr_clave + '</Clave>')
    sb.Append('<NumeroCedulaEmisor>' +
              mr_cedula_emisor + '</NumeroCedulaEmisor>')
    sb.Append('<FechaEmisionDoc>' + mr_fecha_emision + '</FechaEmisionDoc>')
    sb.Append('<Mensaje>' + str(mr_mensaje_id) + '</Mensaje>')

    if mr_detalle_mensaje is not None:
        sb.Append('<DetalleMensaje>' +
                  escape(mr_detalle_mensaje) + '</DetalleMensaje>')

    if mr_monto_impuesto is not None and mr_monto_impuesto > 0:
        sb.Append('<MontoTotalImpuesto>' +
                  str(mr_monto_impuesto) + '</MontoTotalImpuesto>')

    if codigo_actividad:
        sb.Append('<CodigoActividad>' +
                  str(codigo_actividad) + '</CodigoActividad>')

    # TODO: Estar atento a la publicación de Hacienda de cómo utilizar esto
    if condicion_impuesto:
        sb.Append('<CondicionImpuesto>' +
                  str(condicion_impuesto) + '</CondicionImpuesto>')

    # TODO: Estar atento a la publicación de Hacienda de cómo utilizar esto
    if monto_total_impuesto_acreditar:
        sb.Append(
            '<MontoTotalImpuestoAcreditar>' +
            str(monto_total_impuesto_acreditar) +
            '</MontoTotalImpuestoAcreditar>')

    # TODO: Estar atento a la publicación de Hacienda de cómo utilizar esto
    if monto_total_gasto_aplicable:
        sb.Append('<MontoTotalDeGastoAplicable>' +
                  str(monto_total_gasto_aplicable) +
                  '</MontoTotalDeGastoAplicable>')

    if mr_total_factura is not None and mr_total_factura > 0:
        sb.Append('<TotalFactura>' + str(mr_total_factura) + '</TotalFactura>')
    else:
        raise UserError(
            'El monto Total de la Factura para el Mensaje Receptro es inválido'
            )

    sb.Append('<NumeroCedulaReceptor>' +
              mr_cedula_receptor + '</NumeroCedulaReceptor>')
    sb.Append('<NumeroConsecutivoReceptor>' +
              mr_consecutivo_receptor + '</NumeroConsecutivoReceptor>')
    sb.Append('</MensajeReceptor>')

    mreceptor_bytes = str(sb)
    mr_to_base64 = stringToBase64(mreceptor_bytes)

    return base64UTF8Decoder(mr_to_base64)


def gen_xml_fe_v42(inv, date_issuance, sale_conditions,
                   total_servicio_gravado, total_servicio_exento,
                   total_mercaderia_gravado, total_mercaderia_exento,
                   base_total, total_impuestos, total_descuento,
                   lines, currency_rate, invoice_comments):

    numero_linea = 0

    if inv._name == 'pos.order':
        plazo_credito = '0'
        cod_moneda = inv.company_id.currency_id.name
    else:
        plazo_credito = inv.payment_term_id and inv.payment_term_id.line_ids[0].days or 0
        cod_moneda = inv.currency_id.name

    sb = StringBuilder()
    sb.Append(
        '<FacturaElectronica xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append(
        'xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/facturaElectronica" ')
    sb.Append(
        'xsi:schemaLocation="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/facturaElectronica ')
    sb.Append(
        'https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/FacturaElectronica_V.4.2.xsd">')
    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<NumeroConsecutivo>' +
              inv.number_electronic[21:41] + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + date_issuance + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' +
              escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')

    vat = inv.partner_id and inv.partner_id.vat and re.sub('[^0-9]', '', inv.partner_id.vat)
    if inv.partner_id and vat:
        if not inv.partner_id.identification_id:
            if len(vat) == 9:  # cedula fisica
                id_code = '01'
            elif len(vat) == 10:  # cedula juridica
                id_code = '02'
            elif len(vat) == 11 or len(vat) == 12:  # dimex
                id_code = '03'
            else:
                id_code = '05'
        else:
            id_code = inv.partner_id.identification_id.code

        sb.Append('<Receptor>')
        sb.Append('<Nombre>' + escape(str(inv.partner_id.name[:80])) + '</Nombre>')

        if id_code == '05':
            sb.Append('<IdentificacionExtranjero>' + vat + '</IdentificacionExtranjero>')
        else:
            sb.Append('<Identificacion>')
            sb.Append('<Tipo>' + id_code + '</Tipo>')
            sb.Append('<Numero>' + vat + '</Numero>')
            sb.Append('</Identificacion>')

        if inv.partner_id.state_id and inv.partner_id.county_id and inv.partner_id.district_id and inv.partner_id.neighborhood_id:
            sb.Append('<Ubicacion>')
            sb.Append('<Provincia>' + str(inv.partner_id.state_id.code or '') + '</Provincia>')
            sb.Append('<Canton>' + str(inv.partner_id.county_id.code or '') + '</Canton>')
            sb.Append('<Distrito>' + str(inv.partner_id.district_id.code or '') + '</Distrito>')
            sb.Append('<Barrio>' + str(inv.partner_id.neighborhood_id.code or '00') + '</Barrio>')
            sb.Append('<OtrasSenas>' + escape(str(inv.partner_id.street or 'NA')) + '</OtrasSenas>')
            sb.Append('</Ubicacion>')
        telefono_receptor = inv.partner_id.phone and re.sub('[^0-9]+', '', inv.partner_id.phone)
        if telefono_receptor:
            sb.Append('<Telefono>')
            sb.Append('<CodigoPais>' + inv.partner_id.phone_code or '506' + '</CodigoPais>')
            sb.Append('<NumTelefono>' + telefono_receptor + '</NumTelefono>')
            sb.Append('</Telefono>')
        match = inv.partner_id.email and re.match(r'^(\s?[^\s,]+@[^\s,]+\.[^\s,]+\s?,)*(\s?[^\s,]+@[^\s,]+\.[^\s,]+)$', inv.partner_id.email.lower())
        if match:
            email_receptor = inv.partner_id.email
        else:
            email_receptor = 'indefinido@indefinido.com'
        sb.Append('<CorreoElectronico>' + email_receptor + '</CorreoElectronico>')
        sb.Append('</Receptor>')
    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.Append('<PlazoCredito>' + str(plazo_credito) + '</PlazoCredito>')
    sb.Append('<MedioPago>' + (inv.payment_methods_id.sequence or '01') + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')
        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' +
                  str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' +
                  str(v['precioUnitario']) + '</PrecioUnitario>')
        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
        if v.get('montoDescuento'):
            sb.Append('<Descuento><MontoDescuento>' +
                      str(v['montoDescuento']) + '</MontoDescuento>')
            if v.get('naturalezaDescuento'):
                sb.Append('<NaturalezaDescuento>' +
                          str(v['naturalezaDescuento']) + '</NaturalezaDescuento>')
            sb.Append('</Descuento>')
        sb.Append('<SubTotal>' + str(v['subtotal']) + '</SubTotal>')
        if v.get('impuesto'):
            for (a, b) in v['impuesto'].items():
                sb.Append('<Impuesto>')
                sb.Append('<Codigo>' + str(b['codigo']) + '</Codigo>')
                sb.Append('<Tarifa>' + str(b['tarifa']) + '</Tarifa>')
                sb.Append('<Monto>' + str(b['monto']) + '</Monto>')

                if b.get('exoneracion'):
                    for (c, d) in b['exoneracion']:
                        sb.Append('<Exoneracion>')
                        sb.Append('<TipoDocumento>' +
                                  d['tipoDocumento'] + '</TipoDocumento>')
                        sb.Append('<NumeroDocumento>' +
                                  d['numeroDocumento'] + '</NumeroDocumento>')
                        sb.Append('<NombreInstitucion>' +
                                  d['nombreInstitucion'] + '</NombreInstitucion>')
                        sb.Append('<FechaEmision>' +
                                  d['fechaEmision'] + '</FechaEmision>')
                        sb.Append('<MontoImpuesto>' +
                                  d['montoImpuesto'] + '</MontoImpuesto>')
                        sb.Append('<PorcentajeCompra>' +
                                  d['porcentajeCompra'] + '</PorcentajeCompra>')
                        sb.Append('</Exoneracion>')

                sb.Append('</Impuesto>')
        sb.Append('<MontoTotalLinea>' +
                  str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')
    sb.Append('</DetalleServicio>')
    sb.Append('<ResumenFactura>')
    sb.Append('<CodigoMoneda>' + str(cod_moneda) + '</CodigoMoneda>')
    sb.Append('<TipoCambio>' + str(currency_rate) + '</TipoCambio>')
    sb.Append('<TotalServGravados>' +
              str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' +
              str(total_servicio_exento) + '</TotalServExentos>')
    sb.Append('<TotalMercanciasGravadas>' +
              str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' +
              str(total_mercaderia_exento) + '</TotalMercanciasExentas>')
    sb.Append('<TotalGravado>' + str(total_servicio_gravado +
                                     total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento +
                                    total_mercaderia_exento) + '</TotalExento>')
    sb.Append('<TotalVenta>' + str(total_servicio_gravado + total_mercaderia_gravado +
                                   total_servicio_exento + total_mercaderia_exento) + '</TotalVenta>')
    sb.Append('<TotalDescuentos>' +
              str(round(total_descuento, 5)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' +
              str(round(base_total, 5)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' +
              str(round(total_impuestos, 5)) + '</TotalImpuesto>')
    sb.Append('<TotalComprobante>' + str(round(base_total +
                                               total_impuestos, 5)) + '</TotalComprobante>')
    sb.Append('</ResumenFactura>')
    sb.Append('<Normativa>')
    sb.Append('<NumeroResolucion>DGT-R-48-2016</NumeroResolucion>')
    sb.Append('<FechaResolucion>07-10-2016 08:00:00</FechaResolucion>')
    sb.Append('</Normativa>')
    if invoice_comments:
        sb.Append('<Otros>')
        sb.Append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
        sb.Append('</Otros>')

    sb.Append('</FacturaElectronica>')

    #felectronica_bytes = str(sb)
    return sb
    # return stringToBase64(felectronica_bytes)


def gen_xml_fe_v43(inv, sale_conditions, total_servicio_gravado, total_servicio_exento,
                   totalServExonerado, total_mercaderia_gravado, total_mercaderia_exento, totalMercExonerada,
                   totalOtrosCargos, base_total, total_impuestos, total_descuento, lines, otrosCargos,
                   currency_rate, invoice_comments
):

    numero_linea = 0

    sb = StringBuilder()
    sb.Append('<FacturaElectronica xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronica" ')
    sb.Append(
        'xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsd="http://www.w3.org/2001/XMLSchema" ')
    sb.Append('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append('xsi:schemaLocation="https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/FacturaElectronica_V4.3.xsd">')

    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<CodigoActividad>' +
              inv.company_id.activity_id.code + '</CodigoActividad>')
    sb.Append('<NumeroConsecutivo>' + inv.number_electronic[21:41] + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + get_time_hacienda() + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' +
              escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')
    sb.Append('<Receptor>')
    sb.Append('<Nombre>' + escape(str(inv.partner_id.name[:80])) + '</Nombre>')

    if inv.partner_id.identification_id.code == '05':
        sb.Append('<IdentificacionExtranjero>' +
                  inv.partner_id.vat + '</IdentificacionExtranjero>')
    else:
        sb.Append('<Identificacion>')
        sb.Append('<Tipo>' + inv.partner_id.identification_id.code + '</Tipo>')
        sb.Append('<Numero>' + inv.partner_id.vat + '</Numero>')
        sb.Append('</Identificacion>')

    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' +
              str(inv.partner_id.state_id.code or '') + '</Provincia>')
    sb.Append('<Canton>' + str(inv.partner_id.county_id.code or '') + '</Canton>')
    sb.Append('<Distrito>' +
              str(inv.partner_id.district_id.code or '') + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.partner_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              escape(str(inv.partner_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.partner_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.partner_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.partner_id.email) + '</CorreoElectronico>')
    sb.Append('</Receptor>')
    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.Append('<PlazoCredito>' +
              str(inv.payment_term_id and inv.payment_term_id.line_ids[0].days or '0') + '</PlazoCredito>')
    sb.Append('<MedioPago>' + (inv.payment_methods_id.sequence or '01') + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')
        # sb.Append('<CodigoComercial>' + str(v['codigoProducto']) + '</CodigoComercial>')
        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' +
                  str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' +
                  str(v['precioUnitario']) + '</PrecioUnitario>')
        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
        if v.get('montoDescuento'):
            sb.Append('<Descuento>')
            sb.Append('<MontoDescuento>' +
                      str(v['montoDescuento']) + '</MontoDescuento>')
            if v.get('naturalezaDescuento'):
                sb.Append('<NaturalezaDescuento>' +
                          str(v['naturalezaDescuento']) + '</NaturalezaDescuento>')
            sb.Append('</Descuento>')

        sb.Append('<SubTotal>' + str(v['subtotal']) + '</SubTotal>')

        # TODO: ¿qué es base imponible? ¿porqué podría ser diferente del subtotal?
        # sb.Append('<BaseImponible>' + str(v['subtotal']) + '</BaseImponible>')

        if v.get('impuesto'):
            for (a, b) in v['impuesto'].items():
                sb.Append('<Impuesto>')
                sb.Append('<Codigo>' + str(b['codigo']) + '</Codigo>')
                sb.Append('<CodigoTarifa>' +
                          str(b['iva_tax_code']) + '</CodigoTarifa>')
                sb.Append('<Tarifa>' + str(b['tarifa']) + '</Tarifa>')
                sb.Append('<Monto>' + str(b['monto']) + '</Monto>')

                if b.get('exoneracion'):
                    sb.Append('<Exoneracion>')
                    sb.Append('<TipoDocumento>' +
                              inv.partner_id.type_exoneration.code + '</TipoDocumento>')
                    sb.Append('<NumeroDocumento>' +
                              inv.partner_id.exoneration_number + '</NumeroDocumento>')
                    sb.Append('<NombreInstitucion>' +
                              inv.partner_id.institution_name + '</NombreInstitucion>')
                    sb.Append('<FechaEmision>' +
                              str(inv.partner_id.date_issue) + 'T00:00:00-06:00' + '</FechaEmision>')
                    sb.Append('<PorcentajeExoneracion>' +
                              str(b['exoneracion']['porcentajeCompra']) + '</PorcentajeExoneracion>')
                    sb.Append( '<MontoExoneracion>' +
                               str( b['exoneracion']['montoImpuesto'] ) + '</MontoExoneracion>' )
                    sb.Append( '</Exoneracion>' )

                sb.Append('</Impuesto>')
        sb.Append('<ImpuestoNeto>' + str(v['impuestoNeto']) + '</ImpuestoNeto>')

        sb.Append('<MontoTotalLinea>' +
                  str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')
    sb.Append('</DetalleServicio>')

    # TODO: ¿Cómo implementar otros cargos a nivel de UI y model en Odoo?
    if otrosCargos:
        sb.Append('<OtrosCargos>')
        for otro_cargo in otrosCargos:
            sb.Append('<TipoDocumento>' +
                      str(otrosCargos[otro_cargo]['TipoDocumento']) +
                      '</TipoDocumento>')

            if otrosCargos[otro_cargo].get('NumeroIdentidadTercero'):
                sb.Append('<NumeroIdentidadTercero>' +
                          str(otrosCargos[otro_cargo]['NumeroIdentidadTercero']) +
                          '</NumeroIdentidadTercero>')

            if otrosCargos[otro_cargo].get('NombreTercero'):
                sb.Append('<NombreTercero>' +
                          str(otrosCargos[otro_cargo]['NombreTercero']) +
                          '</NombreTercero>')

            sb.Append('<Detalle>' +
                      str(otrosCargos[otro_cargo]['Detalle']) +
                      '</Detalle>')

            if otrosCargos[otro_cargo].get('Porcentaje'):
                sb.Append('<Porcentaje>' +
                          str(otrosCargos[otro_cargo]['Porcentaje']) +
                          '</Porcentaje>')

            sb.Append('<MontoCargo>' +
                      str(otrosCargos[otro_cargo]['MontoCargo']) +
                      '</MontoCargo>')
        sb.Append('</OtrosCargos>')

    sb.Append('<ResumenFactura>')
    sb.Append('<CodigoTipoMoneda><CodigoMoneda>' +
              str(inv.currency_id.name) +
              '</CodigoMoneda><TipoCambio>' +
              str(currency_rate) +
              '</TipoCambio></CodigoTipoMoneda>')

    sb.Append('<TotalServGravados>' +
              str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' +
              str(total_servicio_exento) + '</TotalServExentos>')

    # TODO: Hay que calcular TotalServExonerado
    sb.Append('<TotalServExonerado>' + str(totalServExonerado) + '</TotalServExonerado>')

    sb.Append('<TotalMercanciasGravadas>' +
              str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' +
              str(total_mercaderia_exento) + '</TotalMercanciasExentas>')

    # TODO: Hay que calcular TotalMercExonerada
    sb.Append('<TotalMercExonerada>' + str(totalMercExonerada) + '</TotalMercExonerada>')

    sb.Append('<TotalGravado>' + str(total_servicio_gravado +
                                     total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento +
                                    total_mercaderia_exento) + '</TotalExento>')

    # TODO: Hay que calcular TotalExonerado
    sb.Append('<TotalExonerado>' + str(totalServExonerado + totalMercExonerada) + '</TotalExonerado>')

    # TODO: agregar los exonerados en la suma
    sb.Append('<TotalVenta>' + str(
        total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento + totalServExonerado + totalMercExonerada) + '</TotalVenta>')

    sb.Append('<TotalDescuentos>' +
              str(round(total_descuento, 2)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' +
              str(round(base_total, 2)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' +
              str(round(total_impuestos, 2)) + '</TotalImpuesto>')

    # TODO: Hay que calcular el TotalIVADevuelto
    # sb.Append('<TotalIVADevuelto>' + str(¿de dónde sacamos esto?) + '</TotalIVADevuelto>')

    # TODO: Hay que calcular el TotalOtrosCargos
    # sb.Append('<TotalOtrosCargos>' + str(¿de dónde sacamos esto?) + '</TotalOtrosCargos>')

    sb.Append('<TotalComprobante>' + str(round(base_total +
                                               total_impuestos, 2)) + '</TotalComprobante>')
    sb.Append('</ResumenFactura>')
    sb.Append('<Otros>')
    sb.Append('<OtroTexto>' +
              str(invoice_comments or 'Test FE V4.3') + '</OtroTexto>')
    sb.Append('</Otros>')

    sb.Append('</FacturaElectronica>')

    return sb


def gen_xml_fee_v43(inv, consecutivo, date, sale_conditions, total_servicio_gravado, total_servicio_exento, totalServExonerado,
                    total_mercaderia_gravado, total_mercaderia_exento, totalMercExonerada, totalOtrosCargos, base_total, total_impuestos, total_descuento,
                    lines, otrosCargos, currency_rate, invoice_comments):

    numero_linea = 0

    sb = StringBuilder()
    sb.Append('<?xml version="1.0" encoding="utf-8"?>')
    sb.Append('<FacturaElectronica xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronicaExportacion" ')
    sb.Append(
        'xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsd="http://www.w3.org/2001/XMLSchema" ')
    sb.Append('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append('xsi:schemaLocation="https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/FacturaElectronicaExportacion_V4.3.xsd">')

    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<CodigoActividad>' +
              inv.company_id.activity_id.code + '</CodigoActividad>')
    sb.Append('<NumeroConsecutivo>' + consecutivo + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + date + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' +
              escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')
    sb.Append('<Receptor>')
    sb.Append('<Nombre>' + escape(str(inv.partner_id.name[:80])) + '</Nombre>')

    if inv.partner_id.identification_id.code == '05':
        sb.Append('<IdentificacionExtranjero>' +
                  inv.partner_id.vat + '</IdentificacionExtranjero>')
    else:
        sb.Append('<Identificacion>')
        sb.Append('<Tipo>' + inv.partner_id.identification_id.code + '</Tipo>')
        sb.Append('<Numero>' + inv.partner_id.vat + '</Numero>')
        sb.Append('</Identificacion>')

    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' +
              str(inv.partner_id.state_id.code or '') + '</Provincia>')
    sb.Append('<Canton>' + str(inv.partner_id.county_id.code or '') + '</Canton>')
    sb.Append('<Distrito>' +
              str(inv.partner_id.district_id.code or '') + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.partner_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              escape(str(inv.partner_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.partner_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.partner_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.partner_id.email) + '</CorreoElectronico>')
    sb.Append('</Receptor>')
    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.Append('<PlazoCredito>' +
              str(inv.partner_id.property_payment_term_id.line_ids[0].days or 0) + '</PlazoCredito>')
    sb.Append('<MedioPago>' + (inv.payment_methods_id.sequence or '01') + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')

        # TODO: Implementar esto en la interfaz y en la factura
        # sb.Append('<PartidaArancelaria>' +  + '</PartidaArancelaria>')

        sb.Append('<CodigoComercial>' +
                  str(v['codigoProducto']) + '</CodigoComercial>')
        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' +
                  str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' +
                  str(v['precioUnitario']) + '</PrecioUnitario>')
        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
        if v.get('montoDescuento'):
            sb.Append('<MontoDescuento>' +
                      str(v['montoDescuento']) + '</MontoDescuento>')
        if v.get('naturalezaDescuento'):
            sb.Append('<NaturalezaDescuento>' +
                      str(v['naturalezaDescuento']) + '</NaturalezaDescuento>')
        sb.Append('<SubTotal>' + str(v['subtotal']) + '</SubTotal>')

        if v.get('impuesto'):
            for (a, b) in v['impuesto'].items():
                sb.Append('<Impuesto>')
                sb.Append('<Codigo>' + str(b['codigo']) + '</Codigo>')
                sb.Append('<Tarifa>' + str(b['tarifa']) + '</Tarifa>')
                sb.Append('<Monto>' + str(b['monto']) + '</Monto>')

                if b.get('exoneracion'):
                    for (c, d) in b['exoneracion']:
                        sb.Append('<Exoneracion>')
                        sb.Append('<TipoDocumento>' +
                                  d['tipoDocumento'] + '</TipoDocumento>')
                        sb.Append('<NumeroDocumento>' +
                                  d['numeroDocumento'] + '</NumeroDocumento>')
                        sb.Append('<NombreInstitucion>' +
                                  d['nombreInstitucion'] + '</NombreInstitucion>')
                        sb.Append('<FechaEmision>' +
                                  d['fechaEmision'] + '</FechaEmision>')
                        sb.Append('<MontoImpuesto>' +
                                  d['montoImpuesto'] + '</MontoImpuesto>')
                        sb.Append('<PorcentajeCompra>' +
                                  d['porcentajeCompra'] + '</PorcentajeCompra>')

                sb.Append('</Impuesto>')
        sb.Append('<MontoTotalLinea>' +
                  str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')
    sb.Append('</DetalleServicio>')

    # TODO: ¿Cómo implementar otros cargos a nivel de UI y model en Odoo?
    if otrosCargos:
        sb.Append('<OtrosCargos>')
        response_json = json.loads(otrosCargos)
        for (k, v) in response_json.items():
            sb.Append('<TipoDocumento>' +
                      str(v['TipoDocumento']) + '<TipoDocumento>')

            if v.get('NumeroIdentidadTercero'):
                sb.Append('<NumeroIdentidadTercero>' +
                          str(v['NumeroIdentidadTercero']) + '<NumeroIdentidadTercero>')

            if v.get('NombreTercero'):
                sb.Append('<NombreTercero>' +
                          str(v['NombreTercero']) + '<NombreTercero>')

            sb.Append('<Detalle>' + str(v['Detalle']) + '<Detalle>')
            if v.get('Porcentaje'):
                sb.Append('<Porcentaje>' +
                          str(v['Porcentaje']) + '<Porcentaje>')

            sb.Append('<MontoCargo>' + str(v['MontoCargo']) + '<MontoCargo>')
        sb.Append('</OtrosCargos>')

    sb.Append('<ResumenFactura>')
    sb.Append('<CodigoTipoMoneda><CodigoMoneda>' + str(inv.currency_id.name) +
              '</CodigoMoneda><TipoCambio>' + str(currency_rate) + '</TipoCambio></CodigoTipoMoneda>')
    sb.Append('<TotalServGravados>' +
              str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' +
              str(total_servicio_exento) + '</TotalServExentos>')

    sb.Append('<TotalMercanciasGravadas>' +
              str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' +
              str(total_mercaderia_exento) + '</TotalMercanciasExentas>')

    sb.Append('<TotalGravado>' + str(total_servicio_gravado +
                                     total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento +
                                    total_mercaderia_exento) + '</TotalExento>')

    # TODO: Hay que calcular TotalExonerado
    #sb.Append('<TotalExonerado>' + str(totalServExonerado + totalMercExonerada) + '</TotalExonerado>')

    # TODO: agregar los exonerados en la suma
    sb.Append('<TotalVenta>' + str(total_servicio_gravado + total_mercaderia_gravado +
                                   total_servicio_exento + total_mercaderia_exento) + '</TotalVenta>')

    sb.Append('<TotalDescuentos>' +
              str(round(total_descuento, 2)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' +
              str(round(base_total, 2)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' +
              str(round(total_impuestos, 2)) + '</TotalImpuesto>')

    # TODO: Hay que calcular el TotalIVADevuelto
    # sb.Append('<TotalIVADevuelto>' + str(¿de dónde sacamos esto?) + '</TotalIVADevuelto>')

    # TODO: Hay que calcular el TotalOtrosCargos
    # sb.Append('<TotalOtrosCargos>' + str(¿de dónde sacamos esto?) + '</TotalOtrosCargos>')

    sb.Append('<TotalComprobante>' + str(round(base_total +
                                               total_impuestos, 2)) + '</TotalComprobante>')
    sb.Append('</ResumenFactura>')

    sb.Append('<Otros>')
    sb.Append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
    sb.Append('</Otros>')

    sb.Append('</FacturaElectronica>')

    #felectronica_bytes = str(sb)

    #return stringToBase64(felectronica_bytes)
    return sb


def gen_xml_te_42(inv, sale_conditions, total_servicio_gravado, total_servicio_exento,
               total_mercaderia_gravado, total_mercaderia_exento, base_total, total_impuestos, total_descuento,
               lines, currency_rate, invoice_comments):

    numero_linea = 0

    sb = StringBuilder()
    sb.Append('<?xml version="1.0" encoding="utf-8"?>')
    sb.Append('<TiqueteElectronico xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/tiqueteElectronico" ')
    sb.Append(
        'xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsd="http://www.w3.org/2001/XMLSchema" ')
    sb.Append('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append('xsi:schemaLocation="https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.2/TiqueteElectronico_V4.2.xsd">')

    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<NumeroConsecutivo>' + inv.number_electronic[21:41] + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + inv.date_issuance + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' +
              escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')
    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.Append('<PlazoCredito>' +
              str(inv.payment_term_id and inv.payment_term_id.line_ids[0].days or '0') + '</PlazoCredito>')
    sb.Append('<MedioPago>' + (inv.payment_methods_id.sequence or '01') + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')
        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' +
                  str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' +
                  str(v['precioUnitario']) + '</PrecioUnitario>')
        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
        if v.get('montoDescuento'):
            sb.Append('<MontoDescuento>' +
                      str(v['montoDescuento']) + '</MontoDescuento>')
        if v.get('naturalezaDescuento'):
            sb.Append('<NaturalezaDescuento>' +
                      str(v['naturalezaDescuento']) + '</NaturalezaDescuento>')
        sb.Append('<SubTotal>' + str(v['subtotal']) + '</SubTotal>')

        if v.get('impuesto'):
            for (a, b) in v['impuesto'].items():
                sb.Append('<Impuesto>')
                sb.Append('<Codigo>' + str(b['codigo']) + '</Codigo>')
                sb.Append('<CodigoTarifa>' +
                          str(b['iva_tax_code']) + '</CodigoTarifa>')
                sb.Append('<Tarifa>' + str(b['tarifa']) + '</Tarifa>')
                sb.Append('<Monto>' + str(b['monto']) + '</Monto>')

                if b.get('exoneracion'):
                    for (c, d) in b['exoneracion']:
                        sb.Append('<Exoneracion>')
                        sb.Append('<TipoDocumento>' +
                                  d['tipoDocumento'] + '</TipoDocumento>')
                        sb.Append('<NumeroDocumento>' +
                                  d['numeroDocumento'] + '</NumeroDocumento>')
                        sb.Append('<NombreInstitucion>' +
                                  d['nombreInstitucion'] + '</NombreInstitucion>')
                        sb.Append('<FechaEmision>' +
                                  d['fechaEmision'] + '</FechaEmision>')
                        sb.Append('<MontoImpuesto>' +
                                  d['montoImpuesto'] + '</MontoImpuesto>')
                        sb.Append('<PorcentajeCompra>' +
                                  d['porcentajeCompra'] + '</PorcentajeCompra>')

                sb.Append('</Impuesto>')
        sb.Append('<MontoTotalLinea>' +
                  str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')
    sb.Append('</DetalleServicio>')
    sb.Append('<ResumenFactura>')
    sb.Append('<CodigoMoneda>' + str(inv.currency_id.name) + '</CodigoMoneda>')
    sb.Append('<TipoCambio>' + str(currency_rate) + '</TipoCambio>')
    sb.Append('<TotalServGravados>' +
              str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' +
              str(total_servicio_exento) + '</TotalServExentos>')
    sb.Append('<TotalMercanciasGravadas>' +
              str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' +
              str(total_mercaderia_exento) + '</TotalMercanciasExentas>')
    sb.Append('<TotalGravado>' + str(total_servicio_gravado +
                                     total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento +
                                    total_mercaderia_exento) + '</TotalExento>')
    sb.Append('<TotalVenta>' + str(total_servicio_gravado + total_mercaderia_gravado +
                                   total_servicio_exento + total_mercaderia_exento) + '</TotalVenta>')
    sb.Append('<TotalDescuentos>' +
              str(round(total_descuento, 2)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' +
              str(round(base_total, 2)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' +
              str(round(total_impuestos, 2)) + '</TotalImpuesto>')
    sb.Append('<TotalComprobante>' + str(round(base_total +
                                               total_impuestos, 2)) + '</TotalComprobante>')
    sb.Append('</ResumenFactura>')
    sb.Append('<Normativa>')
    sb.Append('<NumeroResolucion>DGT-R-48-2016</NumeroResolucion>')
    sb.Append('<FechaResolucion>07-10-2016 08:00:00</FechaResolucion>')
    sb.Append('</Normativa>')
    sb.Append('<Otros>')
    sb.Append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
    sb.Append('</Otros>')

    sb.Append('</TiqueteElectronico>')

    #telectronico_bytes = str(sb)
    #return stringToBase64(telectronico_bytes)
    return sb

def gen_xml_te_43(inv, sale_conditions, total_servicio_gravado, total_servicio_exento,
               total_mercaderia_gravado, total_mercaderia_exento, base_total, total_impuestos, total_descuento,
               lines, currency_rate, invoice_comments, otrosCargos):

    numero_linea = 0

    sb = StringBuilder()
    sb.Append('<TiqueteElectronico xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/tiqueteElectronico" ')
    sb.Append(
        'xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsd="http://www.w3.org/2001/XMLSchema" ')
    sb.Append('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append('xsi:schemaLocation="https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/TiqueteElectronico_V4.3.xsd">')

    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<CodigoActividad>' +
              inv.company_id.activity_id.code + '</CodigoActividad>')
    sb.Append('<NumeroConsecutivo>' + inv.number_electronic[21:41] + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + get_time_hacienda() + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' +
              escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')
    
    sb.Append('<Receptor>')
    sb.Append('<Nombre>' + escape(str(inv.partner_id.name[:80])) + '</Nombre>')
    sb.Append('</Receptor>')

    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')

    sb.Append('<MedioPago>' + (inv.payment_methods_id.sequence or '01') + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')

        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' +
                  str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' +
                  str(v['precioUnitario']) + '</PrecioUnitario>')
        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
        if v.get('montoDescuento'):
            sb.Append('<MontoDescuento>' +
                      str(v['montoDescuento']) + '</MontoDescuento>')
        if v.get('naturalezaDescuento'):
            sb.Append('<NaturalezaDescuento>' +
                      str(v['naturalezaDescuento']) + '</NaturalezaDescuento>')
        sb.Append('<SubTotal>' + str(v['subtotal']) + '</SubTotal>')

        if v.get('impuesto'):
            for (a, b) in v['impuesto'].items():
                sb.Append('<Impuesto>')
                sb.Append('<Codigo>' + str(b['codigo']) + '</Codigo>')
                sb.Append('<Tarifa>' + str(b['tarifa']) + '</Tarifa>')
                sb.Append('<Monto>' + str(b['monto']) + '</Monto>')

                if b.get('exoneracion'):
                    for (c, d) in b['exoneracion']:
                        sb.Append('<Exoneracion>')
                        sb.Append('<TipoDocumento>' +
                                  d['tipoDocumento'] + '</TipoDocumento>')
                        sb.Append('<NumeroDocumento>' +
                                  d['numeroDocumento'] + '</NumeroDocumento>')
                        sb.Append('<NombreInstitucion>' +
                                  d['nombreInstitucion'] + '</NombreInstitucion>')
                        sb.Append('<FechaEmision>' +
                                  d['fechaEmision'] + '</FechaEmision>')
                        sb.Append('<MontoImpuesto>' +
                                  d['montoImpuesto'] + '</MontoImpuesto>')
                        sb.Append('<PorcentajeCompra>' +
                                  d['porcentajeCompra'] + '</PorcentajeCompra>')

                sb.Append('</Impuesto>')
        sb.Append('<MontoTotalLinea>' +
                  str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')
    sb.Append('</DetalleServicio>')

    # TODO: ¿Cómo implementar otros cargos a nivel de UI y model en Odoo?
    if otrosCargos:
        sb.Append('<OtrosCargos>')
        response_json = json.loads(otrosCargos)
        for (k, v) in response_json.items():
            sb.Append('<TipoDocumento>' +
                      str(v['TipoDocumento']) + '<TipoDocumento>')

            if v.get('NumeroIdentidadTercero'):
                sb.Append('<NumeroIdentidadTercero>' +
                          str(v['NumeroIdentidadTercero']) + '<NumeroIdentidadTercero>')

            if v.get('NombreTercero'):
                sb.Append('<NombreTercero>' +
                          str(v['NombreTercero']) + '<NombreTercero>')

            sb.Append('<Detalle>' + str(v['Detalle']) + '<Detalle>')
            if v.get('Porcentaje'):
                sb.Append('<Porcentaje>' +
                          str(v['Porcentaje']) + '<Porcentaje>')

            sb.Append('<MontoCargo>' + str(v['MontoCargo']) + '<MontoCargo>')
        sb.Append('</OtrosCargos>')

    sb.Append('<ResumenFactura>')
    sb.Append('<CodigoTipoMoneda><CodigoMoneda>' + str(inv.currency_id.name) +
              '</CodigoMoneda><TipoCambio>' + str(currency_rate) + '</TipoCambio></CodigoTipoMoneda>')
    sb.Append('<TotalServGravados>' +
              str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' +
              str(total_servicio_exento) + '</TotalServExentos>')

    sb.Append('<TotalMercanciasGravadas>' +
              str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' +
              str(total_mercaderia_exento) + '</TotalMercanciasExentas>')

    sb.Append('<TotalGravado>' + str(total_servicio_gravado +
                                     total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento +
                                    total_mercaderia_exento) + '</TotalExento>')

    # TODO: Hay que calcular TotalExonerado
    #sb.Append('<TotalExonerado>' + str(totalServExonerado + totalMercExonerada) + '</TotalExonerado>')

    # TODO: agregar los exonerados en la suma
    sb.Append('<TotalVenta>' + str(total_servicio_gravado + total_mercaderia_gravado +
                                   total_servicio_exento + total_mercaderia_exento) + '</TotalVenta>')

    sb.Append('<TotalDescuentos>' +
              str(round(total_descuento, 2)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' +
              str(round(base_total, 2)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' +
              str(round(total_impuestos, 2)) + '</TotalImpuesto>')

    # TODO: Hay que calcular el TotalIVADevuelto
    # sb.Append('<TotalIVADevuelto>' + str(¿de dónde sacamos esto?) + '</TotalIVADevuelto>')

    # TODO: Hay que calcular el TotalOtrosCargos
    # sb.Append('<TotalOtrosCargos>' + str(¿de dónde sacamos esto?) + '</TotalOtrosCargos>')

    sb.Append('<TotalComprobante>' + str(round(base_total +
                                               total_impuestos, 2)) + '</TotalComprobante>')
    sb.Append('</ResumenFactura>')

    sb.Append('<Otros>')
    sb.Append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
    sb.Append('</Otros>')

    sb.Append('</TiqueteElectronico>')

    #telectronico_bytes = str(sb)
    #return stringToBase64(telectronico_bytes)
    return sb


def gen_xml_nc_v43(
    inv, sale_conditions, total_servicio_gravado,
    total_servicio_exento, total_mercaderia_gravado, total_mercaderia_exento, base_total,
    total_impuestos, total_descuento, lines,
    tipo_documento_referencia, numero_documento_referencia, fecha_emision_referencia,
    codigo_referencia, razon_referencia, currency_rate, invoice_comments
):

    numero_linea = 0

    sb = StringBuilder()

    sb.Append('<NotaCreditoElectronica xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/notaCreditoElectronica" ')
    sb.Append('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append('xsi:schemaLocation="https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/NotaCreditoElectronica_V4.3.xsd">')
    # sb.Append('https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3">')

    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<CodigoActividad>' +
              inv.company_id.activity_id.code + '</CodigoActividad>')
    sb.Append('<NumeroConsecutivo>' + inv.number_electronic[21:41] + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + inv.date_issuance + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' +
              escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')
    sb.Append('<Receptor>')
    sb.Append('<Nombre>' + escape(str(inv.partner_id.name[:80])) + '</Nombre>')

    if inv.partner_id.identification_id.code == '05':
        sb.Append('<IdentificacionExtranjero>' +
                  inv.partner_id.vat + '</IdentificacionExtranjero>')
    else:
        sb.Append('<Identificacion>')
        sb.Append('<Tipo>' + inv.partner_id.identification_id.code + '</Tipo>')
        sb.Append('<Numero>' + inv.partner_id.vat + '</Numero>')
        sb.Append('</Identificacion>')

    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' +
              str(inv.partner_id.state_id.code or '') + '</Provincia>')
    sb.Append('<Canton>' + str(inv.partner_id.county_id.code or '') + '</Canton>')
    sb.Append('<Distrito>' +
              str(inv.partner_id.district_id.code or '') + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.partner_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              str(inv.partner_id.street or 'NA') + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.partner_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.partner_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.partner_id.email) + '</CorreoElectronico>')
    sb.Append('</Receptor>')
    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.Append('<PlazoCredito>' +
              str(inv.partner_id.property_payment_term_id.line_ids[0].days or 0) + '</PlazoCredito>')
    sb.Append('<MedioPago>' + (inv.payment_methods_id.sequence or '01') + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')
        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' +
                  str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' +
                  str(v['precioUnitario']) + '</PrecioUnitario>')

        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
        if v.get('montoDescuento'):
            sb.Append('<MontoDescuento>' +
                      str(v['montoDescuento']) + '</MontoDescuento>')
        if v.get('naturalezaDescuento'):
            sb.Append('<NaturalezaDescuento>' +
                      str(v['naturalezaDescuento']) + '</NaturalezaDescuento>')
        sb.Append('<SubTotal>' + str(v['subtotal']) + '</SubTotal>')
        sb.Append('<BaseImponible>' + str(v['subtotal']) + '</BaseImponible>')

        if v.get('impuesto'):
            for (a, b) in v['impuesto'].items():
                sb.Append('<Impuesto>')
                sb.Append('<Codigo>' + str(b['codigo']) + '</Codigo>')
                sb.Append('<CodigoTarifa>' +
                          str(b['iva_tax_code']) + '</CodigoTarifa>')
                sb.Append('<Tarifa>' + str(b['tarifa']) + '</Tarifa>')
                sb.Append('<Monto>' + str(b['monto']) + '</Monto>')

                if b.get('exoneracion'):
                    for (c, d) in b['exoneracion']:
                        sb.Append('<Exoneracion>')
                        sb.Append('<TipoDocumento>' +
                                  d['tipoDocumento'] + '</TipoDocumento>')
                        sb.Append('<NumeroDocumento>' +
                                  d['numeroDocumento'] + '</NumeroDocumento>')
                        sb.Append('<NombreInstitucion>' +
                                  d['nombreInstitucion'] + '</NombreInstitucion>')
                        sb.Append('<FechaEmision>' +
                                  d['fechaEmision'] + '</FechaEmision>')
                        sb.Append('<MontoImpuesto>' +
                                  str(d['montoImpuesto']) + '</MontoImpuesto>')
                        sb.Append(
                            '<PorcentajeCompra>' + str(d['porcentajeCompra']) + '</PorcentajeCompra>')

                sb.Append('</Impuesto>')
        sb.Append('<MontoTotalLinea>' +
                  str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')
    sb.Append('</DetalleServicio>')

    sb.Append('<ResumenFactura>')
    #sb.Append('<CodigoMoneda>' + str(inv.currency_id.name) + '</CodigoMoneda>')
    #sb.Append('<TipoCambio>' + str(currency_rate) + '</TipoCambio>')

    sb.Append('<CodigoTipoMoneda><CodigoMoneda>' + str(inv.currency_id.name) + '</CodigoMoneda><TipoCambio>' + str(
        currency_rate) + '</TipoCambio></CodigoTipoMoneda>')

    sb.Append('<TotalServGravados>' +
              str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' +
              str(total_servicio_exento) + '</TotalServExentos>')

    # TODO: Hay que calcular TotalServExonerado
    # sb.Append('<TotalServExonerado>' + str(totalServExonerado) + '</TotalServExonerado>')

    sb.Append('<TotalMercanciasGravadas>' +
              str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' +
              str(total_mercaderia_exento) + '</TotalMercanciasExentas>')

    # TODO: Hay que calcular TotalMercExonerada
    # sb.Append('<TotalMercExonerada>' + str(totalMercExonerada) + '</TotalMercExonerada>')

    sb.Append('<TotalGravado>' + str(total_servicio_gravado +
                                     total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento +
                                    total_mercaderia_exento) + '</TotalExento>')

    # TODO: Hay que calcular TotalExonerado
    # sb.Append('<TotalExonerado>' + str(totalServExonerado + totalMercExonerada) + '</TotalExonerado>')

    sb.Append('<TotalVenta>' + str(
        total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento) + '</TotalVenta>')
    sb.Append('<TotalDescuentos>' +
              str(round(total_descuento, 2)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' +
              str(round(base_total, 2)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' +
              str(round(total_impuestos, 2)) + '</TotalImpuesto>')

    # TODO: Hay que calcular el TotalIVADevuelto
    # sb.Append('<TotalIVADevuelto>' + str(¿de dónde sacamos esto?) + '</TotalIVADevuelto>')

    # TODO: Hay que calcular el TotalOtrosCargos
    # sb.Append('<TotalOtrosCargos>' + str(¿de dónde sacamos esto?) + '</TotalOtrosCargos>')

    sb.Append('<TotalComprobante>' + str(round(base_total +
                                               total_impuestos, 2)) + '</TotalComprobante>')
    sb.Append('</ResumenFactura>')

    sb.Append('<InformacionReferencia>')
    sb.Append('<TipoDoc>' + str(tipo_documento_referencia) + '</TipoDoc>')
    sb.Append('<Numero>' + str(numero_documento_referencia) + '</Numero>')
    sb.Append('<FechaEmision>' + fecha_emision_referencia + '</FechaEmision>')
    sb.Append('<Codigo>' + str(codigo_referencia) + '</Codigo>')
    sb.Append('<Razon>' + str(razon_referencia) + '</Razon>')
    sb.Append('</InformacionReferencia>')
    # sb.Append('<Normativa>')
    # sb.Append('<NumeroResolucion>DGT-R-48-2016</NumeroResolucion>')
    #sb.Append('<FechaResolucion>07-10-2016 08:00:00</FechaResolucion>')
    # sb.Append('</Normativa>')
    if invoice_comments:
        sb.Append('<Otros>')
        sb.Append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
        sb.Append('</Otros>')
    sb.Append('</NotaCreditoElectronica>')

    return sb


def gen_xml_nc(
    inv, sale_conditions, total_servicio_gravado,
    total_servicio_exento, total_mercaderia_gravado, total_mercaderia_exento, base_total,
    total_impuestos, total_descuento, lines,
    tipo_documento_referencia, numero_documento_referencia, fecha_emision_referencia,
    codigo_referencia, razon_referencia, currency_rate, invoice_comments
):

    numero_linea = 0

    sb = StringBuilder()

    sb.Append(
        '<NotaCreditoElectronica xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append(
        'xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2019/v4.2/notaCreditoElectronica" ')
    sb.Append('xsi:schemaLocation="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/notaCreditoElectronica ')
    sb.Append(
        'https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/NotaCreditoElectronica_V4.2.xsd">')
    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<NumeroConsecutivo>' + inv.number_electronic[21:41] + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + inv.date_issuance + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' +
              escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')
    sb.Append('<Receptor>')
    sb.Append('<Nombre>' + escape(str(inv.partner_id.name[:80])) + '</Nombre>')

    if inv.partner_id.identification_id.code == '05':
        sb.Append('<IdentificacionExtranjero>' +
                  inv.partner_id.vat + '</IdentificacionExtranjero>')
    else:
        sb.Append('<Identificacion>')
        sb.Append('<Tipo>' + inv.partner_id.identification_id.code + '</Tipo>')
        sb.Append('<Numero>' + inv.partner_id.vat + '</Numero>')
        sb.Append('</Identificacion>')

    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' +
              str(inv.partner_id.state_id.code or '') + '</Provincia>')
    sb.Append('<Canton>' + str(inv.partner_id.county_id.code or '') + '</Canton>')
    sb.Append('<Distrito>' +
              str(inv.partner_id.district_id.code or '') + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.partner_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              str(inv.partner_id.street or 'NA') + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.partner_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.partner_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.partner_id.email) + '</CorreoElectronico>')
    sb.Append('</Receptor>')
    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.Append('<PlazoCredito>' +
              str(inv.partner_id.property_payment_term_id.line_ids[0].days or 0) + '</PlazoCredito>')
    sb.Append('<MedioPago>' + (inv.payment_methods_id.sequence or '01') + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')
        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' +
                  str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' +
                  str(v['precioUnitario']) + '</PrecioUnitario>')

        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
        if v.get('montoDescuento'):
            sb.Append('<MontoDescuento>' +
                      str(v['montoDescuento']) + '</MontoDescuento>')
        if v.get('naturalezaDescuento'):
            sb.Append('<NaturalezaDescuento>' +
                      str(v['naturalezaDescuento']) + '</NaturalezaDescuento>')
        sb.Append('<SubTotal>' + str(v['subtotal']) + '</SubTotal>')

        if v.get('impuesto'):
            for (a, b) in v['impuesto'].items():
                sb.Append('<Impuesto>')
                sb.Append('<Codigo>' + str(b['codigo']) + '</Codigo>')
                sb.Append('<Tarifa>' + str(b['tarifa']) + '</Tarifa>')
                sb.Append('<Monto>' + str(b['monto']) + '</Monto>')

                if b.get('exoneracion'):
                    for (c, d) in b['exoneracion']:
                        sb.Append('<Exoneracion>')
                        sb.Append('<TipoDocumento>' +
                                  d['tipoDocumento'] + '</TipoDocumento>')
                        sb.Append('<NumeroDocumento>' +
                                  d['numeroDocumento'] + '</NumeroDocumento>')
                        sb.Append('<NombreInstitucion>' +
                                  d['nombreInstitucion'] + '</NombreInstitucion>')
                        sb.Append('<FechaEmision>' +
                                  d['fechaEmision'] + '</FechaEmision>')
                        sb.Append('<MontoImpuesto>' +
                                  str(d['montoImpuesto']) + '</MontoImpuesto>')
                        sb.Append(
                            '<PorcentajeCompra>' + str(d['porcentajeCompra']) + '</PorcentajeCompra>')

                sb.Append('</Impuesto>')
        sb.Append('<MontoTotalLinea>' +
                  str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')
    sb.Append('</DetalleServicio>')
    sb.Append('<ResumenFactura>')
    sb.Append('<CodigoMoneda>' + str(inv.currency_id.name) + '</CodigoMoneda>')
    sb.Append('<TipoCambio>' + str(currency_rate) + '</TipoCambio>')
    sb.Append('<TotalServGravados>' +
              str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' +
              str(total_servicio_exento) + '</TotalServExentos>')
    sb.Append('<TotalMercanciasGravadas>' +
              str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' +
              str(total_mercaderia_exento) + '</TotalMercanciasExentas>')
    sb.Append('<TotalGravado>' + str(total_servicio_gravado +
                                     total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento +
                                    total_mercaderia_exento) + '</TotalExento>')
    sb.Append('<TotalVenta>' + str(
        total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento) + '</TotalVenta>')
    sb.Append('<TotalDescuentos>' +
              str(round(total_descuento, 2)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' +
              str(round(base_total, 2)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' +
              str(round(total_impuestos, 2)) + '</TotalImpuesto>')
    sb.Append('<TotalComprobante>' + str(round(base_total +
                                               total_impuestos, 2)) + '</TotalComprobante>')
    sb.Append('</ResumenFactura>')
    sb.Append('<InformacionReferencia>')
    sb.Append('<TipoDoc>' + str(tipo_documento_referencia) + '</TipoDoc>')
    sb.Append('<Numero>' + str(numero_documento_referencia) + '</Numero>')
    sb.Append('<FechaEmision>' + fecha_emision_referencia + '</FechaEmision>')
    sb.Append('<Codigo>' + str(codigo_referencia) + '</Codigo>')
    sb.Append('<Razon>' + str(razon_referencia) + '</Razon>')
    sb.Append('</InformacionReferencia>')
    sb.Append('<Normativa>')
    sb.Append('<NumeroResolucion>DGT-R-48-2016</NumeroResolucion>')
    sb.Append('<FechaResolucion>07-10-2016 08:00:00</FechaResolucion>')
    sb.Append('</Normativa>')
    if invoice_comments:
        sb.Append('<Otros>')
        sb.Append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
        sb.Append('</Otros>')
    sb.Append('</NotaCreditoElectronica>')

    return sb
    #ncelectronica_bytes = str(sb)

    # return stringToBase64(ncelectronica_bytes)


def gen_xml_nd(
    inv, consecutivo, date, sale_conditions, total_servicio_gravado,
    total_servicio_exento, total_mercaderia_gravado, total_mercaderia_exento, base_total,
    total_impuestos, total_descuento, lines,
    tipo_documento_referencia, numero_documento_referencia, fecha_emision_referencia,
    codigo_referencia, razon_referencia, currency_rate, invoice_comments
):
    numero_linea = 0

    sb = StringBuilder()
    sb.Append(
        '<NotaDebitoElectronica xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append(
        'xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/notaDebitoElectronica" ')
    sb.Append('xsi:schemaLocation="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/notaCreditoElectronica ')
    sb.Append(
        'https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/NotaCreditoElectronica_V4.2.xsd">')
    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<NumeroConsecutivo>' + consecutivo + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + date + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' +
              escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')
    sb.Append('<Receptor>')
    sb.Append('<Nombre>' + escape(str(inv.partner_id.name[:80])) + '</Nombre>')

    if inv.partner_id.identification_id.code == '05':
        sb.Append('<IdentificacionExtranjero>' +
                  inv.partner_id.vat + '</IdentificacionExtranjero>')
    else:
        sb.Append('<Identificacion>')
        sb.Append('<Tipo>' + inv.partner_id.identification_id.code + '</Tipo>')
        sb.Append('<Numero>' + inv.partner_id.vat + '</Numero>')
        sb.Append('</Identificacion>')

    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' +
              str(inv.partner_id.state_id.code or '') + '</Provincia>')
    sb.Append('<Canton>' + str(inv.partner_id.county_id.code or '') + '</Canton>')
    sb.Append('<Distrito>' +
              str(inv.partner_id.district_id.code or '') + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.partner_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              str(inv.partner_id.street or 'NA') + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.partner_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.partner_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.partner_id.email) + '</CorreoElectronico>')
    sb.Append('</Receptor>')
    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.Append('<PlazoCredito>' +
              str(inv.partner_id.property_payment_term_id.line_ids[0].days or 0) + '</PlazoCredito>')
    sb.Append('<MedioPago>' + (inv.payment_methods_id.sequence or '01') + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')
        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' +
                  str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' +
                  str(v['precioUnitario']) + '</PrecioUnitario>')
        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
        if v.get('montoDescuento'):
            sb.Append('<MontoDescuento>' +
                      str(v['montoDescuento']) + '</MontoDescuento>')
        if v.get('naturalezaDescuento'):
            sb.Append('<NaturalezaDescuento>' +
                      v['naturalezaDescuento'] + '</NaturalezaDescuento>')
        sb.Append('<SubTotal>' + str(v['subtotal']) + '</SubTotal>')

        if v.get('impuesto'):
            for (a, b) in v['impuesto'].items():
                sb.Append('<Impuesto>')
                sb.Append('<Codigo>' + str(b['codigo']) + '</Codigo>')
                sb.Append('<Tarifa>' + str(b['tarifa']) + '</Tarifa>')
                sb.Append('<Monto>' + str(b['monto']) + '</Monto>')

                if b.get('exoneracion'):
                    for (c, d) in b['exoneracion']:
                        sb.Append('<Exoneracion>')
                        sb.Append('<TipoDocumento>' +
                                  d['tipoDocumento'] + '</TipoDocumento>')
                        sb.Append('<NumeroDocumento>' +
                                  d['numeroDocumento'] + '</NumeroDocumento>')
                        sb.Append('<NombreInstitucion>' +
                                  d['nombreInstitucion'] + '</NombreInstitucion>')
                        sb.Append('<FechaEmision>' +
                                  d['fechaEmision'] + '</FechaEmision>')
                        sb.Append('<MontoImpuesto>' +
                                  str(d['montoImpuesto']) + '</MontoImpuesto>')
                        sb.Append(
                            '<PorcentajeCompra>' + str(d['porcentajeCompra']) + '</PorcentajeCompra>')

                sb.Append('</Impuesto>')
        sb.Append('<MontoTotalLinea>' +
                  str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')

    sb.Append('</DetalleServicio>')
    sb.Append('<ResumenFactura>')
    sb.Append('<CodigoMoneda>' + str(inv.currency_id.name) + '</CodigoMoneda>')
    sb.Append('<TipoCambio>' + str(currency_rate) + '</TipoCambio>')
    sb.Append('<TotalServGravados>' +
              str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' +
              str(total_servicio_exento) + '</TotalServExentos>')
    sb.Append('<TotalMercanciasGravadas>' +
              str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' +
              str(total_mercaderia_exento) + '</TotalMercanciasExentas>')
    sb.Append('<TotalGravado>' + str(total_servicio_gravado +
                                     total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento +
                                    total_mercaderia_exento) + '</TotalExento>')
    sb.Append('<TotalVenta>' + str(
        total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento) + '</TotalVenta>')
    sb.Append('<TotalDescuentos>' +
              str(round(total_descuento, 2)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' +
              str(round(base_total, 2)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' +
              str(round(total_impuestos, 2)) + '</TotalImpuesto>')
    sb.Append('<TotalComprobante>' + str(round(base_total +
                                               total_impuestos, 2)) + '</TotalComprobante>')
    sb.Append('</ResumenFactura>')
    sb.Append('<InformacionReferencia>')
    sb.Append('<TipoDoc>' + str(tipo_documento_referencia) + '</TipoDoc>')
    sb.Append('<Numero>' + str(numero_documento_referencia) + '</Numero>')
    sb.Append('<FechaEmision>' + fecha_emision_referencia + '</FechaEmision>')
    sb.Append('<Codigo>' + str(codigo_referencia) + '</Codigo>')
    sb.Append('<Razon>' + str(razon_referencia) + '</Razon>')
    sb.Append('</InformacionReferencia>')
    sb.Append('<Normativa>')
    sb.Append('<NumeroResolucion>DGT-R-48-2016</NumeroResolucion>')
    sb.Append('<FechaResolucion>07-10-2016 08:00:00</FechaResolucion>')
    sb.Append('</Normativa>')
    if invoice_comments:
        sb.Append('<Otros>')
        sb.Append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
        sb.Append('</Otros>')
    sb.Append('</NotaDebitoElectronica>')

    return sb
    #ncelectronica_bytes = str(sb)

    # return stringToBase64(ncelectronica_bytes)


def gen_xml_nd_v43(
    inv, consecutivo, date, sale_conditions, total_servicio_gravado,
    total_servicio_exento, total_mercaderia_gravado, total_mercaderia_exento, base_total,
    total_impuestos, total_descuento, lines,
    tipo_documento_referencia, numero_documento_referencia, fecha_emision_referencia,
    codigo_referencia, razon_referencia, currency_rate, invoice_comments
):
    numero_linea = 0

    sb = StringBuilder()
    sb.Append(
        '<NotaDebitoElectronica xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/notaDebitoElectronica" ')
    sb.Append('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append(
        'xsi:schemaLocation="https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/NotaDebitoElectronica_V4.3.xsd">')

    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<CodigoActividad>' +
              inv.company_id.activity_id.code + '</CodigoActividad>')
    sb.Append('<NumeroConsecutivo>' + consecutivo + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + date + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' +
              escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')
    sb.Append('<Receptor>')
    sb.Append('<Nombre>' + escape(str(inv.partner_id.name[:80])) + '</Nombre>')

    if inv.partner_id.identification_id.code == '05':
        sb.Append('<IdentificacionExtranjero>' +
                  inv.partner_id.vat + '</IdentificacionExtranjero>')
    else:
        sb.Append('<Identificacion>')
        sb.Append('<Tipo>' + inv.partner_id.identification_id.code + '</Tipo>')
        sb.Append('<Numero>' + inv.partner_id.vat + '</Numero>')
        sb.Append('</Identificacion>')

    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' +
              str(inv.partner_id.state_id.code or '') + '</Provincia>')
    sb.Append('<Canton>' + str(inv.partner_id.county_id.code or '') + '</Canton>')
    sb.Append('<Distrito>' +
              str(inv.partner_id.district_id.code or '') + '</Distrito>')
    sb.Append(
        '<Barrio>' + str(inv.partner_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' +
              str(inv.partner_id.street or 'NA') + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.partner_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' +
              re.sub('[^0-9]+', '', inv.partner_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' +
              str(inv.partner_id.email) + '</CorreoElectronico>')
    sb.Append('</Receptor>')
    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.Append('<PlazoCredito>' +
              str(inv.partner_id.property_payment_term_id.line_ids[0].days or 0) + '</PlazoCredito>')
    sb.Append('<MedioPago>' + (inv.payment_methods_id.sequence or '01') + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')
        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' +
                  str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' +
                  str(v['precioUnitario']) + '</PrecioUnitario>')
        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')

        if v.get('montoDescuento'):
            sb.Append('<MontoDescuento>' +
                      str(v['montoDescuento']) + '</MontoDescuento>')
        if v.get('naturalezaDescuento'):
            sb.Append('<NaturalezaDescuento>' +
                      str(v['naturalezaDescuento']) + '</NaturalezaDescuento>')
        sb.Append('<SubTotal>' + str(v['subtotal']) + '</SubTotal>')
        sb.Append('<BaseImponible>' + str(v['subtotal']) + '</BaseImponible>')

        if v.get('impuesto'):
            for (a, b) in v['impuesto'].items():
                sb.Append('<Impuesto>')
                sb.Append('<Codigo>' + str(b['codigo']) + '</Codigo>')
                sb.Append('<CodigoTarifa>' +
                          str(b['iva_tax_code']) + '</CodigoTarifa>')
                sb.Append('<Tarifa>' + str(b['tarifa']) + '</Tarifa>')
                sb.Append('<Monto>' + str(b['monto']) + '</Monto>')

                if b.get('exoneracion'):
                    for (c, d) in b['exoneracion']:
                        sb.Append('<Exoneracion>')
                        sb.Append('<TipoDocumento>' +
                                  d['tipoDocumento'] + '</TipoDocumento>')
                        sb.Append('<NumeroDocumento>' +
                                  d['numeroDocumento'] + '</NumeroDocumento>')
                        sb.Append('<NombreInstitucion>' +
                                  d['nombreInstitucion'] + '</NombreInstitucion>')
                        sb.Append('<FechaEmision>' +
                                  d['fechaEmision'] + '</FechaEmision>')
                        sb.Append('<MontoImpuesto>' +
                                  str(d['montoImpuesto']) + '</MontoImpuesto>')
                        sb.Append(
                            '<PorcentajeCompra>' + str(d['porcentajeCompra']) + '</PorcentajeCompra>')

                sb.Append('</Impuesto>')
        sb.Append('<MontoTotalLinea>' +
                  str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')

    sb.Append('</DetalleServicio>')

    sb.Append('<ResumenFactura>')
    # sb.Append('<CodigoMoneda>' + str(inv.currency_id.name) + '</CodigoMoneda>')
    # sb.Append('<TipoCambio>' + str(currency_rate) + '</TipoCambio>')

    sb.Append('<CodigoTipoMoneda><CodigoMoneda>' + str(inv.currency_id.name) + '</CodigoMoneda><TipoCambio>' + str(
        currency_rate) + '</TipoCambio></CodigoTipoMoneda>')

    sb.Append('<TotalServGravados>' +
              str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' +
              str(total_servicio_exento) + '</TotalServExentos>')

    # TODO: Hay que calcular TotalServExonerado
    # sb.Append('<TotalServExonerado>' + str(totalServExonerado) + '</TotalServExonerado>')

    sb.Append('<TotalMercanciasGravadas>' +
              str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' +
              str(total_mercaderia_exento) + '</TotalMercanciasExentas>')

    # TODO: Hay que calcular TotalMercExonerada
    # sb.Append('<TotalMercExonerada>' + str(totalMercExonerada) + '</TotalMercExonerada>')

    sb.Append('<TotalGravado>' + str(total_servicio_gravado +
                                     total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento +
                                    total_mercaderia_exento) + '</TotalExento>')

    # TODO: Hay que calcular TotalExonerado
    # sb.Append('<TotalExonerado>' + str(totalServExonerado + totalMercExonerada) + '</TotalExonerado>')

    sb.Append('<TotalVenta>' + str(
        total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento) + '</TotalVenta>')
    sb.Append('<TotalDescuentos>' +
              str(round(total_descuento, 2)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' +
              str(round(base_total, 2)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' +
              str(round(total_impuestos, 2)) + '</TotalImpuesto>')

    # TODO: Hay que calcular el TotalIVADevuelto
    # sb.Append('<TotalIVADevuelto>' + str(¿de dónde sacamos esto?) + '</TotalIVADevuelto>')

    # TODO: Hay que calcular el TotalOtrosCargos
    # sb.Append('<TotalOtrosCargos>' + str(¿de dónde sacamos esto?) + '</TotalOtrosCargos>')

    sb.Append('<TotalComprobante>' + str(round(base_total +
                                               total_impuestos, 2)) + '</TotalComprobante>')
    sb.Append('</ResumenFactura>')

    sb.Append('<InformacionReferencia>')
    sb.Append('<TipoDoc>' + str(tipo_documento_referencia) + '</TipoDoc>')
    sb.Append('<Numero>' + str(numero_documento_referencia) + '</Numero>')
    sb.Append('<FechaEmision>' + fecha_emision_referencia + '</FechaEmision>')
    sb.Append('<Codigo>' + str(codigo_referencia) + '</Codigo>')
    sb.Append('<Razon>' + str(razon_referencia) + '</Razon>')
    sb.Append('</InformacionReferencia>')
    if invoice_comments:
        sb.Append('<Otros>')
        sb.Append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
        sb.Append('</Otros>')

    sb.Append('</NotaDebitoElectronica>')

    return sb


# Funcion para enviar el XML al Ministerio de Hacienda
def send_xml_fe(inv, token, date, xml, tipo_ambiente):
    headers = {'Authorization': 'Bearer ' +
               token, 'Content-type': 'application/json'}

    # establecer el ambiente al cual me voy a conectar
    endpoint = fe_enums.UrlHaciendaRecepcion[tipo_ambiente]

    xml_base64 = stringToBase64(xml)

    data = {'clave': inv.number_electronic,
            'fecha': date,
            'emisor': {
                'tipoIdentificacion': inv.company_id.identification_id.code,
                'numeroIdentificacion': inv.company_id.vat
            },
            'receptor': {
                'tipoIdentificacion': inv.partner_id.identification_id.code,
                'numeroIdentificacion': inv.partner_id.vat
            },
            'comprobanteXml': xml_base64
            }

    json_hacienda = json.dumps(data)

    try:
        #  enviando solicitud post y guardando la respuesta como un objeto json
        response = requests.request(
            "POST", endpoint, data=json_hacienda, headers=headers)

        # Verificamos el codigo devuelto, si es distinto de 202 es porque hacienda nos está devolviendo algun error
        if response.status_code != 202:
            error_caused_by = response.headers.get(
                'X-Error-Cause') if 'X-Error-Cause' in response.headers else ''
            error_caused_by += response.headers.get('validation-exception', '')
            _logger.info('Status: {}, Text {}'.format(
                response.status_code, error_caused_by))

            return {'status': response.status_code, 'text': error_caused_by}
        else:
            # respuesta_hacienda = response.status_code
            return {'status': response.status_code, 'text': response.reason}
            # return respuesta_hacienda

    except ImportError:
        raise Warning('Error enviando el XML al Ministerior de Hacienda')


def schema_validator(xml_file, xsd_file) -> bool:
    """
    verifies a xml
    :param xml_invoice: Invoice xml
    :param  xsd_file: XSD File Name
    :return:
    """

    xmlschema = etree.XMLSchema(etree.parse(os.path.join(
        os.path.dirname(__file__), "xsd/" + xsd_file
    )))

    xml_doc = base64decode(xml_file)
    root = etree.fromstring(xml_doc, etree.XMLParser(remove_blank_text=True))
    result = xmlschema.validate(root)

    return result


# Obtener Attachments para las Facturas Electrónicas
def get_invoice_attachments(invoice, record_id):

    attachments = []

    attachment = invoice.env['ir.attachment'].search(
        [('res_model', '=', 'account.invoice'), ('res_id', '=', record_id),
         ('res_field', '=', 'xml_comprobante')], limit=1)

    if attachment.id:
        attachment.name = invoice.fname_xml_comprobante
        attachment.datas_fname = invoice.fname_xml_comprobante
        attachments.append(attachment.id)

    attachment_resp = invoice.env['ir.attachment'].search(
        [('res_model', '=', 'account.invoice'), ('res_id', '=', record_id),
         ('res_field', '=', 'xml_respuesta_tributacion')], limit=1)

    if attachment_resp.id:
        attachment_resp.name = invoice.fname_xml_respuesta_tributacion
        attachment_resp.datas_fname = invoice.fname_xml_respuesta_tributacion
        attachments.append(attachment_resp.id)

    return attachments


def parse_xml(name):
    return etree.parse(name).getroot()


# CONVIERTE UN STRING A BASE 64
def stringToBase64(s):
    return base64.b64encode(s).decode()


# TOMA UNA CADENA Y ELIMINA LOS CARACTERES AL INICIO Y AL FINAL
def stringStrip(s, start, end):
    return s[start:-end]


# Tomamos el XML y le hacemos el decode de base 64, esto por ahora es solo para probar
# la posible implementacion de la firma en python
def base64decode(string_decode):
    return base64.b64decode(string_decode)


# TOMA UNA CADENA EN BASE64 Y LA DECODIFICA PARA ELIMINAR EL b' Y DEJAR EL STRING CODIFICADO
# DE OTRA MANERA HACIENDA LO RECHAZA
def base64UTF8Decoder(s):
    return s.decode("utf-8")


# CLASE PERSONALIZADA (NO EXISTE EN PYTHON) QUE CONSTRUYE UNA CADENA MEDIANTE APPEND SEMEJANTE
# AL STRINGBUILDER DEL C#
class StringBuilder:
    _file_str = None

    def __init__(self):
        self._file_str = io.StringIO()

    def Append(self, str):
        self._file_str.write(str)

    def __str__(self):
        return self._file_str.getvalue()


def consulta_clave(clave, token, tipo_ambiente):

    endpoint = fe_enums.UrlHaciendaRecepcion[tipo_ambiente] + clave

    headers = {
        'Authorization': 'Bearer {}'.format(token),
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Postman-Token': 'bf8dc171-5bb7-fa54-7416-56c5cda9bf5c'
    }

    _logger.error('MAB - consulta_clave - url: %s' % endpoint)

    try:
        # response = requests.request("GET", url, headers=headers)
        response = requests.get(endpoint, headers=headers)
        ############################
    except requests.exceptions.RequestException as e:
        _logger.error('Exception %s' % e)
        return {'status': -1, 'text': 'Excepcion %s' % e}

    if 200 <= response.status_code <= 299:
        response_json = {
            'status': 200,
            'ind-estado': response.json().get('ind-estado'),
            'respuesta-xml': response.json().get('respuesta-xml')
        }
    elif 400 <= response.status_code <= 499:
        response_json = {'status': 400, 'ind-estado': 'error'}
    else:
        _logger.error('MAB - consulta_clave failed.  error: %s',
                      response.status_code)
        response_json = {'status': response.status_code,
                         'text': 'token_hacienda failed: %s' % response.reason}
    return response_json


def consulta_documentos(self, inv, env, token_m_h, date_cr, xml_firmado):
    if inv.type == 'in_invoice' or inv.type == 'in_refund':
        if not inv.consecutive_number_receiver:
            if len(inv.number) == 20:
                inv.consecutive_number_receiver = inv.number
            else:
                if inv.state_invoice_partner == '1':
                    tipo_documento = 'CCE'
                elif inv.state_invoice_partner == '2':
                    tipo_documento = 'CPCE'
                else:
                    tipo_documento = 'RCE'
                response_json = get_clave_hacienda(
                    self, tipo_documento, inv.number, inv.journal_id.sucursal, inv.journal_id.terminal)
                inv.consecutive_number_receiver = response_json.get(
                    'consecutivo')

        clave = inv.number_electronic + "-" + inv.consecutive_number_receiver
    else:
        clave = inv.number_electronic

    response_json = consulta_clave(clave, token_m_h, env)
    _logger.debug(response_json)
    estado_m_h = response_json.get('ind-estado')

    if (not xml_firmado) and (not date_cr):
        self.message_post(body='<p>Ha realizado la consulta a Haciendo de:'
                               + '<br /><b>Documento: </b>' + payload['clave']
                               + '<br /><b>Estado del documento: </b>' + estado_m_h + '</p>',
                          subtype='mail.mt_note',
                          content_subtype='html')

    # Siempre sin importar el estado se actualiza la fecha de acuerdo a la devuelta por Hacienda y
    # se carga el xml devuelto por Hacienda
    last_state = inv.state_send_invoice
    if inv.type == 'out_invoice' or inv.type == 'out_refund':
        # Se actualiza el estado con el que devuelve Hacienda
        inv.state_tributacion = estado_m_h
        inv.date_issuance = date_cr
        inv.fname_xml_comprobante = 'comprobante_' + inv.number_electronic + '.xml'
        inv.xml_comprobante = xml_firmado
    elif inv.type == 'in_invoice' or inv.type == 'in_refund':
        inv.fname_xml_comprobante = 'receptor_' + inv.number_electronic + '.xml'
        inv.xml_comprobante = xml_firmado
        inv.state_send_invoice = estado_m_h

    # Si fue aceptado o rechazado por haciendo se carga la respuesta
    if (estado_m_h == 'aceptado' or estado_m_h == 'rechazado') or (
            inv.type == 'out_invoice' or inv.type == 'out_refund'):
        inv.fname_xml_respuesta_tributacion = 'respuesta_' + inv.number_electronic + '.xml'
        inv.xml_respuesta_tributacion = response_json.get('respuesta-xml')

    # Si fue aceptado por Hacienda y es un factura de cliente o nota de crédito, se envía el correo con los documentos
    if inv.state_send_invoice == 'aceptado' and (last_state is False or last_state == 'procesando'):
        # if not inv.partner_id.opt_out:
        if inv.type == 'in_invoice' or inv.type == 'in_refund':
            email_template = self.env.ref(
                'cr_electronic_invoice.email_template_invoice_vendor', False)
        else:
            email_template = self.env.ref(
                'account.email_template_edi_invoice', False)

            # attachment_resp = self.env['ir.attachment'].search(
            #    [('res_model', '=', 'account.invoice'), ('res_id', '=', inv.id),
            #     ('res_field', '=', 'xml_respuesta_tributacion')], limit=1)
            # attachment_resp.name = inv.fname_xml_respuesta_tributacion
            # attachment_resp.datas_fname = inv.fname_xml_respuesta_tributacion

        attachments = []

        attachment = self.env['ir.attachment'].search(
            [('res_model', '=', 'account.invoice'), ('res_id', '=', inv.id),
             ('res_field', '=', 'xml_comprobante')], limit=1)

        if attachment.id:
            attachment.name = inv.fname_xml_comprobante
            attachment.datas_fname = inv.fname_xml_comprobante
            attachments.append(attachment.id)

        attachment_resp = self.env['ir.attachment'].search(
            [('res_model', '=', 'account.invoice'), ('res_id', '=', inv.id),
             ('res_field', '=', 'xml_respuesta_tributacion')], limit=1)

        if attachment_resp.id:
            attachment_resp.name = inv.fname_xml_respuesta_tributacion
            attachment_resp.datas_fname = inv.fname_xml_respuesta_tributacion
            attachments.append(attachment_resp.id)

        if len(attachments) == 2:
            email_template.attachment_ids = [(6, 0, attachments)]

            email_template.with_context(type='binary', default_type='binary').send_mail(inv.id,
                                                                                        raise_exception=False,
                                                                                        force_send=True)  # default_type='binary'

            # limpia el template de los attachments
            email_template.attachment_ids = [(5)]


def send_message(inv, date_cr, token, env):

    endpoint = fe_enums.UrlHaciendaRecepcion[tipo_ambiente]

    comprobante = {}
    comprobante['clave'] = inv.number_electronic
    comprobante['consecutivoReceptor'] = inv.consecutive_number_receiver
    comprobante["fecha"] = date_cr
    vat = re.sub('[^0-9]', '', inv.partner_id.vat)
    comprobante['emisor'] = {}
    comprobante['emisor']['tipoIdentificacion'] = inv.partner_id.identification_id.code
    comprobante['emisor']['numeroIdentificacion'] = vat
    comprobante['receptor'] = {}
    comprobante['receptor']['tipoIdentificacion'] = inv.company_id.identification_id.code
    comprobante['receptor']['numeroIdentificacion'] = inv.company_id.vat

    comprobante['comprobanteXml'] = inv.xml_comprobante
    _logger.info('MAB - Comprobante : %s' % comprobante)
    headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer {}'.format(token)}
    _logger.info('MAB - URL : %s' % endpoint)
    _logger.info('MAB - Headers : %s' % headers)

    try:
        response = requests.post(
            endpoint, data=json.dumps(comprobante), headers=headers)

    except requests.exceptions.RequestException as e:
        _logger.info('Exception %s' % e)
        return {'status': 400, 'text': u'Excepción de envio XML'}
        # raise Exception(e)

    if not (200 <= response.status_code <= 299):
        _logger.error('MAB - ERROR SEND MESSAGE - RESPONSE:%s' %
                      response.headers.get('X-Error-Cause', 'Unknown'))
        return {'status': response.status_code, 'text': response.headers.get('X-Error-Cause', 'Unknown')}
    else:
        return {'status': response.status_code, 'text': response.text}
