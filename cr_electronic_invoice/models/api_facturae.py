import requests
import random
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
from odoo.exceptions import UserError
from xml.sax.saxutils import escape

try:
    from lxml import etree
except ImportError:
    from xml.etree import ElementTree

try:
    #import xmlsig
    from .. import signature
    from OpenSSL import crypto
except(ImportError, IOError) as err:
    logging.info(err)

#PARA VALIDAR JSON DE RESPUESTA
from .. import extensions

_logger = logging.getLogger(__name__)


def sign_file2(cert, password, xml):
    min = 1
    max = 99999
    signature_id = 'Signature-%05d' % random.randint(min, max)
    #signed_properties_id = signature_id + '-SignedProperties%05d' \
    #                       % random.randint(min, max)


    signed_properties_id = 'SignedProperties-' + signature_id

    #key_info_id = 'KeyInfo%05d' % random.randint(min, max)
    key_info_id = 'KeyInfoId-' + signature_id
    reference_id = 'Reference-%05d' % random.randint(min, max)
    object_id = 'XadesObjectId-%05d' % random.randint(min, max)
    etsi = 'http://uri.etsi.org/01903/v1.3.2#'
    #sig_policy_identifier = 'http://www.facturae.es/' \
    #                        'politica_de_firma_formato_facturae/' \
    #                        'politica_de_firma_formato_facturae_v3_1' \
    #                        '.pdf'

    #sig_policy_identifier = 'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4/' \
    #                        'Resolucion%20Comprobantes%20Electronicos%20%20DGT-R-48-2016.pdf'

    sig_policy_identifier = 'https://tribunet.hacienda.go.cr/docs/esquemas/2016/v4/Resolucion%20Comprobantes%20Electronicos%20%20DGT-R-48-2016.pdf'

    sig_policy_hash_value = 'V8lVVNGDCPen6VELRD1Ja8HARFk='
    #root = etree.fromstring(xml)

    xml_decoder = base64decode(xml)
    xml_no_bytes = base64UTF8Decoder(xml_decoder)

    #root = etree.fromstring(xml, etree.XMLParser(remove_blank_text=True))
    root = etree.fromstring(xml_no_bytes)

    #sign = xmlsig.template.create(
    sign = signature.template.create(
        c14n_method=signature.constants.TransformInclC14N,
        sign_method=signature.constants.TransformRsaSha256,
        name=signature_id,
        ns="ds"
    )

    #sign = create_sign_node(
    #    c14n_method=xmlsig.constants.TransformInclC14N,
    #    sign_method=xmlsig.constants.TransformRsaSha256,
    #    name=signature_id,
    #    ns="ds"
    #)

    #key_info = xmlsig.template.ensure_key_info(
    key_info = signature.template.ensure_key_info(
        sign,
        name=key_info_id
    )

    #key_info= ensure_key_info_fe(
    #    sign,
    #    name=key_info_id
    #)

    #x509_data = xmlsig.template.add_x509_data(key_info)
    x509_data = signature.template.add_x509_data(key_info)
    #x509_data = add_x509_data_fe(key_info)

    #xmlsig.template.x509_data_add_certificate(x509_data)
    signature.template.x509_data_add_certificate(x509_data)

    #x509_data_add_certificate_fe(x509_data)

    #xmlsig.template.add_key_value(key_info)
    signature.template.add_key_value(key_info)
    #add_key_value_fe(key_info)

    certificate = crypto.load_pkcs12(base64.b64decode(cert), password)

    ref = signature.template.add_reference(
        sign,
        signature.constants.TransformSha256,
        name=reference_id,
        uri=""
    )

    #xmlsig.template.add_transform(
    signature.template.add_transform(
        ref,
        signature.constants.TransformEnveloped
    )

    signature.template.add_reference(
        sign,
        signature.constants.TransformSha256,
        uri='#' + key_info_id,
        name='ReferenceKeyInfo'
    )

    signature.template.add_reference(
        sign,
        signature.constants.TransformSha256,
        uri='#' + signed_properties_id,
        uri_type='http://uri.etsi.org/01903#SignedProperties'
    )

    object_node = etree.SubElement(
        sign,
        etree.QName(signature.constants.DSigNs, 'Object'),
        #nsmap={'xades': etsi},
        attrib={signature.constants.ID_ATTR: object_id}
    )

    qualifying_properties = etree.SubElement(
        object_node,
        etree.QName(etsi, 'QualifyingProperties'),
        nsmap={'xades': etsi},
        attrib={
            signature.constants.ID_ATTR: 'QualifyingProperties-44587',
            'Target': '#' + signature_id
        }
    )

    signed_properties = etree.SubElement(
        qualifying_properties,
        etree.QName(etsi, 'SignedProperties'),
        attrib={
            signature.constants.ID_ATTR: signed_properties_id
        }
    )

    signed_signature_properties = etree.SubElement(
        signed_properties,
        etree.QName(etsi, 'SignedSignatureProperties')
    )

    #now = datetime.now().replace(
    #    microsecond=0, tzinfo=pytz.utc
    #)

    etree.SubElement(
        signed_signature_properties,
        etree.QName(etsi, 'SigningTime')
    ).text = get_time_hacienda()

    signing_certificate = etree.SubElement(
        signed_signature_properties,
        etree.QName(etsi, 'SigningCertificate')
    )

    signing_certificate_cert = etree.SubElement(
        signing_certificate,
        etree.QName(etsi, 'Cert')
    )

    cert_digest = etree.SubElement(
        signing_certificate_cert,
        etree.QName(etsi, 'CertDigest')
    )

    #ESTE NODO TIENEN PROBLEMAS PUESTO QUE SOLO CARGA EN
    etree.SubElement(
        cert_digest,
        etree.QName(signature.constants.DSigNs, 'DigestMethod'),
        #etree.QName('http://www.w3.org/2001/04/xmlenc#sha256', 'DigestMethod'),
        #xmlsig.constants.TransformSha256,
        attrib={
            #'Algorithm': 'http://www.w3.org/2000/09/xmldsig#sha1'
            'Algorithm': 'http://www.w3.org/2001/04/xmlenc#sha256'
        }
    )

    hash_cert = hashlib.sha256(
        crypto.dump_certificate(
            crypto.FILETYPE_ASN1,
            certificate.get_certificate()
        )
    )

    #ESTE TAMBIEN TIENE PROBLEMAS NO GENERA EL DIGEST VALUE EN SHA 256
    etree.SubElement(
        cert_digest,
        etree.QName(signature.constants.DSigNs, 'DigestValue')
    ).text = base64.b64encode(hash_cert.digest())


    issuer_serial = etree.SubElement(
        signing_certificate_cert,
        etree.QName(etsi, 'IssuerSerial')
    )

    etree.SubElement(
        issuer_serial,
        etree.QName(signature.constants.DSigNs, 'X509IssuerName')
    ).text = signature.utils.get_rdns_name(
        certificate.get_certificate().to_cryptography().issuer.rdns)

    etree.SubElement(
        issuer_serial,
        etree.QName(signature.constants.DSigNs, 'X509SerialNumber')
    ).text = str(certificate.get_certificate().get_serial_number())

    signature_policy_identifier = etree.SubElement(
        signed_signature_properties,
        etree.QName(etsi, 'SignaturePolicyIdentifier')
    )

    signature_policy_id = etree.SubElement(
        signature_policy_identifier,
        etree.QName(etsi, 'SignaturePolicyId')
    )
    sig_policy_id = etree.SubElement(
        signature_policy_id,
        etree.QName(etsi, 'SigPolicyId')
    )
    etree.SubElement(
        sig_policy_id,
        etree.QName(etsi, 'Identifier')
    ).text = sig_policy_identifier

    #HACIENDA NO PIDE ESTE NODO
    #etree.SubElement(
    #    sig_policy_id,
    #    etree.QName(etsi, 'Description')
    #).text = "Política de Firma FacturaE v3.1"

    sig_policy_hash = etree.SubElement(
        signature_policy_id,
        etree.QName(etsi, 'SigPolicyHash')
    )

    etree.SubElement(
        sig_policy_hash,
        etree.QName(signature.constants.DSigNs, 'DigestMethod'),
        attrib={
            'Algorithm': 'http://www.w3.org/2000/09/xmldsig#sha1'
        }
    )

    #try:
    #    remote = urllib.request.urlopen(sig_policy_identifier)
    #    hash_value = base64.b64encode(hashlib.sha1(remote.read()).digest())
        #hacemos este cambio porque estamos encodeando el valor
    #except urllib.request.HTTPError:
    #    hash_value = sig_policy_hash_value

    etree.SubElement(
        sig_policy_hash,
        etree.QName(signature.constants.DSigNs, 'DigestValue')
    ).text = sig_policy_hash_value

    signer_role = etree.SubElement(
        signed_signature_properties,
        etree.QName(etsi, 'SignerRole')
    )
    claimed_roles = etree.SubElement(
        signer_role,
        etree.QName(etsi, 'ClaimedRoles')
    )
    etree.SubElement(
        claimed_roles,
        etree.QName(etsi, 'ClaimedRole')
    ).text = 'supplier'

    signed_data_object_properties = etree.SubElement(
        signed_properties,
        etree.QName(etsi, 'SignedDataObjectProperties')
    )

    data_object_format = etree.SubElement(
        signed_data_object_properties,
        etree.QName(etsi, 'DataObjectFormat'),
        attrib={
            'ObjectReference': '#' + reference_id
        }
    )

    etree.SubElement(
        data_object_format,
        etree.QName(etsi, 'MimeType')
    ).text = 'text/xml'

    etree.SubElement(
        data_object_format,
        etree.QName(etsi, 'Encoding')
    ).text = 'UTF-8'

    ctx = signature.SignatureContext()
    key = crypto.load_pkcs12(base64.b64decode(cert), password)

    ctx.x509 = key.get_certificate().to_cryptography()
    ctx.public_key = ctx.x509.public_key()
    ctx.private_key = key.get_privatekey().to_cryptography_key()

    root.append(sign)
    ctx.sign(sign)

    return etree.tostring(
        root
    )


def get_time_hacienda():
    now_utc = datetime.datetime.now(pytz.timezone('UTC'))
    now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
    date_cr = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")

    return date_cr


#Utilizada para establecer un limite de caracteres en la cedula del cliente, no mas de 20
#de lo contrario hacienda lo rechaza
def limit(str, limit):
    return (str[:limit - 3] + '...') if len(str) > limit else str


def get_mr_sequencevalue(inv):

    '''Verificamos si el ID del mensaje receptor es válido'''
    mr_mensaje_id = int(inv.state_invoice_partner)
    if mr_mensaje_id < 1 and mr_mensaje_id > 3:
        raise UserError('El ID del mensaje receptor es inválido.')
    elif mr_mensaje_id is None:
        raise UserError('No se ha proporcionado un ID válido para el MR.')

    if inv.state_invoice_partner == '1':
        detalle_mensaje = 'Aceptado'
        tipo = 1
        tipo_documento = fe_enums.TipoDocumento.CCE.name
        sequence = inv.env['ir.sequence'].next_by_code('sequece.electronic.doc.confirmation')

    elif inv.state_invoice_partner == '2':
        detalle_mensaje = 'Aceptado parcial'
        tipo = 2
        tipo_documento = fe_enums.TipoDocumento.CPCE.name
        sequence = inv.env['ir.sequence'].next_by_code('sequece.electronic.doc.partial.confirmation')
    else:
        detalle_mensaje = 'Rechazado'
        tipo = 3
        tipo_documento = fe_enums.TipoDocumento.RCE.name
        sequence = inv.env['ir.sequence'].next_by_code('sequece.electronic.doc.reject')

    return {'detalle_mensaje': detalle_mensaje, 'tipo': tipo, 'tipo_documento': tipo_documento, 'sequence': sequence}


def get_consecutivo_hacienda(tipo_documento, consecutivo, sucursal_id, terminal_id):

    if tipo_documento == 'FE':
        tipo_doc = fe_enums.TipoDocumento.FE.value
    elif tipo_documento == 'NC':
        tipo_doc = fe_enums.TipoDocumento.NC.value
    elif tipo_documento == 'ND':
        tipo_doc = fe_enums.TipoDocumento.ND.value
    elif tipo_documento == 'TE':
        tipo_doc = fe_enums.TipoDocumento.TE.value
    elif tipo_documento == 'CCE':
        tipo_doc = fe_enums.TipoDocumento.CCE.value
    elif tipo_documento == 'CPCE':
        tipo_doc = fe_enums.TipoDocumento.CPCE.value
    else:
        tipo_doc = fe_enums.TipoDocumento.RCE.value

    inv_consecutivo = str(consecutivo).zfill(10)
    inv_sucursal = str(sucursal_id).zfill(3)
    inv_terminal = str(terminal_id).zfill(5)

    consecutivo_mh = inv_sucursal + inv_terminal + tipo_doc + inv_consecutivo

    return consecutivo_mh


def get_clave_hacienda(self, tipo_documento, consecutivo, sucursal_id, terminal_id, situacion='normal'):

    if tipo_documento == 'FE':
        tipo_doc = fe_enums.TipoDocumento.FE.value
    elif tipo_documento == 'NC':
        tipo_doc = fe_enums.TipoDocumento.NC.value
    elif tipo_documento == 'ND':
        tipo_doc = fe_enums.TipoDocumento.ND.value
    elif tipo_documento == 'TE':
        tipo_doc = fe_enums.TipoDocumento.TE.value
    elif tipo_documento == 'CCE':
        tipo_doc = fe_enums.TipoDocumento.CCE.value
    elif tipo_documento == 'CPCE':
        tipo_doc = fe_enums.TipoDocumento.CPCE.value
    else:
        tipo_doc = fe_enums.TipoDocumento.RCE.value

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
        raise UserError('Seleccione el tipo de identificación del emisor en el pérfil de la compañía')

    '''Obtenemos el número de identificación del Emisor y lo validamos númericamente'''
    inv_cedula = re.sub('[^0-9]', '', self.company_id.vat)

    '''Validamos el largo de la cadena númerica de la cédula del emisor'''
    if self.company_id.identification_id.code == '01' and len(inv_cedula) != 9:
        raise UserError('La Cédula Física del emisor debe de tener 9 dígitos')
    elif self.company_id.identification_id.code == '02' and len(inv_cedula) != 10:
        raise UserError('La Cédula Jurídica del emisor debe de tener 10 dígitos')
    elif self.company_id.identification_id.code == '03' and (len(inv_cedula) != 11 or len(inv_cedula) != 12):
        raise UserError('La identificación DIMEX del emisor debe de tener 11 o 12 dígitos')
    elif self.company_id.identification_id.code == '04' and len(inv_cedula) != 10:
        raise UserError('La identificación NITE del emisor debe de tener 10 dígitos')

    inv_cedula = str(inv_cedula).zfill(12)

    '''Limitamos la cedula del emisor a 20 caracteres o nos dará error'''
    cedula_emisor = limit(inv_cedula, 20)

    '''Validamos la situación del comprobante electrónico'''
    if situacion == 'normal':
        situacion_comprobante = fe_enums.SituacionComprobante.normal.value
    elif situacion == 'contingencia':
        situacion_comprobante = fe_enums.SituacionComprobante.contingencia.value
    elif situacion == 'sininternet':
        situacion_comprobante = fe_enums.SituacionComprobante.sininternet.value
    else:
        raise UserError('La situación indicada para el comprobante electŕonico es inválida: ' + situacion)

    '''Creamos la fecha para la clave'''
    now_utc = datetime.datetime.now(pytz.timezone('UTC'))
    now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))

    cur_date = now_cr.strftime("%d%m%y")

    codigo_pais = self.company_id.phone_code

    '''Creamos un código de seguridad random'''
    codigo_seguridad = str(random.randint(1, 99999999)).zfill(8)

    clave_hacienda = codigo_pais + cur_date + cedula_emisor + consecutivo_mh + situacion_comprobante + codigo_seguridad

    return {'length': len(clave_hacienda), 'clave': clave_hacienda, 'consecutivo': consecutivo_mh}


'''Variables para poder manejar el Refrescar del Token'''
last_tokens = {}
last_tokens_time = {}


def get_token_hacienda(inv, tipo_ambiente):
    token = last_tokens.get(inv.company_id.id, False)
    token_time = last_tokens_time.get(inv.company_id.id, False)
    current_time = time.time()

    if token and (current_time - token_time < 280):
        token_hacienda = token
    else:
        headers = {}
        data = {'client_id': tipo_ambiente,
                'client_secret': '',
                'grant_type': fe_enums.GrandTypes.TypePassword.value,
                'username': inv.company_id.frm_ws_identificador,
                'password': inv.company_id.frm_ws_password
                }

        # establecer el ambiente al cual me voy a conectar
        if tipo_ambiente == 'api-stag':
            endpoint = fe_enums.UrlHaciendaToken.apistag.value
        else:
            endpoint = fe_enums.UrlHaciendaToken.apiprod.value

        try:
            # enviando solicitud post y guardando la respuesta como un objeto json
            response = requests.request("POST", endpoint, data=data, headers=headers)
            response_json = response.json()

            respuesta = extensions.response_validator.assert_valid_schema(response_json, 'token.json')

            if 200 <= response.status_code <= 299:
                token_hacienda = response_json.get('access_token')
                last_tokens[inv.company_id.id] = token
                last_tokens_time[inv.company_id.id] = time.time()
            else:
                _logger.error('MAB - token_hacienda failed.  error: %s', response.status_code)

        except requests.exceptions.RequestException as e:
            raise Warning('Error Obteniendo el Token desde MH. Excepcion %s' % e)

    return token_hacienda


def refresh_token_hacienda(tipo_ambiente, token):

    headers = {}
    data = {'client_id': tipo_ambiente,
            'client_secret': '',
            'grant_type': fe_enums.GrandTypes.TypeRefresh.value,
            'refresh_token': token
            }

    # establecer el ambiente al cual me voy a conectar
    if tipo_ambiente == 'api-stag':
        endpoint = fe_enums.UrlHaciendaToken.apistag.value
    else:
        endpoint = fe_enums.UrlHaciendaToken.apiprod.value

    try:
        # enviando solicitud post y guardando la respuesta como un objeto json
        response = requests.request("POST", endpoint, data=data, headers=headers)
        response_json = response.json()
        token_hacienda = response_json.get('access_token')
        return token_hacienda
    except ImportError:
        raise Warning('Error Refrescando el Token desde MH')


def gen_xml_mr(clave, cedula_emisor, fecha_emision, id_mensaje, detalle_mensaje, cedula_receptor, consecutivo_receptor,
               monto_impuesto=0, total_factura=0):

    '''Verificamos si la clave indicada corresponde a un numeros'''
    mr_clave = re.sub('[^0-9]', '', clave)
    if len(mr_clave) != 50:
        raise UserError('La clave a utilizar es inválida. Debe contener al menos 50 digitos')

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
        raise UserError('No se ha proporcionado una cédula de receptor válida para el MR.')

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
    sb.Append('<?xml version="1.0" encoding="utf-8"?>')
    sb.Append('<MensajeReceptor xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/mensajeReceptor" ')
    sb.Append('xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsd="http://www.w3.org/2001/XMLSchema" ')
    sb.Append('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append(
        'xsi:schemaLocation="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/mensajeReceptor MensajeReceptor_4.2.xsd">')
    sb.Append('<Clave>' + mr_clave + '</Clave>')
    sb.Append('<NumeroCedulaEmisor>' + mr_cedula_emisor + '</NumeroCedulaEmisor>')
    sb.Append('<FechaEmisionDoc>' + mr_fecha_emision + '</FechaEmisionDoc>')
    sb.Append('<Mensaje>' + str(mr_mensaje_id) + '</Mensaje>')

    if mr_detalle_mensaje is not None:
        sb.Append('<DetalleMensaje>' + escape(mr_detalle_mensaje) + '</DetalleMensaje>')

    if mr_monto_impuesto is not None and mr_monto_impuesto > 0:
        sb.Append('<MontoTotalImpuesto>' + str(mr_monto_impuesto) + '</MontoTotalImpuesto>')

    if mr_total_factura is not None and mr_total_factura > 0:
        sb.Append('<TotalFactura>' + str(mr_total_factura) + '</TotalFactura>')
    else:
        raise UserError('El monto Total de la Factura para el Mensaje Receptro es inválido')

    sb.Append('<NumeroCedulaReceptor>' + mr_cedula_receptor + '</NumeroCedulaReceptor>')
    sb.Append('<NumeroConsecutivoReceptor>' + mr_consecutivo_receptor + '</NumeroConsecutivoReceptor>')
    sb.Append('</MensajeReceptor>')

    mreceptor_bytes = str(sb)
    mr_to_base64 = stringToBase64(mreceptor_bytes)

    return base64UTF8Decoder(mr_to_base64)


def gen_xml_fe(inv,consecutivo, date, sale_conditions, medio_pago, total_servicio_gravado, total_servicio_exento,
               total_mercaderia_gravado, total_mercaderia_exento, base_total, total_impuestos, total_descuento,
               lines, currency_rate, invoice_comments):

    numero_linea = 0

    sb = StringBuilder()
    sb.Append('<?xml version="1.0" encoding="utf-8"?>')
    sb.Append('<FacturaElectronica xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/facturaElectronica" ')
    sb.Append('xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsd="http://www.w3.org/2001/XMLSchema" ')
    sb.Append('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append('xsi:schemaLocation="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/facturaElectronicaFacturaElectronica_V.4.2.xsd">')

    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<NumeroConsecutivo>' + consecutivo + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + date + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' + escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append('<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' + escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' + re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' + str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')
    sb.Append('<Receptor>')
    sb.Append('<Nombre>' + escape(str(inv.partner_id.name[:80])) + '</Nombre>')

    if inv.partner_id.identification_id.code == '05':
        sb.Append('<IdentificacionExtranjero>' + inv.partner_id.vat + '</IdentificacionExtranjero>')
    else:
        sb.Append('<Identificacion>')
        sb.Append('<Tipo>' + inv.partner_id.identification_id.code + '</Tipo>')
        sb.Append('<Numero>' + inv.partner_id.vat + '</Numero>')
        sb.Append('</Identificacion>')

    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + str(inv.partner_id.state_id.code or '') + '</Provincia>')
    sb.Append('<Canton>' + str(inv.partner_id.county_id.code or '') + '</Canton>')
    sb.Append('<Distrito>' + str(inv.partner_id.district_id.code or '') + '</Distrito>')
    sb.Append('<Barrio>' + str(inv.partner_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' + escape(str(inv.partner_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.partner_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' + re.sub('[^0-9]+', '', inv.partner_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' + str(inv.partner_id.email) + '</CorreoElectronico>')
    sb.Append('</Receptor>')
    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.Append('<PlazoCredito>' + str(inv.partner_id.property_payment_term_id.line_ids[0].days or 0) + '</PlazoCredito>')
    sb.Append('<MedioPago>' + medio_pago + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')
        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' + str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' + str(v['precioUnitario']) + '</PrecioUnitario>')
        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
        if v.get('montoDescuento'):
            sb.Append('<MontoDescuento>' + str(v['montoDescuento']) + '</MontoDescuento>')
        if v.get('naturalezaDescuento'):
            sb.Append('<NaturalezaDescuento>' + str(v['naturalezaDescuento']) + '</NaturalezaDescuento>')
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
                        sb.Append('<TipoDocumento>' + d['tipoDocumento'] + '</TipoDocumento>')
                        sb.Append('<NumeroDocumento>' + d['numeroDocumento'] + '</NumeroDocumento>')
                        sb.Append('<NombreInstitucion>' + d['nombreInstitucion'] + '</NombreInstitucion>')
                        sb.Append('<FechaEmision>' + d['fechaEmision'] + '</FechaEmision>')
                        sb.Append('<MontoImpuesto>' + d['montoImpuesto'] + '</MontoImpuesto>')
                        sb.Append('<PorcentajeCompra>' + d['porcentajeCompra'] + '</PorcentajeCompra>')

                sb.Append('</Impuesto>')
        sb.Append('<MontoTotalLinea>' + str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')
    sb.Append('</DetalleServicio>')
    sb.Append('<ResumenFactura>')
    sb.Append('<CodigoMoneda>' + str(inv.currency_id.name) + '</CodigoMoneda>')
    sb.Append('<TipoCambio>' + str(currency_rate) + '</TipoCambio>')
    sb.Append('<TotalServGravados>' + str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' + str(total_servicio_exento) + '</TotalServExentos>')
    sb.Append('<TotalMercanciasGravadas>' + str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' + str(total_mercaderia_exento) + '</TotalMercanciasExentas>')
    sb.Append('<TotalGravado>' + str(total_servicio_gravado + total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento + total_mercaderia_exento) + '</TotalExento>')
    sb.Append('<TotalVenta>' + str(total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento) + '</TotalVenta>')
    sb.Append('<TotalDescuentos>' + str(round(total_descuento, 2)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' + str(round(base_total, 2)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' + str(round(total_impuestos, 2)) + '</TotalImpuesto>')
    sb.Append('<TotalComprobante>' + str(round(base_total + total_impuestos, 2)) + '</TotalComprobante>')
    sb.Append('</ResumenFactura>')
    sb.Append('<Normativa>')
    sb.Append('<NumeroResolucion>DGT-R-48-2016</NumeroResolucion>')
    sb.Append('<FechaResolucion>07-10-2016 08:00:00</FechaResolucion>')
    sb.Append('</Normativa>')
    sb.Append('<Otros>')
    sb.Append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
    sb.Append('</Otros>')

    sb.Append('</FacturaElectronica>')

    felectronica_bytes = str(sb)

    return stringToBase64(felectronica_bytes)


def gen_xml_nc(inv, consecutivo, date, sale_conditions, medio_pago, total_servicio_gravado,
                     total_servicio_exento, total_mercaderia_gravado, total_mercaderia_exento, base_total,
                     total_impuestos, total_descuento,lines,
                     tipo_documento_referencia, numero_documento_referencia, fecha_emision_referencia,
                     codigo_referencia, razon_referencia, currency_rate, invoice_comments):

    numero_linea = 0

    sb = StringBuilder()
    sb.Append('<?xml version="1.0" encoding="utf-8"?>')
    sb.Append('<NotaCreditoElectronica xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/notaCreditoElectronica" ')
    sb.Append('xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsd="http://www.w3.org/2001/XMLSchema" ')
    sb.Append('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append('xsi:schemaLocation="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/notaCreditoElectronicaNotaCreditoElectronica_V4.2.xsd">')

    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<NumeroConsecutivo>' + consecutivo + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + date + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' + escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append('<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' + escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' + re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' + str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')
    sb.Append('<Receptor>')
    sb.Append('<Nombre>' + escape(str(inv.partner_id.name[:80])) + '</Nombre>')

    if inv.partner_id.identification_id.code == '05':
        sb.Append('<IdentificacionExtranjero>' + inv.partner_id.vat + '</IdentificacionExtranjero>')
    else:
        sb.Append('<Identificacion>')
        sb.Append('<Tipo>' + inv.partner_id.identification_id.code + '</Tipo>')
        sb.Append('<Numero>' + inv.partner_id.vat + '</Numero>')
        sb.Append('</Identificacion>')

    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + str(inv.partner_id.state_id.code or '') + '</Provincia>')
    sb.Append('<Canton>' + str(inv.partner_id.county_id.code or '') + '</Canton>')
    sb.Append('<Distrito>' + str(inv.partner_id.district_id.code or '') + '</Distrito>')
    sb.Append('<Barrio>' + str(inv.partner_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' + str(inv.partner_id.street or 'NA') + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.partner_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' + re.sub('[^0-9]+', '', inv.partner_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' + str(inv.partner_id.email) + '</CorreoElectronico>')
    sb.Append('</Receptor>')
    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.Append('<PlazoCredito>' + str(inv.partner_id.property_payment_term_id.line_ids[0].days or 0) + '</PlazoCredito>')
    sb.Append('<MedioPago>' + medio_pago + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')
        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' + str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' + str(v['precioUnitario']) + '</PrecioUnitario>')

        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
        if v.get('montoDescuento'):
            sb.Append('<MontoDescuento>' + str(v['montoDescuento']) + '</MontoDescuento>')
        if v.get('naturalezaDescuento'):
            sb.Append('<NaturalezaDescuento>' + str(v['naturalezaDescuento']) + '</NaturalezaDescuento>')
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
                        sb.Append('<TipoDocumento>' + d['tipoDocumento'] + '</TipoDocumento>')
                        sb.Append('<NumeroDocumento>' + d['numeroDocumento'] + '</NumeroDocumento>')
                        sb.Append('<NombreInstitucion>' + d['nombreInstitucion'] + '</NombreInstitucion>')
                        sb.Append('<FechaEmision>' + d['fechaEmision'] + '</FechaEmision>')
                        sb.Append('<MontoImpuesto>' + str(d['montoImpuesto']) + '</MontoImpuesto>')
                        sb.Append('<PorcentajeCompra>' + str(d['porcentajeCompra']) + '</PorcentajeCompra>')

                sb.Append('</Impuesto>')
        sb.Append('<MontoTotalLinea>' + str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')
    sb.Append('</DetalleServicio>')
    sb.Append('<ResumenFactura>')
    sb.Append('<CodigoMoneda>' + str(inv.currency_id.name) + '</CodigoMoneda>')
    sb.Append('<TipoCambio>' + str(currency_rate) + '</TipoCambio>')
    sb.Append('<TotalServGravados>' + str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' + str(total_servicio_exento) + '</TotalServExentos>')
    sb.Append('<TotalMercanciasGravadas>' + str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' + str(total_mercaderia_exento) + '</TotalMercanciasExentas>')
    sb.Append('<TotalGravado>' + str(total_servicio_gravado + total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento + total_mercaderia_exento) + '</TotalExento>')
    sb.Append('<TotalVenta>' + str(
        total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento) + '</TotalVenta>')
    sb.Append('<TotalDescuentos>' + str(round(total_descuento, 2)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' + str(round(base_total, 2)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' + str(round(total_impuestos, 2)) + '</TotalImpuesto>')
    sb.Append('<TotalComprobante>' + str(round(base_total + total_impuestos, 2)) + '</TotalComprobante>')
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
    sb.Append('<Otros>')
    sb.Append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
    sb.Append('</Otros>')
    sb.Append('</NotaCreditoElectronica>')

    ncelectronica_bytes = str(sb)

    return stringToBase64(ncelectronica_bytes)


def gen_xml_nd(inv, consecutivo, date, sale_conditions, medio_pago, total_servicio_gravado,
                     total_servicio_exento, total_mercaderia_gravado, total_mercaderia_exento, base_total,
                     total_impuestos, total_descuento, lines,
                     tipo_documento_referencia, numero_documento_referencia, fecha_emision_referencia,
                     codigo_referencia, razon_referencia, currency_rate, invoice_comments):


    numero_linea = 0

    sb = StringBuilder()
    sb.Append('<?xml version="1.0" encoding="utf-8"?>')
    sb.Append('<NotaDebitoElectronica xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/notaDebitoElectronica" ')
    sb.Append('xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsd="http://www.w3.org/2001/XMLSchema" ')
    sb.Append('xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
    sb.Append(
        'xsi:schemaLocation="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/notaCreditoElectronicaNotaCreditoElectronica_V4.2.xsd">')

    sb.Append('<Clave>' + inv.number_electronic + '</Clave>')
    sb.Append('<NumeroConsecutivo>' + consecutivo + '</NumeroConsecutivo>')
    sb.Append('<FechaEmision>' + date + '</FechaEmision>')
    sb.Append('<Emisor>')
    sb.Append('<Nombre>' + escape(inv.company_id.name) + '</Nombre>')
    sb.Append('<Identificacion>')
    sb.Append('<Tipo>' + inv.company_id.identification_id.code + '</Tipo>')
    sb.Append('<Numero>' + inv.company_id.vat + '</Numero>')
    sb.Append('</Identificacion>')
    sb.Append('<NombreComercial>' + escape(str(inv.company_id.commercial_name or 'NA')) + '</NombreComercial>')
    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + inv.company_id.state_id.code + '</Provincia>')
    sb.Append('<Canton>' + inv.company_id.county_id.code + '</Canton>')
    sb.Append('<Distrito>' + inv.company_id.district_id.code + '</Distrito>')
    sb.Append('<Barrio>' + str(inv.company_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' + escape(str(inv.company_id.street or 'NA')) + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.company_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' + re.sub('[^0-9]+', '', inv.company_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' + str(inv.company_id.email) + '</CorreoElectronico>')
    sb.Append('</Emisor>')
    sb.Append('<Receptor>')
    sb.Append('<Nombre>' + escape(str(inv.partner_id.name[:80])) + '</Nombre>')

    if inv.partner_id.identification_id.code == '05':
        sb.Append('<IdentificacionExtranjero>' + inv.partner_id.vat + '</IdentificacionExtranjero>')
    else:
        sb.Append('<Identificacion>')
        sb.Append('<Tipo>' + inv.partner_id.identification_id.code + '</Tipo>')
        sb.Append('<Numero>' + inv.partner_id.vat + '</Numero>')
        sb.Append('</Identificacion>')

    sb.Append('<Ubicacion>')
    sb.Append('<Provincia>' + str(inv.partner_id.state_id.code or '') + '</Provincia>')
    sb.Append('<Canton>' + str(inv.partner_id.county_id.code or '') + '</Canton>')
    sb.Append('<Distrito>' + str(inv.partner_id.district_id.code or '') + '</Distrito>')
    sb.Append('<Barrio>' + str(inv.partner_id.neighborhood_id.code or '00') + '</Barrio>')
    sb.Append('<OtrasSenas>' + str(inv.partner_id.street or 'NA') + '</OtrasSenas>')
    sb.Append('</Ubicacion>')
    sb.Append('<Telefono>')
    sb.Append('<CodigoPais>' + inv.partner_id.phone_code + '</CodigoPais>')
    sb.Append('<NumTelefono>' + re.sub('[^0-9]+', '', inv.partner_id.phone) + '</NumTelefono>')
    sb.Append('</Telefono>')
    sb.Append('<CorreoElectronico>' + str(inv.partner_id.email) + '</CorreoElectronico>')
    sb.Append('</Receptor>')
    sb.Append('<CondicionVenta>' + sale_conditions + '</CondicionVenta>')
    sb.Append('<PlazoCredito>' + str(inv.partner_id.property_payment_term_id.line_ids[0].days or 0) + '</PlazoCredito>')
    sb.Append('<MedioPago>' + medio_pago + '</MedioPago>')
    sb.Append('<DetalleServicio>')

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = numero_linea + 1

        sb.Append('<LineaDetalle>')
        sb.Append('<NumeroLinea>' + str(numero_linea) + '</NumeroLinea>')
        sb.Append('<Cantidad>' + str(v['cantidad']) + '</Cantidad>')
        sb.Append('<UnidadMedida>' + str(v['unidadMedida']) + '</UnidadMedida>')
        sb.Append('<Detalle>' + str(v['detalle']) + '</Detalle>')
        sb.Append('<PrecioUnitario>' + str(v['precioUnitario']) + '</PrecioUnitario>')
        sb.Append('<MontoTotal>' + str(v['montoTotal']) + '</MontoTotal>')
        if v.get('montoDescuento'):
            sb.Append('<MontoDescuento>' + str(v['montoDescuento']) + '</MontoDescuento>')
        if v.get('naturalezaDescuento'):
            sb.Append('<NaturalezaDescuento>' + v['naturalezaDescuento'] + '</NaturalezaDescuento>')
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
                        sb.Append('<TipoDocumento>' + d['tipoDocumento'] + '</TipoDocumento>')
                        sb.Append('<NumeroDocumento>' + d['numeroDocumento'] + '</NumeroDocumento>')
                        sb.Append('<NombreInstitucion>' + d['nombreInstitucion'] + '</NombreInstitucion>')
                        sb.Append('<FechaEmision>' + d['fechaEmision'] + '</FechaEmision>')
                        sb.Append('<MontoImpuesto>' + str(d['montoImpuesto']) + '</MontoImpuesto>')
                        sb.Append('<PorcentajeCompra>' + str(d['porcentajeCompra']) + '</PorcentajeCompra>')

                sb.Append('</Impuesto>')
        sb.Append('<MontoTotalLinea>' + str(v['montoTotalLinea']) + '</MontoTotalLinea>')
        sb.Append('</LineaDetalle>')

    sb.Append('</DetalleServicio>')
    sb.Append('<ResumenFactura>')
    sb.Append('<CodigoMoneda>' + str(inv.currency_id.name) + '</CodigoMoneda>')
    sb.Append('<TipoCambio>' + str(currency_rate) + '</TipoCambio>')
    sb.Append('<TotalServGravados>' + str(total_servicio_gravado) + '</TotalServGravados>')
    sb.Append('<TotalServExentos>' + str(total_servicio_exento) + '</TotalServExentos>')
    sb.Append('<TotalMercanciasGravadas>' + str(total_mercaderia_gravado) + '</TotalMercanciasGravadas>')
    sb.Append('<TotalMercanciasExentas>' + str(total_mercaderia_exento) + '</TotalMercanciasExentas>')
    sb.Append('<TotalGravado>' + str(total_servicio_gravado + total_mercaderia_gravado) + '</TotalGravado>')
    sb.Append('<TotalExento>' + str(total_servicio_exento + total_mercaderia_exento) + '</TotalExento>')
    sb.Append('<TotalVenta>' + str(
        total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento) + '</TotalVenta>')
    sb.Append('<TotalDescuentos>' + str(round(total_descuento, 2)) + '</TotalDescuentos>')
    sb.Append('<TotalVentaNeta>' + str(round(base_total, 2)) + '</TotalVentaNeta>')
    sb.Append('<TotalImpuesto>' + str(round(total_impuestos, 2)) + '</TotalImpuesto>')
    sb.Append('<TotalComprobante>' + str(round(base_total + total_impuestos, 2)) + '</TotalComprobante>')
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
    sb.Append('<Otros>')
    sb.Append('<OtroTexto>' + str(invoice_comments) + '</OtroTexto>')
    sb.Append('</Otros>')
    sb.Append('</NotaDebitoElectronica>')

    ncelectronica_bytes = str(sb)

    return stringToBase64(ncelectronica_bytes)


#Funcion para enviar el XML al Ministerio de Hacienda
def send_xml_fe(inv, token, date, xml, tipo_ambiente):
    headers = {'Authorization': 'Bearer ' + token, 'Content-type': 'application/json'}

    # establecer el ambiente al cual me voy a conectar
    if tipo_ambiente == 'api-stag':
        endpoint = fe_enums.UrlHaciendaRecepcion.apistag.value
    else:
        endpoint = fe_enums.UrlHaciendaRecepcion.apiprod.value

    try:
        xml_listo = base64UTF8Decoder(xml)
    except AttributeError:
        xml_listo = xml
        pass

    data = {'clave': inv.number_electronic,
            'fecha': date,
            'emisor': {
                'tipoIdentificacion': inv.company_id.identification_id.code,
                'numeroIdentificacion': inv.company_id.vat
            },
            'receptor': {
                'tipoIdentificacion': inv.company_id.identification_id.code,
                'numeroIdentificacion': inv.company_id.vat
            },
            'comprobanteXml': xml_listo
            }

    json_hacienda = json.dumps(data)

    try:
        #  enviando solicitud post y guardando la respuesta como un objeto json
        response = requests.request("POST", endpoint, data=json_hacienda, headers=headers)

        # Verificamos el codigo devuelto, si es distinto de 202 es porque hacienda nos está devolviendo algun error
        if response.status_code != 202:
            error_caused_by = response.headers['x-error-cause']
            return {'resp': {'Status': response.status_code, 'text': error_caused_by}}
        else:
            # respuesta_hacienda = response.status_code
            return {'resp': {'Status': response.status_code, 'text': response.reason}}
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


#Obtener Attachments para las Facturas Electrónicas
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


#CONVIERTE UN STRING A BASE 64
def stringToBase64(s):
    return base64.b64encode(s.encode('utf-8'))


#TOMA UNA CADENA Y ELIMINA LOS CARACTERES AL INICIO Y AL FINAL
def stringStrip(s, start, end):
    return s[start:-end]


#Tomamos el XML y le hacemos el decode de base 64, esto por ahora es solo para probar
#la posible implementacion de la firma en python
def base64decode(string_decode):
    return base64.b64decode(string_decode)


#TOMA UNA CADENA EN BASE64 Y LA DECODIFICA PARA ELIMINAR EL b' Y DEJAR EL STRING CODIFICADO
#DE OTRA MANERA HACIENDA LO RECHAZA
def base64UTF8Decoder(s):
    return s.decode("utf-8")


#CLASE PERSONALIZADA (NO EXISTE EN PYTHON) QUE CONSTRUYE UNA CADENA MEDIANTE APPEND SEMEJANTE
#AL STRINGBUILDER DEL C#
class StringBuilder:
    _file_str = None

    def __init__(self):
        self._file_str = io.StringIO()

    def Append(self, str):
        self._file_str.write(str)

    def __str__(self):
        return self._file_str.getvalue()
