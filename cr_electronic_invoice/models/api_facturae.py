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

try:
    from lxml import etree
except ImportError:
    from xml.etree import ElementTree

try:
    import xmlsig
    from OpenSSL import crypto
except(ImportError, IOError) as err:
    logging.info(err)

#TEST DE LA CLASE GENERADA
#from . import fe
#import tempfile

#ESTO ES PARA TEST DE LA FIRMA USANDO EL CODIGO DE LA CARPETA XADES
#from .. xades import XAdESContext, PolicyId, template


def sign_test(cert, password, xml_firma):

    min = 1
    max = 99999
    signature_id = 'Signature%05d' % random.randint(min, max)
    signed_properties_id = signature_id + '-SignedProperties%05d' \
                           % random.randint(min, max)

    key_info_id = 'KeyInfo%05d' % random.randint(min, max)
    reference_id = 'Reference%05d' % random.randint(min, max)
    object_id = 'Object%05d' % random.randint(min, max)
    etsi = 'http://uri.etsi.org/01903/v1.3.2#'

    sig_policy_identifier = 'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4/' \
                            'Resolucion%20Comprobantes%20Electronicos%20%20DGT-R-48-2016.pdf'

    sig_policy_hash_value = 'Ohixl6upD6av8N7pEvDABhEL6hM='
    #root = etree.fromstring(xml)

    xml_decoder = base64decode(xml)
    xml_no_bytes = base64UTF8Decoder(xml_decoder)

    root = etree.fromstring(xml_decoder, etree.XMLParser(remove_blank_text=True))

    sign = xmlsig.template.create(
        c14n_method=xmlsig.constants.TransformInclC14N,
        sign_method=xmlsig.constants.TransformRsaSha256,
        name=signature_id,
        ns="ds"
    )

    key_info = xmlsig.template.ensure_key_info(
        sign,
        name=key_info_id
    )

    x509_data = xmlsig.template.add_x509_data(key_info)
    xmlsig.template.x509_data_add_certificate(x509_data)
    xmlsig.template.add_key_value(key_info)
    certificate = crypto.load_pkcs12(base64.b64decode(cert), password)

    ref = xmlsig.template.add_reference(
        sign,
        xmlsig.constants.TransformSha256,
        name=reference_id
    )

    xmlsig.template.add_transform(
        ref,
        xmlsig.constants.TransformEnveloped
    )

    xmlsig.template.add_reference(
        sign,
        xmlsig.constants.TransformSha256,
        uri='#' + key_info_id
    )

    xmlsig.template.add_reference(
        sign,
        xmlsig.constants.TransformSha256,
        uri='#' + signed_properties_id,
        uri_type='http://uri.etsi.org/01903#SignedProperties'
    )

    object_node = etree.SubElement(
        sign,
        etree.QName(xmlsig.constants.DSigNs, 'Object'),
        nsmap={'xades': etsi},
        attrib={xmlsig.constants.ID_ATTR: object_id}
    )
    qualifying_properties = etree.SubElement(
        object_node,
        etree.QName(etsi, 'QualifyingProperties'),
        attrib={
            'Target': '#' + signature_id
        }
    )
    signed_properties = etree.SubElement(
        qualifying_properties,
        etree.QName(etsi, 'SignedProperties'),
        attrib={
            xmlsig.constants.ID_ATTR: signed_properties_id
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
        etree.QName(xmlsig.constants.DSigNs, 'DigestMethod'),
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
        etree.QName(xmlsig.constants.DSigNs, 'DigestValue')
    ).text = base64.b64encode(hash_cert.digest())


    issuer_serial = etree.SubElement(
        signing_certificate_cert,
        etree.QName(etsi, 'IssuerSerial')
    )
    etree.SubElement(
        issuer_serial,
        etree.QName(xmlsig.constants.DSigNs, 'X509IssuerName')
    ).text = xmlsig.utils.get_rdns_name(
        certificate.get_certificate().to_cryptography().issuer.rdns)
    etree.SubElement(
        issuer_serial,
        etree.QName(xmlsig.constants.DSigNs, 'X509SerialNumber')
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
    etree.SubElement(
        sig_policy_id,
        etree.QName(etsi, 'Description')
    ).text = "Política de Firma FE MH Costa Rica"
    sig_policy_hash = etree.SubElement(
        signature_policy_id,
        etree.QName(etsi, 'SigPolicyHash')
    )
    etree.SubElement(
        sig_policy_hash,
        etree.QName(xmlsig.constants.DSigNs, 'DigestMethod'),
        attrib={
            'Algorithm': 'http://www.w3.org/2000/09/xmldsig#sha1'
        }
    )

    try:
        remote = urllib.request.urlopen(sig_policy_identifier)
        hash_value = base64.b64encode(
            hashlib.sha1(remote.read()).digest())
    except urllib.request.HTTPError:
        hash_value = sig_policy_hash_value
    etree.SubElement(
        sig_policy_hash,
        etree.QName(xmlsig.constants.DSigNs, 'DigestValue')
    ).text = hash_value
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

    ctx = xmlsig.SignatureContext()
    key = crypto.load_pkcs12(base64.b64decode(cert), password)
    ctx.x509 = key.get_certificate().to_cryptography()
    ctx.public_key = ctx.x509.public_key()
    ctx.private_key = key.get_privatekey().to_cryptography_key()

    root.append(sign)
    ctx.sign(sign)

    return etree.tostring(
        root, xml_declaration=True, encoding='UTF-8'
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


