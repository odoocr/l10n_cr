import requests
import datetime
import json
from . import fe_enums
import io
import re
import os
import base64
import logging
import pytz
import time
import phonenumbers
import random
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from odoo import _
from odoo.exceptions import UserError
from xml.sax.saxutils import escape
from ..xades.context2 import XAdESContext2, PolicyId2, create_xades_epes_signature

from lxml import etree

try:
    from OpenSSL import crypto
except(ImportError, IOError) as err:
    logging.info(err)

# PARA VALIDAR JSON DE RESPUESTA
# from .. import extensions

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
def limit(texto, limit):
    return (texto[:limit - 3] + '...') if len(texto) > limit else texto


def get_mr_sequencevalue(inv):
    # '''Verificamos si el ID del mensaje receptor es válido'''
    mr_mensaje_id = int(inv.state_invoice_partner)
    if mr_mensaje_id is None:
        raise UserError(_('No se ha proporcionado un ID válido para el MR.'))
    if mr_mensaje_id < 1 or mr_mensaje_id > 3:
        raise UserError(_('El ID del mensaje receptor es inválido.'))

    if inv.state_invoice_partner == '1':
        detalle_mensaje = 'Aceptado'
        tipo = 1
        tipo_documento = fe_enums.TipoDocumento['CCE']
        sequence = inv.env['ir.sequence'].next_by_code(
            'sequence.electronic.doc.confirmation')

    elif inv.state_invoice_partner == '2':
        detalle_mensaje = 'Aceptado parcial'
        tipo = 2
        tipo_documento = fe_enums.TipoDocumento['CPCE']
        sequence = inv.env['ir.sequence'].next_by_code(
            'sequence.electronic.doc.partial.confirmation')
    else:
        detalle_mensaje = 'Rechazado'
        tipo = 3
        tipo_documento = fe_enums.TipoDocumento['RCE']
        sequence = inv.env['ir.sequence'].next_by_code(
            'sequence.electronic.doc.reject')

    return {'detalle_mensaje': detalle_mensaje, 'tipo': tipo, 'tipo_documento': tipo_documento, 'sequence': sequence}


def get_consecutivo_hacienda(tipo_documento, consecutivo, sucursal_id, terminal_id):

    tipo_doc = fe_enums.TipoDocumento[tipo_documento]

    inv_consecutivo = str(consecutivo).zfill(10)
    inv_sucursal = str(sucursal_id).zfill(3)
    inv_terminal = str(terminal_id).zfill(5)

    consecutivo_mh = inv_sucursal + inv_terminal + tipo_doc + inv_consecutivo

    return consecutivo_mh


def get_clave_hacienda(doc, tipo_documento, consecutivo, sucursal_id, terminal_id, situacion='normal'):

    tipo_doc = fe_enums.TipoDocumento[tipo_documento]

    # '''Verificamos si el consecutivo indicado corresponde a un numero'''
    inv_consecutivo = re.sub('[^0-9]', '', consecutivo)
    if len(inv_consecutivo) != 10:
        raise UserError(_('La numeración debe de tener 10 dígitos'))

    # '''Verificamos la sucursal y terminal'''
    inv_sucursal = re.sub('[^0-9]', '', str(sucursal_id)).zfill(3)
    inv_terminal = re.sub('[^0-9]', '', str(terminal_id)).zfill(5)

    # '''Armamos el consecutivo pues ya tenemos los datos necesarios'''
    consecutivo_mh = inv_sucursal + inv_terminal + tipo_doc + inv_consecutivo

    if not doc.company_id.identification_id:
        raise UserError(_('Seleccione el tipo de identificación del emisor en el pérfil de la compañía'))

    # '''Obtenemos el número de identificación del Emisor y lo validamos númericamente'''
    inv_cedula = re.sub('[^0-9]', '', doc.company_id.vat)

    # '''Validamos el largo de la cadena númerica de la cédula del emisor'''
    if doc.company_id.identification_id.code == '01' and len(inv_cedula) != 9:
        raise UserError(_('La Cédula Física del emisor debe de tener 9 dígitos'))
    elif doc.company_id.identification_id.code == '02' and len(inv_cedula) != 10:
        raise UserError(_('La Cédula Jurídica del emisor debe de tener 10 dígitos'))
    elif doc.company_id.identification_id.code == '03' and len(inv_cedula) not in (11, 12):
        raise UserError(_('La identificación DIMEX del emisor debe de tener 11 o 12 dígitos'))
    elif doc.company_id.identification_id.code == '04' and len(inv_cedula) != 10:
        raise UserError(_('La identificación NITE del emisor debe de tener 10 dígitos'))

    inv_cedula = str(inv_cedula).zfill(12)

    # '''Limitamos la cedula del emisor a 20 caracteres o nos dará error'''
    cedula_emisor = limit(inv_cedula, 20)

    # '''Validamos la situación del comprobante electrónico'''
    situacion_comprobante = fe_enums.SituacionComprobante.get(situacion)
    if not situacion_comprobante:
        raise UserError(_(f'La situación indicada para el comprobante electŕonico es inválida: {situacion}'))

    # '''Creamos la fecha para la clave'''
    dia = str(doc.invoice_date.day).zfill(2)
    mes = str(doc.invoice_date.month).zfill(2)
    anno = str(doc.invoice_date.year)[2:]
    cur_date = dia + mes + anno

    phone = phonenumbers.parse(doc.company_id.phone,
                               doc.company_id.country_id and doc.company_id.country_id.code or 'CR')
    codigo_pais = str(phone and phone.country_code or 506)

    # '''Creamos un código de seguridad random'''
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

    if token and (current_time - token_time < token_expire - 10):
        token_hacienda = token
    else:
        headers = {}
        data = {'client_id': tipo_ambiente,
                'client_secret': '',
                'grant_type': 'password',
                'username': inv.company_id.frm_ws_identificador,
                'password': inv.company_id.frm_ws_password}

        # establecer el ambiente al cual me voy a conectar
        endpoint = fe_enums.UrlHaciendaToken[tipo_ambiente]

        try:
            # enviando solicitud post y guardando la respuesta como un objeto json
            response = requests.request(
                "POST", endpoint, data=data, headers=headers)
            response_json = response.json()

            # F841 local variable 'respuesta' is assigned to but never used
            # respuesta = extensions.response_validator.assert_valid_schema(response_json, 'token.json')

            if 200 <= response.status_code <= 299:
                token_hacienda = response_json.get('access_token')
                last_tokens[inv.company_id.id] = token
                last_tokens_time[inv.company_id.id] = time.time()
                last_tokens_expire[inv.company_id.id] = response_json.get('expires_in')
                last_tokens_refresh[inv.company_id.id] = response_json.get('refresh_expires_in')
            else:
                _logger.error('FECR - token_hacienda failed.  error: %s' % (response.status_code))

        except requests.exceptions.RequestException as e:
            raise Warning(_('Error Obteniendo el Token desde MH. Excepcion %s'), (e))

    return token_hacienda


def refresh_token_hacienda(tipo_ambiente, token):

    headers = {}
    data = {'client_id': tipo_ambiente,
            'client_secret': '',
            'grant_type': 'refresh_token',
            'refresh_token': token}

    # establecer el ambiente al cual me voy a conectar
    endpoint = fe_enums.UrlHaciendaToken[tipo_ambiente]

    try:
        # enviando solicitud post y guardando la respuesta como un objeto json
        response = requests.request("POST", endpoint, data=data, headers=headers)
        response_json = response.json()
        token_hacienda = response_json.get('access_token')
        return token_hacienda
    except ImportError:
        raise Warning(_('Error Refrescando el Token desde MH'))


def gen_xml_mr_43(clave, cedula_emisor, fecha_emision, id_mensaje,
                  detalle_mensaje, cedula_receptor,
                  consecutivo_receptor,
                  monto_impuesto=0, total_factura=0,
                  codigo_actividad=False,
                  condicion_impuesto=False,
                  monto_total_impuesto_acreditar=False,
                  monto_total_gasto_aplicable=False):
    # '''Verificamos si la clave indicada corresponde a un numeros'''
    if clave:
        mr_clave = re.sub('[^0-9]', '', clave)
    else:
        mr_clave = False
    if len(mr_clave) != 50:
        raise UserError(_('La clave a utilizar es inválida. Debe contener al menos 50 digitos'))

    # '''Obtenemos el número de identificación del Emisor y lo validamos númericamente'''
    mr_cedula_emisor = re.sub('[^0-9]', '', cedula_emisor)
    if len(mr_cedula_emisor) != 12:
        mr_cedula_emisor = str(mr_cedula_emisor).zfill(12)
    elif mr_cedula_emisor is None:
        raise UserError(_('La cédula del Emisor en el MR es inválida.'))

    mr_fecha_emision = fecha_emision
    if mr_fecha_emision is None:
        raise UserError(_('La fecha de emisión en el MR es inválida.'))

    # '''Verificamos si el ID del mensaje receptor es válido'''
    mr_mensaje_id = int(id_mensaje)
    if mr_mensaje_id < 1 and mr_mensaje_id > 3:
        raise UserError(_('El ID del mensaje receptor es inválido.'))
    elif mr_mensaje_id is None:
        raise UserError(_('No se ha proporcionado un ID válido para el MR.'))

    mr_cedula_receptor = re.sub('[^0-9]', '', cedula_receptor)
    if len(mr_cedula_receptor) != 12:
        mr_cedula_receptor = str(mr_cedula_receptor).zfill(12)
    elif mr_cedula_receptor is None:
        raise UserError(_('No se ha proporcionado una cédula de receptor válida para el MR.'))

    # '''Verificamos si el consecutivo indicado para el mensaje receptor corresponde a numeros'''
    mr_consecutivo_receptor = re.sub('[^0-9]', '', consecutivo_receptor)
    if len(mr_consecutivo_receptor) != 20:
        raise UserError(_('La clave del consecutivo para el mensaje receptor es inválida. '
                        'Debe contener al menos 50 digitos'))

    mr_monto_impuesto = monto_impuesto
    mr_detalle_mensaje = detalle_mensaje
    mr_total_factura = total_factura

    # '''Iniciamos con la creación del mensaje Receptor'''
    sb = StringBuilder()
    sb.append('<MensajeReceptor xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.append('xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/mensajeReceptor" ')
    sb.append('xsi:schemaLocation="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/mensajeReceptor ')
    # E501 line too long
    sb.append('https://www.hacienda.go.cr/ATV/ComprobanteElectronico/' +
              'docs/esquemas/2016/v4.3/MensajeReceptor_V4.3.xsd">')
    sb.append('<Clave>' + mr_clave + '</Clave>')
    sb.append('<NumeroCedulaEmisor>' + mr_cedula_emisor + '</NumeroCedulaEmisor>')
    sb.append('<FechaEmisionDoc>' + mr_fecha_emision + '</FechaEmisionDoc>')
    sb.append('<Mensaje>' + str(mr_mensaje_id) + '</Mensaje>')

    if mr_detalle_mensaje is not None:
        sb.append('<DetalleMensaje>' + escape(mr_detalle_mensaje) + '</DetalleMensaje>')

    if mr_monto_impuesto is not None and mr_monto_impuesto > 0:
        sb.append('<MontoTotalImpuesto>' + str(mr_monto_impuesto) + '</MontoTotalImpuesto>')

    if codigo_actividad:
        sb.append('<CodigoActividad>' + str(codigo_actividad) + '</CodigoActividad>')

    sb.append('<CondicionImpuesto>' + str(condicion_impuesto) + '</CondicionImpuesto>')

    # TODO: Estar atento a la publicación de Hacienda de cómo utilizar esto
    if monto_total_impuesto_acreditar:
        sb.append('<MontoTotalImpuestoAcreditar>' +
                  str(monto_total_impuesto_acreditar) +
                  '</MontoTotalImpuestoAcreditar>')

    # TODO: Estar atento a la publicación de Hacienda de cómo utilizar esto
    if monto_total_gasto_aplicable:
        sb.append('<MontoTotalDeGastoAplicable>' + str(monto_total_gasto_aplicable) + '</MontoTotalDeGastoAplicable>')

    if mr_total_factura is not None and mr_total_factura > 0:
        sb.append('<TotalFactura>' + str(mr_total_factura) + '</TotalFactura>')
    else:
        raise UserError(_('El monto Total de la Factura para el Mensaje Receptro es inválido'))

    sb.append('<NumeroCedulaReceptor>' + mr_cedula_receptor + '</NumeroCedulaReceptor>')
    sb.append('<NumeroConsecutivoReceptor>' + mr_consecutivo_receptor + '</NumeroConsecutivoReceptor>')
    sb.append('</MensajeReceptor>')

    return str(sb)


def gen_xml_v43(inv, sale_conditions, total_servicio_gravado,
                total_servicio_exento, totalServExonerado,
                total_mercaderia_gravado, total_mercaderia_exento,
                totalMercExonerada, totalOtrosCargos, total_iva_devuelto, base_total,
                total_impuestos, total_descuento, lines,
                otrosCargos, currency_rate, invoice_comments,
                tipo_documento_referencia, numero_documento_referencia,
                fecha_emision_referencia, codigo_referencia, razon_referencia):

    numero_linea = 0
    payment_methods_id = []

    if inv._name == 'pos.order':
        plazo_credito = '0'
        for payment in inv.payment_ids:
            # En caso que no tenga código definido se colocará el de efectivo para evitar rechazos de documentos
            if not payment.payment_method_id.sequence:
                payment_methods_id.append('01')
            else:
                # Se agrega el campo code en los métodos de pago de Odoo POS
                payment_methods_id.append(str(payment.payment_method_id.sequence))
        cod_moneda = str(inv.company_id.currency_id.name)
    else:
        payment_methods_id.append(str(inv.payment_methods_id.sequence))
        plazo_credito = str(inv.invoice_payment_term_id and inv.invoice_payment_term_id.line_ids[0].days or 0)
        cod_moneda = str(inv.currency_id.name)

    if inv.tipo_documento == 'FEC':
        issuing_company = inv.partner_id
        receiver_company = inv.company_id
    else:
        issuing_company = inv.company_id
        receiver_company = inv.partner_id

    sb = StringBuilder()
    sb.append('<' + fe_enums.tagName[inv.tipo_documento] +
              ' xmlns="' +
              fe_enums.XmlnsHacienda[inv.tipo_documento] + '" ')
    sb.append('xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsd="http://www.w3.org/2001/XMLSchema" ')
    sb.append('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.append('xsi:schemaLocation="' + fe_enums.schemaLocation[inv.tipo_documento] + '">')

    sb.append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.append('<CodigoActividad>' + inv.economic_activity_id.code + '</CodigoActividad>')
    sb.append('<NumeroConsecutivo>' + inv.number_electronic[21:41] + '</NumeroConsecutivo>')
    sb.append('<FechaEmision>' + inv.date_issuance + '</FechaEmision>')
    sb.append('<Emisor>')
    sb.append('<Nombre>' + escape(issuing_company.legal_name or issuing_company.name) + '</Nombre>')
    sb.append('<Identificacion>')
    sb.append('<Tipo>' + issuing_company.identification_id.code + '</Tipo>')
    sb.append('<Numero>' + issuing_company.vat + '</Numero>')
    sb.append('</Identificacion>')
    sb.append('<NombreComercial>' + escape(str(issuing_company.commercial_name or 'NA')) + '</NombreComercial>')
    sb.append('<Ubicacion>')
    sb.append('<Provincia>' + issuing_company.state_id.code + '</Provincia>')
    sb.append('<Canton>' + issuing_company.county_id.code + '</Canton>')
    sb.append('<Distrito>' + issuing_company.district_id.code + '</Distrito>')

    if issuing_company.neighborhood_id and issuing_company.neighborhood_id.code:
        sb.append('<Barrio>' + str(issuing_company.neighborhood_id.code or '00') + '</Barrio>')

    sb.append('<OtrasSenas>' + escape(str(issuing_company.street or 'NA')) + '</OtrasSenas>')
    sb.append('</Ubicacion>')

    if issuing_company.phone:
        phone = phonenumbers.parse(issuing_company.phone, (issuing_company.country_id.code or 'CR'))
        sb.append('<Telefono>')
        sb.append('<CodigoPais>' + str(phone.country_code) + '</CodigoPais>')
        sb.append('<NumTelefono>' + str(phone.national_number) + '</NumTelefono>')
        sb.append('</Telefono>')

    sb.append('<CorreoElectronico>' + str(issuing_company.email) + '</CorreoElectronico>')
    sb.append('</Emisor>')

    if inv.tipo_documento == 'TE' or (inv.tipo_documento == 'NC' and not receiver_company.vat):
        pass
    else:
        vat = re.sub('[^0-9]', '', receiver_company.vat)
        if not receiver_company.identification_id:
            if len(vat) == 9:  # cedula fisica
                id_code = '01'
            elif len(vat) == 10:  # cedula juridica
                id_code = '02'
            elif len(vat) == 11 or len(vat) == 12:  # dimex
                id_code = '03'
            else:
                id_code = '05'
        else:
            id_code = receiver_company.identification_id.code

        if receiver_company.name:
            sb.append('<Receptor>')
            sb.append('<Nombre>' + escape(str(receiver_company.name[:99])) + '</Nombre>')

            if inv.tipo_documento == 'FEE' or id_code == '05':
                if receiver_company.vat:
                    sb.append('<IdentificacionExtranjero>' + receiver_company.vat + '</IdentificacionExtranjero>')
            else:
                sb.append('<Identificacion>')
                sb.append('<Tipo>' + id_code + '</Tipo>')
                sb.append('<Numero>' + vat + '</Numero>')
                sb.append('</Identificacion>')

            if inv.tipo_documento != 'FEE':
                if receiver_company.state_id and \
                    receiver_company.county_id and \
                        receiver_company.district_id and receiver_company.neighborhood_id:
                    sb.append('<Ubicacion>')
                    sb.append('<Provincia>' + str(receiver_company.state_id.code or '') + '</Provincia>')
                    sb.append('<Canton>' + str(receiver_company.county_id.code or '') + '</Canton>')
                    sb.append('<Distrito>' + str(receiver_company.district_id.code or '') + '</Distrito>')

                    if receiver_company.neighborhood_id and receiver_company.neighborhood_id.code:
                        sb.append('<Barrio>' + str(receiver_company.neighborhood_id.code or '00') + '</Barrio>')

                    sb.append('<OtrasSenas>' + escape(str(receiver_company.street or 'NA')) + '</OtrasSenas>')
                    sb.append('</Ubicacion>')

                if receiver_company.phone:
                    phone = phonenumbers.parse(receiver_company.phone, (receiver_company.country_id.code or 'CR'))
                    sb.append('<Telefono>')
                    sb.append('<CodigoPais>' + str(phone.country_code) + '</CodigoPais>')
                    sb.append('<NumTelefono>' + str(phone.national_number) + '</NumTelefono>')
                    sb.append('</Telefono>')
                # E501 line too long
                re_match = r'^(\s?[^\s,]+@[^\s,]+\.[^\s,]+\s?,)*(\s?[^\s,]+@[^\s,]+\.[^\s,]+)$'
                match = receiver_company.email and re.match(re_match, receiver_company.email.lower())
                if match:
                    email_receptor = receiver_company.email
                else:
                    email_receptor = 'indefinido@indefinido.com'
                sb.append('<CorreoElectronico>' + email_receptor + '</CorreoElectronico>')

            sb.append('</Receptor>')

    sb.append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.append('<PlazoCredito>' + plazo_credito + '</PlazoCredito>')
    payment_method_length = len(payment_methods_id)
    for payment_method_counter in range(payment_method_length):
        sb.append('<MedioPago>' + payment_methods_id[payment_method_counter] + '</MedioPago>')

    if lines:
        sb.append('<DetalleServicio>')

        for (k, v) in lines.items():
            numero_linea = numero_linea + 1

            sb.append('<LineaDetalle>')
            sb.append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')

            if inv.tipo_documento == 'FEE' and v.get('partidaArancelaria'):
                sb.append('<PartidaArancelaria>' + str(v['partidaArancelaria']) + '</PartidaArancelaria>')

            if v.get('codigoCabys'):
                sb.append('<Codigo>' + (v['codigoCabys']) + '</Codigo>')

            if v.get('codigo'):
                sb.append('<CodigoComercial>')
                sb.append('<Tipo>04</Tipo>')
                sb.append('<Codigo>' + (v['codigo']) + '</Codigo>')
                sb.append('</CodigoComercial>')

            sb.append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
            sb.append('<UnidadMedida>' + str(v['unidadMedida']) + '</UnidadMedida>')
            sb.append('<Detalle>' + str(v['detalle']) + '</Detalle>')
            sb.append('<PrecioUnitario>' + str(v['precioUnitario']) + '</PrecioUnitario>')
            sb.append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
            if v.get('montoDescuento'):
                sb.append('<Descuento>')
                sb.append('<MontoDescuento>' + str(v['montoDescuento']) + '</MontoDescuento>')
                if v.get('naturalezaDescuento'):
                    sb.append('<NaturalezaDescuento>' + str(v['naturalezaDescuento']) + '</NaturalezaDescuento>')
                sb.append('</Descuento>')

            sb.append('<SubTotal>' + str(v['subtotal']) + '</SubTotal>')

            # TODO: ¿qué es base imponible? ¿porqué podría ser diferente del subtotal?
            # if inv.tipo_documento != 'FEE':
            #   sb.append('<BaseImponible>' + str(v['subtotal']) + '</BaseImponible>')

            if v.get('impuesto'):
                for (a, b) in v['impuesto'].items():
                    tax_code = str(b['iva_tax_code'])
                    sb.append('<Impuesto>')
                    sb.append('<Codigo>' + str(b['codigo']) + '</Codigo>')
                    if tax_code.isdigit():
                        sb.append('<CodigoTarifa>' + tax_code + '</CodigoTarifa>')
                    sb.append('<Tarifa>' + str(b['tarifa']) + '</Tarifa>')
                    sb.append('<Monto>' + str(b['monto']) + '</Monto>')

                    if inv.tipo_documento != 'FEE':
                        if b.get('exoneracion'):
                            sb.append('<Exoneracion>')

                            sb.append('<TipoDocumento>' +
                                      receiver_company.type_exoneration.code +
                                      '</TipoDocumento>')
                            sb.append('<NumeroDocumento>' +
                                      receiver_company.exoneration_number +
                                      '</NumeroDocumento>')
                            sb.append('<NombreInstitucion>' +
                                      receiver_company.institution_name +
                                      '</NombreInstitucion>')
                            sb.append('<FechaEmision>' +
                                      str(receiver_company.date_issue) + 'T00:00:00-06:00' +
                                      '</FechaEmision>')
                            sb.append('<PorcentajeExoneracion>' +
                                      str(b['exoneracion']['porcentajeCompra']) +
                                      '</PorcentajeExoneracion>')
                            sb.append('<MontoExoneracion>' +
                                      str(b['exoneracion']['montoImpuesto']) +
                                      '</MontoExoneracion>')

                            sb.append('</Exoneracion>')
                    sb.append('</Impuesto>')

                sb.append('<ImpuestoNeto>' + str(v['impuestoNeto']) + '</ImpuestoNeto>')

            sb.append('<MontoTotalLinea>' + str(v['montoTotalLinea']) + '</MontoTotalLinea>')
            sb.append('</LineaDetalle>')
        sb.append('</DetalleServicio>')

    if otrosCargos:
        sb.append('<OtrosCargos>')
        for otro_cargo in otrosCargos:
            sb.append('<TipoDocumento>' + str(otrosCargos[otro_cargo]['TipoDocumento']) + '</TipoDocumento>')

            if otrosCargos[otro_cargo].get('NumeroIdentidadTercero'):
                sb.append('<NumeroIdentidadTercero>' +
                          str(otrosCargos[otro_cargo]['NumeroIdentidadTercero']) +
                          '</NumeroIdentidadTercero>')

            if otrosCargos[otro_cargo].get('NombreTercero'):
                sb.append('<NombreTercero>' + str(otrosCargos[otro_cargo]['NombreTercero']) + '</NombreTercero>')

            sb.append('<Detalle>' + str(otrosCargos[otro_cargo]['Detalle']) + '</Detalle>')

            if otrosCargos[otro_cargo].get('Porcentaje'):
                sb.append('<Porcentaje>' + str(otrosCargos[otro_cargo]['Porcentaje']) + '</Porcentaje>')

            sb.append('<MontoCargo>' + str(otrosCargos[otro_cargo]['MontoCargo']) + '</MontoCargo>')
        sb.append('</OtrosCargos>')

    sb.append('<ResumenFactura>')
    sb.append('<CodigoTipoMoneda>')
    sb.append('<CodigoMoneda>' + cod_moneda + '</CodigoMoneda>')
    sb.append('<TipoCambio>' + str(currency_rate) + '</TipoCambio>')
    sb.append('</CodigoTipoMoneda>')

    sb.append('<TotalServGravados>' + str(total_servicio_gravado) + '</TotalServGravados>')
    sb.append('<TotalServExentos>' + str(total_servicio_exento) + '</TotalServExentos>')

    if inv.tipo_documento != 'FEE':
        sb.append('<TotalServExonerado>' + str(totalServExonerado) + '</TotalServExonerado>')

    sb.append('<TotalMercanciasGravadas>' + str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.append('<TotalMercanciasExentas>' + str(total_mercaderia_exento) + '</TotalMercanciasExentas>')

    if inv.tipo_documento != 'FEE':
        sb.append('<TotalMercExonerada>' + str(totalMercExonerada) + '</TotalMercExonerada>')

    sb.append('<TotalGravado>' + str(round(total_servicio_gravado + total_mercaderia_gravado, 5)) + '</TotalGravado>')
    sb.append('<TotalExento>' + str(round(total_servicio_exento + total_mercaderia_exento, 5)) + '</TotalExento>')

    if inv.tipo_documento != 'FEE':
        sb.append('<TotalExonerado>' + str(round(totalServExonerado + totalMercExonerada, 5)) + '</TotalExonerado>')

    sb.append('<TotalVenta>' +
              str(round(total_servicio_gravado +
                        total_mercaderia_gravado +
                        total_servicio_exento +
                        total_mercaderia_exento +
                        totalServExonerado +
                        totalMercExonerada, 5)) +
              '</TotalVenta>')
    sb.append('<TotalDescuentos>' + str(round(total_descuento, 5)) + '</TotalDescuentos>')
    sb.append('<TotalVentaNeta>' + str(round(base_total, 5)) + '</TotalVentaNeta>')
    sb.append('<TotalImpuesto>' + str(round(total_impuestos, 5)) + '</TotalImpuesto>')

    if total_iva_devuelto:
        sb.append('<TotalIVADevuelto>' + str(round(total_iva_devuelto, 5)) + '</TotalIVADevuelto>')

    sb.append('<TotalOtrosCargos>' + str(totalOtrosCargos) + '</TotalOtrosCargos>')

    sb.append('<TotalComprobante>' +
              str(round(base_total + total_impuestos + totalOtrosCargos - total_iva_devuelto, 5)) +
              '</TotalComprobante>')

    sb.append('</ResumenFactura>')

    if tipo_documento_referencia and numero_documento_referencia and fecha_emision_referencia:
        sb.append('<InformacionReferencia>')
        sb.append('<TipoDoc>' + str(tipo_documento_referencia) + '</TipoDoc>')
        sb.append('<Numero>' + str(numero_documento_referencia) + '</Numero>')
        sb.append('<FechaEmision>' + fecha_emision_referencia + '</FechaEmision>')
        sb.append('<Codigo>' + str(codigo_referencia) + '</Codigo>')
        sb.append('<Razon>' + str(razon_referencia) + '</Razon>')
        sb.append('</InformacionReferencia>')
    if invoice_comments:
        sb.append('<Otros>')
        sb.append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
        sb.append('</Otros>')

    sb.append('</' + fe_enums.tagName[inv.tipo_documento] + '>')

    return sb


# Funcion para enviar el XML al Ministerio de Hacienda
def send_xml_fe(inv, token, date, xml, tipo_ambiente):
    headers = {'Authorization': 'Bearer ' +
               token, 'Content-type': 'application/json'}

    # establecer el ambiente al cual me voy a conectar
    endpoint = fe_enums.UrlHaciendaRecepcion[tipo_ambiente]

    xml_base64 = string_to_base64(xml)

    data = {'clave': inv.number_electronic,
            'fecha': date,
            'emisor': {
                'tipoIdentificacion': inv.company_id.identification_id.code,
                'numeroIdentificacion': inv.company_id.vat
            },
            'comprobanteXml': xml_base64
            }
    if inv.partner_id and inv.partner_id.vat:
        if not inv.partner_id.identification_id:
            if len(inv.partner_id.vat) == 9:  # cedula fisica
                id_code = '01'
            elif len(inv.partner_id.vat) == 10:  # cedula juridica
                id_code = '02'
            elif len(inv.partner_id.vat) == 11 or len(inv.partner_id.vat) == 12:  # dimex
                id_code = '03'
            else:
                id_code = '05'
        else:
            id_code = inv.partner_id.identification_id.code

        data['receptor'] = {'tipoIdentificacion': id_code,
                            'numeroIdentificacion': inv.partner_id.vat}

    json_hacienda = json.dumps(data)

    try:
        # enviando solicitud post y guardando la respuesta como un objeto json
        response = requests.request("POST", endpoint, data=json_hacienda, headers=headers)

        # Verificamos el codigo devuelto, si es distinto de 202 es porque hacienda nos está devolviendo algun error
        if response.status_code != 202:
            error_caused_by = response.headers.get(
                'X-Error-Cause') if 'X-Error-Cause' in response.headers else ''
            error_caused_by += response.headers.get('validation-exception', '')
            _logger.error('Status: {}, Text {}'.format(
                response.status_code, error_caused_by))

            return {'status': response.status_code, 'text': error_caused_by}
        else:
            # respuesta_hacienda = response.status_code
            return {'status': response.status_code, 'text': response.reason}
            # return respuesta_hacienda

    except ImportError:
        raise Warning(_('Error enviando el XML al Ministerior de Hacienda'))


def schema_validator(xml_file, xsd_file) -> bool:
    """ verifies a xml
    :param xml_invoice: Invoice xml
    :param  xsd_file: XSD File Name
    :return:
    """

    xmlschema = etree.XMLSchema(etree.parse(os.path.join(os.path.dirname(__file__), "xsd/" + xsd_file)))

    xml_doc = base64decode(xml_file)
    root = etree.fromstring(xml_doc, etree.XMLParser(remove_blank_text=True))
    result = xmlschema.validate(root)

    return result


# Obtener Attachments para las Facturas Electrónicas
def get_invoice_attachments(invoice, record_id):
    attachments = []

    domain = [('res_model', '=', invoice._name),
              ('res_id', '=', invoice.id),
              ('res_field', '=', 'xml_comprobante'),
              ('name', '=', invoice.tipo_documento + '_' + invoice.number_electronic + '.xml')]
    attachment = invoice.env['ir.attachment'].sudo().search(domain, limit=1)

    if attachment.id:
        # attachment.name = invoice.fname_xml_comprobante
        # attachment.datas_fname = invoice.fname_xml_comprobante
        attach_copy = invoice.env['ir.attachment'].create({'name': invoice.fname_xml_comprobante,
                                                           'type': 'binary',
                                                           'datas': invoice.xml_comprobante,
                                                           'res_name': invoice.fname_xml_comprobante,
                                                           'mimetype': 'text/xml'})
        attachments.append(attach_copy.id)

    domain_resp = [('res_model', '=', invoice._name),
                   ('res_id', '=', invoice.id),
                   ('res_field', '=', 'xml_respuesta_tributacion'),
                   ('name', '=', 'AHC_' + invoice.number_electronic + '.xml')]
    attachment_resp = invoice.env['ir.attachment'].sudo().search(domain_resp, limit=1)

    if attachment_resp.id:
        # attachment_resp.name = invoice.fname_xml_respuesta_tributacion
        # attachment_resp.datas_fname = invoice.fname_xml_respuesta_tributacion
        attach_resp_copy = invoice.env['ir.attachment'].create({'name': invoice.fname_xml_respuesta_tributacion,
                                                                'type': 'binary',
                                                                'datas': invoice.xml_respuesta_tributacion,
                                                                'res_name': invoice.fname_xml_respuesta_tributacion,
                                                                'mimetype': 'text/xml'})
        attachments.append(attach_resp_copy.id)

    return attachments


def parse_xml(name):
    return etree.parse(name).getroot()


# CONVIERTE UN STRING A BASE 64
def string_to_base64(s):
    return base64.b64encode(s).decode()


# TOMA UNA CADENA Y ELIMINA LOS CARACTERES AL INICIO Y AL FINAL
def string_strip(s, start, end):
    return s[start:-end]


# Tomamos el XML y le hacemos el decode de base 64, esto por ahora es solo para probar
# la posible implementacion de la firma en python
def base64decode(string_decode):
    return base64.b64decode(string_decode)


# TOMA UNA CADENA EN BASE64 Y LA DECODIFICA PARA ELIMINAR EL b' Y DEJAR EL STRING CODIFICADO
# DE OTRA MANERA HACIENDA LO RECHAZA
def base64_utf8_decoder(s):
    return s.decode("utf-8")


# CLASE PERSONALIZADA (NO EXISTE EN PYTHON) QUE CONSTRUYE UNA CADENA MEDIANTE APPEND SEMEJANTE
# AL STRINGBUILDER DEL C#
class StringBuilder:
    _file_str = None

    def __init__(self):
        self._file_str = io.StringIO()

    def append(self, str):
        self._file_str.write(str)

    def __str__(self):
        return self._file_str.getvalue()


def consulta_clave(clave, token, tipo_ambiente):
    endpoint = fe_enums.UrlHaciendaRecepcion[tipo_ambiente] + clave

    headers = {'Authorization': 'Bearer {}'.format(token),
               'Cache-Control': 'no-cache',
               'Content-Type': 'application/x-www-form-urlencoded'}

    _logger.debug('FECR - consulta_clave - url: %s', endpoint)

    try:
        # response = requests.request("GET", url, headers=headers)
        response = requests.get(endpoint, headers=headers)

    except requests.exceptions.RequestException as e:
        _logger.error('Exception %s', e)
        return {'status': -1, 'text': 'Excepcion %s' % e}

    if 200 <= response.status_code <= 299:
        response_json = {'status': 200,
                         'ind-estado': response.json().get('ind-estado'),
                         'respuesta-xml': response.json().get('respuesta-xml')}
    elif 400 <= response.status_code <= 499:
        _logger.error('FECR - 400 - consulta_clave failed.  error: %s reason: %s',
                      response.status_code, response.reason)
        response_json = {'status': 400, 'ind-estado': 'error'}
    else:
        _logger.error('FECR - consulta_clave failed.  error: %s',
                      response.status_code)
        response_json = {'status': response.status_code,
                         'text': 'token_hacienda failed: %s' % response.reason}
    return response_json


def get_economic_activities(company):
    endpoint = "https://api.hacienda.go.cr/fe/ae?identificacion=" + company.vat

    headers = {'Cache-Control': 'no-cache',
               'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        response = requests.get(endpoint, headers=headers, verify=False)
    except requests.exceptions.RequestException as e:
        _logger.error('Exception %s', e)
        return {'status': -1, 'text': 'Excepcion %s' % e}

    if 200 <= response.status_code <= 299:
        _logger.debug('FECR - get_economic_activities response: %s', (response.json()))
        response_json = {'status': 200,
                         'activities': response.json().get('actividades'),
                         'name': response.json().get('nombre')}
    # elif 400 <= response.status_code <= 499:
    #    response_json = {'status': 400, 'ind-estado': 'error'}
    else:
        _logger.error('FECR - get_economic_activities failed.  error: %s',
                      response.status_code)
        response_json = {'status': response.status_code,
                         'text': 'get_economic_activities failed: %s' % response.reason}
    return response_json


def consulta_documentos(self, inv, env, token_m_h, date_cr, xml_firmado):
    if (inv.move_type in ['in_invoice', 'in_refund']) and (inv.tipo_documento != 'FEC'):
        clave = inv.number_electronic + "-" + inv.consecutive_number_receiver
    else:
        clave = inv.number_electronic

    response_json = consulta_clave(clave, token_m_h, env)
    _logger.debug(response_json)
    estado_m_h = response_json.get('ind-estado')

    # Siempre sin importar el estado se actualiza la fecha de acuerdo a la devuelta por Hacienda y
    # se carga el xml devuelto por Hacienda
    last_state = inv.state_tributacion
    inv.state_tributacion = estado_m_h
    if inv.move_type in ['out_invoice', 'out_refund']:
        # Se actualiza el estado con el que devuelve Hacienda
        last_state = inv.state_tributacion
        inv.state_tributacion = estado_m_h
        if date_cr:
            inv.date_issuance = date_cr
        if xml_firmado:
            inv.fname_xml_comprobante = inv.tipo_documento + inv.number_electronic + '.xml'

            # inv.xml_comprobante = xml_firmado
            self.env['ir.attachment'].sudo().create({'name': inv.fname_xml_comprobante,
                                                     'type': 'binary',
                                                     'datas': xml_firmado,
                                                     'res_model': self._name,
                                                     'res_id': inv.id,
                                                     'res_field': 'xml_comprobante',
                                                     'res_name': inv.fname_xml_comprobante,
                                                     'mimetype': 'text/xml'})
    elif inv.move_type in ['in_invoice', 'in_refund']:
        if xml_firmado:
            inv.fname_xml_comprobante = 'AHC_' + inv.number_electronic + '.xml'

            # inv.xml_comprobante = xml_firmado
            self.env['ir.attachment'].sudo().create({'name': inv.fname_xml_comprobante,
                                                     'type': 'binary',
                                                     'datas': xml_firmado,
                                                     'res_model': self._name,
                                                     'res_id': inv.id,
                                                     'res_field': 'xml_comprobante',
                                                     'res_name': inv.fname_xml_comprobante,
                                                     'mimetype': 'text/xml'})

    # Si fue aceptado o rechazado por haciendo se carga la respuesta
    if (estado_m_h in ['aceptado', 'rechazado']) or (inv.move_type in ['out_invoice', 'out_refund']):
        inv.fname_xml_respuesta_tributacion = 'AHC_' + inv.number_electronic + '.xml'

        # inv.xml_respuesta_tributacion = response_json.get('respuesta-xml')
        self.env['ir.attachment'].create({'name': inv.fname_xml_respuesta_tributacion,
                                          'type': 'binary',
                                          'datas': response_json.get('respuesta-xml'),
                                          'res_model': inv._name,
                                          'res_id': inv.id,
                                          'res_field': 'xml_respuesta_tributacion',
                                          'res_name': inv.fname_xml_respuesta_tributacion,
                                          'mimetype': 'text/xml'})

    # Si fue aceptado por Hacienda y es un factura de cliente o nota de crédito, se envía el correo con los documentos
    if inv.tipo_documento != 'FEC' and estado_m_h == 'aceptado' and (not last_state or last_state == 'procesando'):
        # if not inv.partner_id.opt_out:
        if inv.move_type in ['in_invoice', 'in_refund']:
            email_template = self.env.ref('cr_electronic_invoice.email_template_invoice_vendor', False)
        else:
            email_template = self.env.ref('account.email_template_edi_invoice', False)

        attachments = get_invoice_attachments(inv, inv.id)

        if len(attachments) == 2:
            email_template.attachment_ids = [(6, 0, attachments)]

            try:
                email_template.with_context(type='binary', default_type='binary').send_mail(inv.id,
                                                                                            raise_exception=False,
                                                                                            force_send=True)
            except Exception:
                _logger.error('FECR - consulta documento error al enviar correo: %s', inv.number_electronic)

            # limpia el template de los attachments
            email_template.attachment_ids = [(5, 0, 0)]


def send_message(inv, date_cr, xml, token, env):
    endpoint = fe_enums.UrlHaciendaRecepcion[env]

    vat = re.sub('[^0-9]', '', inv.partner_id.vat)
    xml_base64 = string_to_base64(xml)

    comprobante = {'clave': inv.number_electronic,
                   'consecutivoReceptor': inv.consecutive_number_receiver,
                   "fecha": date_cr,
                   'emisor': {'tipoIdentificacion': str(inv.partner_id.identification_id.code),
                              'numeroIdentificacion': vat
                              },
                   'receptor': {'tipoIdentificacion': str(inv.company_id.identification_id.code),
                                'numeroIdentificacion': inv.company_id.vat},
                   'comprobanteXml': xml_base64}

    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer {}'.format(token)}
    try:
        response = requests.post(endpoint, data=json.dumps(comprobante), headers=headers)

    except requests.exceptions.RequestException as e:
        _logger.info('Exception %s', e)
        return {'status': 400, 'text': 'Excepción de envio XML'}
        # raise Exception(e)

    if (200 <= response.status_code <= 299):
        return {'status': response.status_code, 'text': response.text}

    _logger.error('E-INV CR - ERROR SEND MESSAGE - RESPONSE:%s', response.headers.get('X-Error-Cause', 'Unknown'))
    return {'status': response.status_code, 'text': response.headers.get('X-Error-Cause', 'Unknown')}


def load_xml_data(invoice, load_lines, account_id, product_id=False, analytic_account_id=False):
    try:
        invoice_xml = etree.fromstring(base64.b64decode(invoice.xml_supplier_approval))
        doc_types = 'FacturaElectronica|NotaCreditoElectronica|NotaDebitoElectronica|TiqueteElectronico'
        document_type = re.search(doc_types, invoice_xml.tag).group(0)

        if document_type == 'TiqueteElectronico':
            raise UserError(_("This is a TICKET only invoices are valid for taxes"))

    except Exception as e:
        raise UserError(_("This XML file is not XML-compliant. Error: %s") % e)

    namespaces = invoice_xml.nsmap
    inv_xmlns = namespaces.pop(None)
    namespaces['inv'] = inv_xmlns

    # invoice.consecutive_number_receiver = invoice_xml.xpath("inv:NumeroConsecutivo", namespaces=namespaces)[0].text
    invoice.ref = invoice_xml.xpath("inv:NumeroConsecutivo", namespaces=namespaces)[0].text

    invoice.number_electronic = invoice_xml.xpath("inv:Clave", namespaces=namespaces)[0].text
    activity_node = invoice_xml.xpath("inv:CodigoActividad", namespaces=namespaces)
    activity_id = False
    activity = False
    if activity_node:
        activity = invoice.env['economic.activity'].with_context(active_test=False).search([('code',
                                                                                             '=',
                                                                                             activity_node[0].text)],
                                                                                           limit=1)
        activity_id = activity.id

    invoice.economic_activity_id = activity
    invoice.date_issuance = invoice_xml.xpath("inv:FechaEmision", namespaces=namespaces)[0].text
    invoice.invoice_date = invoice.date_issuance
    invoice.tipo_documento = False

    emisor = invoice_xml.xpath("inv:Emisor/inv:Identificacion/inv:Numero", namespaces=namespaces)[0].text
    tipo_emisor = invoice_xml.xpath("inv:Emisor/inv:Identificacion/inv:Tipo", namespaces=namespaces)[0].text
    nombre_emisor = invoice_xml.xpath("inv:Emisor/inv:Nombre", namespaces=namespaces)[0].text
    pais_emisor = invoice.env['res.country'].search([('name', '=', 'Costa Rica')], limit=1).id

    try:
        telefono_emisor = invoice_xml.xpath("inv:Emisor/inv:Telefono/inv:NumTelefono", namespaces=namespaces)[0].text
    except IndexError:
        telefono_emisor = ''
    try:
        otrassenas_emisor = invoice_xml.xpath("inv:Emisor/inv:Telefono/inv:NumTelefono", namespaces=namespaces)[0].text
    except IndexError:
        otrassenas_emisor = ''

    correo_emisor = invoice_xml.xpath("inv:Emisor/inv:CorreoElectronico", namespaces=namespaces)[0].text

    receptor_node = invoice_xml.xpath("inv:Receptor/inv:Identificacion/inv:Numero", namespaces=namespaces)
    if receptor_node:
        receptor = receptor_node[0].text
    else:
        raise UserError(_('El receptor no está definido en el xml'))

    if receptor != invoice.company_id.vat:
        raise UserError(_('El receptor no corresponde con la compañía actual con identificación ' +
                          receptor + '. Por favor active la compañía correcta.'))

    currency_node = invoice_xml.xpath("inv:ResumenFactura/inv:CodigoTipoMoneda/inv:CodigoMoneda",
                                      namespaces=namespaces)
    if currency_node:
        invoice.currency_id = invoice.env['res.currency'].search([('name', '=', currency_node[0].text)], limit=1).id
    else:
        invoice.currency_id = invoice.env['res.currency'].search([('name', '=', 'CRC')], limit=1).id

    partner = invoice.env['res.partner'].search([('vat', '=', emisor), '|',
                                                 ('company_id', '=', invoice.company_id.id),
                                                 ('company_id', '=', False)], limit=1)

    if partner:
        invoice.partner_id = partner
    else:
        new_partner = invoice.env['res.partner'].create({'name': nombre_emisor,
                                                         'vat': emisor,
                                                         'identification_id': tipo_emisor,
                                                         'type': 'contact',
                                                         'country_id': pais_emisor,
                                                         'phone': telefono_emisor,
                                                         'email': correo_emisor,
                                                         'street': otrassenas_emisor,
                                                         'supplier': 'True'})
        if new_partner:
            invoice.partner_id = new_partner
        else:
            raise UserError(_('The provider in the invoice does not exists. ' +
                              'I tried to created without success. Please review it.'))

    # invoice.account_id = partner.property_account_payable_id
    invoice.invoice_payment_term_id = partner.property_supplier_payment_term_id

    payment_method_node = invoice_xml.xpath("inv:MedioPago", namespaces=namespaces)
    if payment_method_node:
        invoice.payment_methods_id = invoice.env['payment.methods'].search([('sequence',
                                                                             '=',
                                                                             payment_method_node[0].text)], limit=1)
    else:
        invoice.payment_methods_id = partner.payment_methods_id

    _logger.debug('FECR - load_lines: %s - account: %s', (load_lines, account_id))

    product = False
    if product_id:
        product = product_id

    analytic_account = False
    if analytic_account_id:
        analytic_account = analytic_account_id.id

    # if load_lines and not invoice.invoice_line_ids:
    if load_lines:
        lines = invoice_xml.xpath("inv:DetalleServicio/inv:LineaDetalle", namespaces=namespaces)
        new_lines = []
        for line in lines:
            product_uom = invoice.env['uom.uom'].search([('code', '=', line.xpath("inv:UnidadMedida",
                                                                                  namespaces=namespaces)[0].text)],
                                                        limit=1).id
            total_amount = float(line.xpath("inv:MontoTotal", namespaces=namespaces)[0].text)

            discount_percentage = 0.0
            discount_note = None

            if total_amount > 0:
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
            taxes = []
            tax_nodes = line.xpath("inv:Impuesto", namespaces=namespaces)
            for tax_node in tax_nodes:
                tax_code = re.sub(r"[^0-9]+", "", tax_node.xpath("inv:Codigo", namespaces=namespaces)[0].text)
                tax_amount = float(tax_node.xpath("inv:Tarifa", namespaces=namespaces)[0].text)
                _logger.debug('FECR - tax_code: %s', tax_code)
                _logger.debug('FECR - tax_amount: %s', tax_amount)

                if product_id and product_id.non_tax_deductible:
                    tax = invoice.env['account.tax'].search([('tax_code', '=', tax_code),
                                                             ('amount', '=', tax_amount),
                                                             ('type_tax_use', '=', 'purchase'),
                                                             ('non_tax_deductible', '=', True),
                                                             ('active', '=', True)], limit=1)
                else:
                    tax = invoice.env['account.tax'].search([('tax_code', '=', tax_code),
                                                             ('amount', '=', tax_amount),
                                                             ('type_tax_use', '=', 'purchase'),
                                                             ('non_tax_deductible', '=', False),
                                                             ('active', '=', True)], limit=1)

                if tax:
                    total_tax += float(tax_node.xpath("inv:Monto", namespaces=namespaces)[0].text)

                    exonerations = tax_node.xpath("inv:Exoneracion", namespaces=namespaces)
                    if exonerations:
                        for exoneration_node in exonerations:
                            exoneration_percentage = float(exoneration_node.xpath("inv:PorcentajeExoneracion",
                                                                                  namespaces=namespaces)[0].text)
                            tax = invoice.env['account.tax'].search([('percentage_exoneration',
                                                                      '=',
                                                                      exoneration_percentage),
                                                                     ('type_tax_use', '=', 'purchase'),
                                                                     ('non_tax_deductible', '=', False),
                                                                     ('has_exoneration', '=', True),
                                                                     ('active', '=', True)], limit=1)
                            taxes.append((4, tax.id))
                    else:
                        taxes.append((4, tax.id))

                else:
                    if product_id and product_id.non_tax_deductible:
                        raise UserError(_(str('Tax code %s and percentage %s as non-tax ', (tax_code, tax_amount)) +
                                          'deductible is not registered in the system'))
                    raise UserError(_(str('Tax code %s and percentage %s is not ' % (tax_code, tax_amount)) +
                                      'registered in the system'))

            _logger.debug('E-INV CR - impuestos de linea: %s', (taxes))
            columns = {'name': line.xpath("inv:Detalle", namespaces=namespaces)[0].text,
                       'move_id': invoice.id,
                       'price_unit': line.xpath("inv:PrecioUnitario", namespaces=namespaces)[0].text,
                       'quantity': line.xpath("inv:Cantidad", namespaces=namespaces)[0].text,
                       'product_uom_id': product_uom,
                       'sequence': line.xpath("inv:NumeroLinea", namespaces=namespaces)[0].text,
                       'discount': discount_percentage,
                       'discount_note': discount_note,
                       'product_id': product,
                       'account_id': account_id.id,
                       'analytic_account_id': analytic_account,
                       'economic_activity_id': activity_id,
                       'tax_ids': taxes}
            new_lines.append((0, 0, columns))

        invoice.invoice_line_ids = new_lines

    invoice.amount_total_electronic_invoice = invoice_xml.xpath("inv:ResumenFactura/inv:TotalComprobante",
                                                                namespaces=namespaces)[0].text

    tax_node = invoice_xml.xpath("inv:ResumenFactura/inv:TotalImpuesto", namespaces=namespaces)
    if tax_node:
        invoice.amount_tax_electronic_invoice = tax_node[0].text
    invoice._compute_amount()


def p12_expiration_date(p12file, password):
    try:
        pkcs12 = crypto.load_pkcs12(base64.b64decode(p12file), password)
        data = crypto.dump_certificate(crypto.FILETYPE_PEM, pkcs12.get_certificate())
        cert = x509.load_pem_x509_certificate(data, default_backend())
        return cert.not_valid_after
    except crypto.Error as crypte:
        exc_str = str(crypte)
        if exc_str.find('mac verify failure'):
            raise
        raise
