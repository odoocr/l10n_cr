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
from . import fe
import tempfile

#ESTO ES PARA TEST DE LA FIRMA USANDO EL CODIGO DE LA CARPETA XADES
from .. xades import XAdESContext, PolicyId, template


def test_model_xml(inv, consecutivo, date, sale_conditions, medio_pago, total_servicio_gravado,
                     total_servicio_exento, total_mercaderia_gravado, total_mercaderia_exento, base_total, lines,
                     currency_rate, invoice_comments):

    factura_electronica = fe.FacturaElectronica()
    rootTag = 'FacturaElectronica'

    factura_electronica.set_Clave(inv.number_electronic)
    factura_electronica.set_NumeroConsecutivo(consecutivo)
    factura_electronica.set_FechaEmision(date)

    emisor = fe.EmisorType()
    emisor.set_Nombre(inv.company_id.name)

    emisor.set_Identificacion(
        fe.IdentificacionType(
            Tipo=inv.company_id.identification_id.code,
            Numero=inv.company_id.vat)
    )

    emisor.set_NombreComercial(str(inv.company_id.commercial_name or 'NA'))

    emisor.set_Ubicacion(
        fe.UbicacionType(
            Provincia=inv.company_id.state_id.code,
            Canton=inv.company_id.district_id.code,
            Distrito=inv.company_id.district_id.code,
            Barrio=str(inv.company_id.neighborhood_id.code or '00'),
            OtrasSenas=str(inv.company_id.street or 'NA'))
    )

    emisor.set_CorreoElectronico(str(inv.company_id.email))

    emisor.set_Telefono(
        fe.TelefonoType(
            CodigoPais=inv.company_id.phone_code,
            NumTelefono=re.sub('[^0-9]+', '', inv.company_id.phone))
    )

    factura_electronica.set_Emisor(emisor)

    receptor = fe.ReceptorType()
    receptor.set_Nombre(str(inv.partner_id.name[:80]))

    if inv.partner_id.identification_id.code == '05':
        receptor.set_IdentificacionExtranjero(inv.partner_id.vat)
    else:
        receptor.set_Identificacion(
            fe.IdentificacionType(
                Tipo=inv.partner_id.identification_id.code,
                Numero=inv.partner_id.vat)
        )

    receptor.set_Ubicacion(
        fe.UbicacionType(
            Provincia=str(inv.partner_id.state_id.code or ''),
            Canton=str(inv.partner_id.county_id.code or ''),
            Distrito=str(inv.partner_id.district_id.code or ''),
            Barrio=str(inv.partner_id.neighborhood_id.code or '00'),
            OtrasSenas=str(inv.partner_id.street or 'NA'))
    )

    receptor.set_CorreoElectronico(str(inv.partner_id.email))

    receptor.set_Telefono(
        fe.TelefonoType(
            CodigoPais=inv.partner_id.phone_code,
            NumTelefono=re.sub('[^0-9]+', '', inv.partner_id.phone))
    )

    factura_electronica.set_Receptor(receptor)

    factura_electronica.set_CondicionVenta(sale_conditions)
    factura_electronica.set_PlazoCredito(str(inv.partner_id.property_payment_term_id.line_ids[0].days or 0))
    factura_electronica.set_MedioPago(medio_pago)

    detalle_factura = lines
    response_json = json.loads(detalle_factura)

    for (k, v) in response_json.items():
        numero_linea = 0
        numero_linea = numero_linea + 1

        linea_detalle = fe.LineaDetalleType(
            NumeroLinea=numero_linea,
            Cantidad=v['cantidad'],
            UnidadMedida=v['unidadMedida'],
            Detalle=v['detalle'],
            PrecioUnitario=v['precioUnitario'],
            MontoTotal=v['montoTotal'],
            MontoDescuento=None,
            NaturalezaDescuento=None,
            SubTotal=v['subtotal'],
            Impuesto=None,
            MontoTotalLinea=v['montoTotalLinea']
        )

        if v.get('montoDescuento'):
            linea_detalle.set_MontoDescuento(str(v['montoDescuento']))

        if v.get('naturalezaDescuento'):
            linea_detalle.set_NaturalezaDescuento(str(v['naturalezaDescuento']))

        if v.get('impuesto'):
            for (a, b) in v['impuesto'].items():
                linea_impuesto = fe.ImpuestoType(
                    Codigo=b['codigo'],
                    Tarifa=b['tarifa'],
                    Monto=b['monto'],
                    Exoneracion=None
                )

                if b.get('exoneracion'):
                    for (c, d) in b['exoneracion']:
                        linea_exoneracion = fe.ExoneracionType(
                            TipoDocumento=d['tipoDocumento'],
                            NumeroDocumento=d['numeroDocumento'],
                            NombreInstitucion=d['nombreInstitucion'],
                            FechaEmision=d['fechaEmision'],
                            MontoImpuesto=d['montoImpuesto'],
                            PorcentajeCompra=d['porcentajeCompra']
                        )

                        linea_impuesto.set_Exoneracion(linea_exoneracion)

                linea_detalle.add_Impuesto(linea_impuesto)

        factura_electronica.set_DetalleServicio(linea_detalle)

        resumen_factura = fe.ResumenFacturaType(
            CodigoMoneda=inv.currency_id.name,
            TipoCambio=currency_rate,
            TotalServGravados=total_servicio_gravado,
            TotalServExentos=total_servicio_exento,
            TotalMercanciasGravadas=total_mercaderia_gravado,
            TotalMercanciasExentas=total_mercaderia_exento,
            TotalGravado=total_servicio_gravado + total_mercaderia_gravado,
            TotalExento=total_servicio_exento + total_mercaderia_exento,
            TotalVenta=(
        total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento),
            TotalDescuentos=(round(base_total - inv.amount_untaxed, 5)),
            TotalVentaNeta=(
        round((total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento) -
              (base_total - inv.amount_untaxed), 5)),
            TotalImpuesto=round(inv.amount_tax, 5),
            TotalComprobante=round(inv.amount_total, 5)
        )

        factura_electronica.set_ResumenFactura(resumen_factura)

        normativa = fe.NormativaType(
            NumeroResolucion='DGT-R-48-2016',
            FechaResolucion='07-10-2016 08:00:00'
        )

        factura_electronica.set_Normativa(normativa)

        otros = fe.OtrosType(
            OtroTexto=str(invoice_comments),
            OtroContenido=None
        )

        factura_electronica.set_Otros(otros)

        xml_type = rootTag[0].lower() + rootTag[1:]
        ns = 'xmlns="https://tribunet.hacienda.go.cr/docs/esquemas/2017/v4.2/' + xml_type + '" '
        ns += 'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'

        file = tempfile.NamedTemporaryFile(delete=False)
        file.write(b'<?xml version="1.0" encoding="utf-8"?>')

        generated_xml = factura_electronica.export(file.encode('utf-8'), 0, name_=rootTag, namespacedef_=ns)

        file.write('\n')
        file.close()

        return generated_xml


def sign_test(cert, password, xml_firma):

    xml_firmar = base64decode(xml_firma)
    #root = parse_xml(xml_firmar)
    root = etree.fromstring(xml_firmar)
    key = crypto.load_pkcs12(base64.b64decode(cert), password)

    sign = root.xpath(
        '//ds:Signature', namespaces={'ds': xmlsig.constants.DSigNs}
    )[0]

    policy = PolicyId()
    policy.id = 'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4/Resolucion%20Comprobantes%20Electronicos%20%20DGT-R-48-2016.pdf'
    policy.hash_method = xmlsig.constants.TransformSha256
    ctx = XAdESContext(policy)
    ctx.load_pkcs12(key)  #crypto.load_pkcs12(base64.b64decode(cert), password)
    ctx.sign(sign)
    ctx.verify(sign)


    return etree.tostring(
        root
    )


def annotate_with_xmlns_prefixes(tree, xmlns_prefix, skip_root_node=True):
    if not etree.iselement(tree):
        tree = tree.getroot()
    iterator = tree.iter()
    if skip_root_node: # Add XMLNS prefix also to the root node?
        iterator.next()
    for e in iterator:
        if not ':' in e.tag:
            e.tag = xmlns_prefix + ":" + e.tag


def add_xmnls_attributes(tree, xmlns_uris_dict):
    if not etree.iselement(tree):
        tree = tree.getroot()
    for prefix, uri in xmlns_uris_dict.items():
        tree.attrib['xmlns:' + prefix] = uri


def sign_file(cert, password, xml_firma):
    min = 1
    max = 99999

    xmlns_uris = {'ds': 'http://myhost.com/p.xsd'}

    random_val = random.randint(min, max)

    signature_id = 'Signature-' + str(random_val)
    #signed_properties_id = signature_id + '-SignedProperties%05d' \
    #                       % random.randint(min, max)

    signed_properties_id = 'SignedProperties-' + signature_id
    signature_value = 'SignatureValue-' + str(random_val)

    qualifying_properties = 'QualifyingProperties-%05d' % random.randint(min, max)

    #key_info_id = 'KeyInfo%05d' % random.randint(min, max)
    key_info_id = 'KeyInfoId-' + signature_id

    reference_id = 'Reference-%05d' % random.randint(min, max)
    #object_id = 'Object%05d' % random.randint(min, max)
    object_id = 'XadesObjectId-%05d' % random.randint(min, max)

    xades = 'http://uri.etsi.org/01903/v1.3.2#'
    ds = 'http://www.w3.org/2000/09/xmldsig#'
    xades141 = 'http://uri.etsi.org/01903/v1.4.1#'
    sig_policy_identifier = 'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4/Resolucion%20Comprobantes%20Electronicos%20%20DGT-R-48-2016.pdf'

    sig_policy_hash_value = 'V8lVVNGDCPen6VELRD1Ja8HARFk='

    xml_firmar = base64decode(xml_firma)

    root = etree.fromstring(xml_firmar)

    certificate = crypto.load_pkcs12(base64.b64decode(cert), password)

    # GENERAR NODO PERSONALIZADO PARA FE
    sign = etree.Element(
        etree.QName(ds, 'Signature'),
        nsmap={'ds': ds},
        attrib={
            xmlsig.constants.ID_ATTR: signature_id,
        }
    )

    #annotate_with_xmlns_prefixes(sign, 'ds')
    #add_xmnls_attributes(sign, xmlns_uris)

    # GENERO EL NODO ds:SignedInfo
    signed_info = etree.SubElement(
        sign,
        etree.QName(ds, 'SignedInfo')
    )

    # CREO EL NODO ds:CanonicalizationMethod DENTRO DE signed_info
    etree.SubElement(
        signed_info,
        etree.QName(ds, 'CanonicalizationMethod'),
        attrib={
            'Algorithm': xmlsig.constants.TransformInclC14N
        }
    )

    # CREO EL NODO ds:SignatureMethod DENTRO DE signed_info
    etree.SubElement(
        signed_info,
        etree.QName(ds, 'SignatureMethod'),
        attrib={
            'Algorithm': xmlsig.constants.TransformRsaSha256
        }
    )

    # CREO EL NODO ds:SignatureMethod DENTRO DE signed_info
    reference = etree.SubElement(
        signed_info,
        etree.QName(ds, 'Reference'),
        attrib={
            xmlsig.constants.ID_ATTR: reference_id,
            'URI': ''
        }
    )

    # CREO EL NODO ds:Transforms DENTRO DE reference
    transforms = etree.SubElement(
        reference,
        etree.QName(ds, 'Transforms'),
    )

    # CREO EL NODO ds:Transform DENTRO DE trasnforms
    etree.SubElement(
        transforms,
        etree.QName(ds, 'Transform'),
        attrib={
            'Algorithm': 'http://www.w3.org/2000/09/xmldsig#enveloped-signature'
        }
    )

    # CREO EL NODO ds:DigestMethod DENTRO DE reference
    etree.SubElement(
        reference,
        etree.QName(ds, 'DigestMethod'),
        attrib={
            'Algorithm': 'http://www.w3.org/2001/04/xmlenc#sha256'
        }
    )

    # OBTENGO EL DIGEST VALUE DEL CERTIFICADO PARA EL NODO DIGESTVALUE
    #digest_value = hashlib.sha256(
    #    crypto.dump_certificate(
    #        crypto.FILETYPE_ASN1,
    #        certificate.get_certificate()
    #    )
    #)

    # GENERO EL NODO ds:DigestValue DENTRO DE reference
    etree.SubElement(
        reference,
        etree.QName(ds, 'DigestValue')
    )#.text = base64.b64encode(digest_value.digest())

    # CREO EL SEGUNDO NODO ds:SignatureMethod DENTRO DE signed_info
    sec_reference = etree.SubElement(
        signed_info,
        etree.QName(ds, 'Reference'),
        attrib={
            xmlsig.constants.ID_ATTR: 'ReferenceKeyInfo',
            'URI': '#' + key_info_id

        }
    )

    # CREO EL NODO ds:DigestMethod DENTRO DE reference
    etree.SubElement(
        sec_reference,
        etree.QName(ds, 'DigestMethod'),
        attrib={
            'Algorithm': 'http://www.w3.org/2001/04/xmlenc#sha256'
        }
    )

    # OBTENGO EL DIGEST VALUE DEL CERTIFICADO PARA EL NODO DIGESTVALUE
    #digest_value2 = hashlib.sha256(
    #    crypto.dump_certificate(
    #        crypto.FILETYPE_ASN1,
    #        certificate.get_certificate()
    #    )
    #)

    # GENERO EL NODO ds:DigestValue DENTRO DE reference
    etree.SubElement(
        sec_reference,
        etree.QName(ds, 'DigestValue')
    )#.text = base64.b64encode(digest_value2.digest())

    # CREO EL TERCER NODO ds:Reference DENTRO DE signed_info
    tr_reference = etree.SubElement(
        signed_info,
        etree.QName(ds, 'Reference'),
        attrib={
            'Type': 'http://uri.etsi.org/01903#SignedProperties',
            'URI': '#' + signed_properties_id,
        }
    )

    # CREO EL NODO ds:DigestMethod DENTRO DE reference
    etree.SubElement(
        tr_reference,
        etree.QName(ds, 'DigestMethod'),
        attrib={
            'Algorithm': 'http://www.w3.org/2001/04/xmlenc#sha256'
        }
    )

    # OBTENGO EL DIGEST VALUE DEL CERTIFICADO PARA EL NODO DIGESTVALUE
    #digest_value3 = hashlib.sha256(
    #    crypto.dump_certificate(
    #        crypto.FILETYPE_ASN1,
    #        certificate.get_certificate()
    #    )
    #)

    # GENERO EL NODO ds:DigestValue DENTRO DE reference
    etree.SubElement(
        tr_reference,
        etree.QName(ds, 'DigestValue')
    )#.text = base64.b64encode(digest_value3.digest())

    # GENERO EL NODO ds:SignatureValue
    etree.SubElement(
        sign,
        etree.QName(ds, 'SignatureValue'),
        attrib={
            xmlsig.constants.ID_ATTR: signature_value
        }
    )

    # GENERO EL NODO ds:KeyInfo
    key_info = etree.SubElement(
        sign,
        etree.QName(ds, 'KeyInfo'),
        attrib={
            xmlsig.constants.ID_ATTR: key_info_id
        }
    )


    # GENERO EL NODO ds:X509Data
    x509 = etree.SubElement(
        key_info,
        etree.QName(ds, 'X509Data'),
    )

    # GENERO EL NODO ds:X509Certificate
    etree.SubElement(
        x509,
        etree.QName(ds, 'X509Certificate'),
    )

    # GENERO EL NODO ds:KeyValue
    etree.SubElement(
        key_info,
        etree.QName(ds, 'KeyValue'),
    )



    #AQUI EMPIEZO A CREAR EL NODO DE QUALIFYNG PROPERTIES
    object_node = etree.SubElement(
        sign,
        etree.QName(xmlsig.constants.DSigNs, 'Object'),
        #nsmap={'etsi': etsi},
        attrib={xmlsig.constants.ID_ATTR: object_id}
        #nsmap={'xades': xades},
        #attrib={xmlsig.constants.ID_ATTR: object_id} NO SE NECESITA EN EL XML DE HACIENDA
    )

    #CREO EL SUBNODO QUALIFYING PROPERTIES
    qualifying_properties = etree.SubElement(
        object_node,
        etree.QName(xades, 'QualifyingProperties'),
        nsmap = {'xades': xades, 'xades141': xades141},
        attrib={
            xmlsig.constants.ID_ATTR: qualifying_properties,
            'Target': '#' + signature_id
        })

    #CREO EL NODO xades:SignedProperties DENTRO DE QUALIFYING PROPERTIES
    signed_properties = etree.SubElement(
        qualifying_properties,
        etree.QName(xades, 'SignedProperties'),
        attrib={
            xmlsig.constants.ID_ATTR: signed_properties_id #ESTO HAY QUE CAMBIARLO PARA QUE SEA COMO LO PIDE HACIENDA
        }
    )

    # CREO EL NODO xades:SignedSignatureProperties DENTRO DE SIGNED PROPERTIES
    signed_signature_properties = etree.SubElement(
        signed_properties,
        etree.QName(xades, 'SignedSignatureProperties')
    )

    #GENERO LA HORA PARA EL NODO xades:SigningTime
    #now = datetime.datetime.now().replace(
    #    microsecond=0, tzinfo=pytz.utc
    #)

    # GENERO EL NODO xades:SigningTime Y LE PONGO LA HORA
    etree.SubElement(
        signed_signature_properties,
        etree.QName(xades, 'SigningTime')
    ).text = get_time_hacienda()

    #GENERO EL NODO xades:SigningCertificate
    signing_certificate = etree.SubElement(
        signed_signature_properties,
        etree.QName(xades, 'SigningCertificate')
    )

    #GENERO EL NODO xades:Cert DENTRO DE xades:SigningCertificate
    signing_certificate_cert = etree.SubElement(
        signing_certificate,
        etree.QName(xades, 'Cert')
    )

    #GENERO EL NODO xades:CertDigest DENTRO DE xades:cert
    cert_digest = etree.SubElement(
        signing_certificate_cert,
        etree.QName(xades, 'CertDigest')
    )

    #GENERO EL NODO ds:DigestMethod DENTRO DE xades:CertDigest
    etree.SubElement(
        cert_digest,
        etree.QName(xmlsig.constants.DSigNs, 'DigestMethod'),
        attrib={
            'Algorithm': 'http://www.w3.org/2001/04/xmlenc#sha256'
        }
    )

    # OBTENGO EL DIGEST VALUE DEL CERTIFICADO PARA EL NODO DIGESTVALUE
    hash_cert = hashlib.sha256(
        crypto.dump_certificate(
            crypto.FILETYPE_ASN1,
            certificate.get_certificate()
        )
    )

    # GENERO EL NODO ds:DigestValue DENTRO DE xades:CertDigest Y LE PONGO EL VALOR DEL DIGESTVALUE ANTERIOR
    etree.SubElement(
        cert_digest,
        etree.QName(xmlsig.constants.DSigNs, 'DigestValue')
    ).text = base64.b64encode(hash_cert.digest())

    # GENERO EL NODO xades:IssuerSerial DENTRO DE xades:Cert
    issuer_serial = etree.SubElement(
        signing_certificate_cert,
        etree.QName(xades, 'IssuerSerial')
    )

    # GENERO EL NODO ds:X509IssuerName DENTRO DE xades:IssuerSerial
    etree.SubElement(
        issuer_serial,
        etree.QName(xmlsig.constants.DSigNs, 'X509IssuerName')
    ).text = xmlsig.utils.get_rdns_name(certificate.get_certificate().to_cryptography().issuer.rdns)

    # GENERO EL NODO ds:X509SerialNumber DENTRO DE xades:IssuerSerial
    etree.SubElement(
        issuer_serial,
        etree.QName(xmlsig.constants.DSigNs, 'X509SerialNumber')
    ).text = str(certificate.get_certificate().get_serial_number())

    # GENERO EL NODO xades:SignaturePolicyIdentifier DENTRO DE sign
    signature_policy_identifier = etree.SubElement(
        signed_signature_properties,
        etree.QName(xades, 'SignaturePolicyIdentifier')
    )

    # GENERO EL NODO xades:SignaturePolicyId DENTRO DE xades:SignaturePolicyIdentifier
    signature_policy_id = etree.SubElement(
        signature_policy_identifier,
        etree.QName(xades, 'SignaturePolicyId')
    )

    # GENERO EL NODO xades:SigPolicyId DENTRO DE xades:SignaturePolicyId
    sig_policy_id = etree.SubElement(
        signature_policy_id,
        etree.QName(xades, 'SigPolicyId')
    )

    # GENERO EL NODO xades:Identifier DENTRO DE xades:SigPolicyId
    etree.SubElement(
        sig_policy_id,
        etree.QName(xades, 'Identifier')
    ).text = sig_policy_identifier

    #BORRO ESTE NODO PUES EN FE COSTA RICA NO SE NECESITA
    etree.SubElement(
        sig_policy_id,
        etree.QName(xades, 'Description')
    )#.text = "Política de Firma FacturaE v3.1"

    # GENERO EL NODO xades:Identifier DENTRO DE signature_policy_id
    sig_policy_hash = etree.SubElement(
        signature_policy_id,
        etree.QName(xades, 'SigPolicyHash')
    )

    # GENERO EL NODO ds:DigestMethod DENTRO DE xades:Identifier
    etree.SubElement(
        sig_policy_hash,
        etree.QName(xmlsig.constants.DSigNs, 'DigestMethod'),
        attrib={
            'Algorithm': 'http://www.w3.org/2000/09/xmldsig#sha1'
        })

    #GENERO EL DIGEST PARA EL CERTIFICADO LEYENDOLO DE LA URL DE HACIENDA
    try:
        remote = urllib.request.urlopen(sig_policy_identifier)
        hash_value = base64.b64encode(hashlib.sha256(remote.read()).digest())
    except urllib.request.HTTPError:
        hash_value = sig_policy_hash_value

    # GENERO EL NODO ds:DigestValue ds:DigestMethod DENTRO DE sig_policy_hash
    etree.SubElement(
        sig_policy_hash,
        etree.QName(xmlsig.constants.DSigNs, 'DigestValue')
    ).text = hash_value

    #NO REQUERIDO PARA FE COSTA RICA
    #signer_role = etree.SubElement(
    #    signed_signature_properties,
    #    etree.QName(etsi, 'SignerRole')
    #)
    #claimed_roles = etree.SubElement(
    #    signer_role,
    #    etree.QName(etsi, 'ClaimedRoles')
    #)

    #etree.SubElement(
    #    claimed_roles,
    #    etree.QName(etsi, 'ClaimedRole')
    #).text = 'supplier'

    signed_data_object_properties = etree.SubElement(
        signed_properties,
        etree.QName(xades, 'SignedDataObjectProperties')
    )

    data_object_format = etree.SubElement(
        signed_data_object_properties,
        etree.QName(xades, 'DataObjectFormat'),
        attrib={
            'ObjectReference': '#' + reference_id
        }
    )

    #etree.SubElement(
    #    data_object_format,
    #    etree.QName(etsi, 'Description')
    #).text = 'Factura'

    etree.SubElement(
        data_object_format,
        etree.QName(xades, 'MimeType')
    ).text = 'text/xml'

    ctx = xmlsig.SignatureContext()
    key = crypto.load_pkcs12(base64.b64decode(cert), password)
    ctx.x509 = key.get_certificate().to_cryptography()
    ctx.public_key = ctx.x509.public_key()
    ctx.private_key = key.get_privatekey().to_cryptography_key()
    root.append(sign)

    root.xpath(
        '//ds:Signature', namespaces={'ds': xmlsig.constants.DSigNs}
    )[0]

    ctx.sign(sign)

    #xml_bytes = etree.tostring(root, xml_declaration=True)

    #return stringToBase64(xml_bytes)


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


