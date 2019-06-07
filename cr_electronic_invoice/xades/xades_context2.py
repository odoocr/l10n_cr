# Lib to sign Xades-EPES xml docx
# 2019 Ricardo Vong <rvong@indelsacr.com>
# This file should be imported after xmlsig or byitself if only XadesContext is used.

import hashlib
import xmlsig
from lxml import etree
from base64 import b64decode, b64encode
from urllib import parse, request
import logging

__all__ = ['XAdESContext2', 'PolicyId2', 'PolicyId2Exception']

logger = logging.getLogger(__name__)


def xmlsig_create(c14n_method=False, sign_method=False, name=False, ns='ds', value_name=None):
    node = etree.Element(etree.QName(xmlsig.constants.DSigNs, 'Signature'), nsmap={ns: xmlsig.constants.DSigNs})
    if name:
        node.set(xmlsig.constants.ID_ATTR, name)
    signed_info = xmlsig.utils.create_node('SignedInfo', node, xmlsig.constants.DSigNs)
    canonicalization = xmlsig.utils.create_node('CanonicalizationMethod', signed_info, xmlsig.constants.DSigNs)
    canonicalization.set('Algorithm', c14n_method)
    signature_method = xmlsig.utils.create_node('SignatureMethod', signed_info, xmlsig.constants.DSigNs)
    signature_method.set('Algorithm', sign_method)
    signature_value = xmlsig.utils.create_node('SignatureValue', node, xmlsig.constants.DSigNs)
    if value_name:
        signature_value.set(xmlsig.constants.ID_ATTR, value_name)
    return node


def xmlsig_add_key_name(node, name=False):
    key_name = xmlsig.utils.create_node('KeyName', node, xmlsig.constants.DSigNs)
    if name:
        key_name.text = name
    return key_name


def get_reversed_rdns_name(rdns):
    """
    Gets the rdns String name, but in the right order. xmlsig original function produces a reversed order
    :param rdns: RDNS object
    :type rdns: cryptography.x509.RelativeDistinguishedName
    :return: RDNS name
    """
    name = ''
    for rdn in reversed(rdns):
        for attr in rdn._attributes:
            if len(name) > 0:
                name = name + ','
            if attr.oid in xmlsig.utils.OID_NAMES:
                name = name + xmlsig.utils.OID_NAMES[attr.oid]
            else:
                name = name + attr.oid._name
            name = name + '=' + attr.value
    return name


def make_xmlsig_template_function(xml_key):

    def xmlfunc(node):
        return xmlsig.utils.create_node(xml_key, node, xmlsig.constants.DSigNs)

    return xmlfunc


def b64_print(s):
    return s


def create_node(name, parent=None, ns='', tail=False, text=False):
    node = etree.Element(etree.QName(ns, name))
    if parent is not None:
        parent.append(node)
    if tail and tail != '\n':
        node.tail = tail
    if text and text != '\n':
        node.text = text
    return node


# Monkey patching xmlsig functions to remove unecesary tail and body newlines
xmlsig.template.create = xmlsig_create
xmlsig.template.add_key_name = xmlsig_add_key_name
xmlsig.template.add_x509_data = make_xmlsig_template_function('X509Data')
xmlsig.template.x509_data_add_certificate = make_xmlsig_template_function('X509Certificate')
xmlsig.template.x509_data_add_crl = make_xmlsig_template_function('X509CRL')
xmlsig.template.x509_data_add_issuer_serial = make_xmlsig_template_function('X509IssuerSerial')
xmlsig.template.x509_data_add_ski = make_xmlsig_template_function('X509SKI')
xmlsig.template.x509_data_add_subject_name = make_xmlsig_template_function('X509SubjectName')
xmlsig.template.x509_issuer_serial_add_issuer_name = make_xmlsig_template_function('X509IssuerName')
xmlsig.template.x509_issuer_serial_add_serial_number = make_xmlsig_template_function('X509SerialNumber')
xmlsig.template.create_node = create_node
xmlsig.signature_context.b64_print = b64_print
xmlsig.algorithms.rsa.create_node = create_node
xmlsig.algorithms.rsa.b64_print = b64_print

from .xades_context import XAdESContext
from .policy import PolicyId
from .constants import NS_MAP, EtsiNS, MAP_HASHLIB
import re

URL_ESCAPE_PATTERN = re.compile('[\r\n]')
URL_HACIENDA_PATTERN = re.compile('.+\.hacienda\.go\.cr$')


class XAdESContext2(XAdESContext):

    def fill_x509_issuer_name(self, x509_issuer_serial):
        """
        Fills the X509IssuerSerial node
        :param x509_issuer_serial: X509IssuerSerial node
        :type x509_issuer_serial: lxml.etree.Element
        :return: None
        """
        x509_issuer_name = x509_issuer_serial.find('ds:X509IssuerName', namespaces=NS_MAP)
        if x509_issuer_name is not None:
            x509_issuer_name.text = get_reversed_rdns_name(self.x509.issuer.rdns)
        x509_issuer_number = x509_issuer_serial.find('ds:X509SerialNumber', namespaces=NS_MAP)
        if x509_issuer_number is not None:
            x509_issuer_number.text = str(self.x509.serial_number)

    def is_signed(self, node):
        """
        Check if document is already signed
        :param node: etree node
        :return: true if already signed
        """
        signed_value = node.find('ds:SignatureValue', namespaces=NS_MAP)
        return signed_value is not None and len(signed_value.text) > 0


def validate_hacienda_url(url):
    """
    Checks for malicious url to avoid surprises
    :param url: text url
    :return: the valid url if valid or None is invalid
    """
    url_unescaped = parse.unquote(url)
    if URL_ESCAPE_PATTERN.search(url_unescaped):
        return None
    p = parse.urlparse(url_unescaped, allow_fragments=False)
    if URL_HACIENDA_PATTERN.match(p.netloc) is None:
        return None
    return url


class PolicyId2Exception(Exception):
    pass


class PolicyId2(PolicyId):
    check_strict = False
    # Theres is something wrong with Hacienda's hash for their policy document, so we need to use their
    # previously generated value
    cache = {
        'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.2/'
        'ResolucionComprobantesElectronicosDGT-R-48-2016_4.2.pdf': {
            'http://www.w3.org/2000/09/xmldsig#sha1': 'E9/BBP0G1Z3JJQzOpwqpJuf7xdY=',
        },
        'https://tribunet.hacienda.go.cr/docs/esquemas/2016/v4/'
        'Resolucion%20Comprobantes%20Electronicos%20%20DGT-R-48-2016.pdf': {
            'http://www.w3.org/2000/09/xmldsig#sha1': 'JyeDiicXk0QZL9hHKZW097BHnDo=',  # 'V8lVVNGDCPen6VELRD1Ja8HARFk=',
        },
    }

    def calculate_policy_node(self, node, sign=False):
        if not (sign or self.check_strict):
            # print('No policy check')
            return None
        if sign:
            remote = self.id
            hash_method = self.hash_method
            policy_id = create_node('SignaturePolicyId', node, EtsiNS)
            identifier = create_node('SigPolicyId', policy_id, EtsiNS)
            create_node('Identifier', identifier, EtsiNS).text = self.id
            create_node('Description', identifier, EtsiNS).text = self.name
            digest = create_node('SigPolicyHash', policy_id, EtsiNS)
            digest_method = create_node('DigestMethod', digest, xmlsig.ns.DSigNs)
            digest_method.set('Algorithm', self.hash_method)
            digest_value = create_node('DigestValue', digest, xmlsig.ns.DSigNs)
        else:
            policy_id = node.find('etsi:SignaturePolicyId', namespaces=NS_MAP)
            identifier = policy_id.find('etsi:SigPolicyId', namespaces=NS_MAP)
            remote = identifier.find('etsi:Identifier', namespaces=NS_MAP).text
            hash_method = policy_id.find('etsi:SigPolicyHash/ds:DigestMethod', namespaces=NS_MAP).get('Algorithm')
            doc_digest_data = policy_id.find('etsi:SigPolicyHash/ds:DigestValue', namespaces=NS_MAP).text
            logger.debug('Doc hash[{}] Digest[{}]'.format(hash_method, doc_digest_data))
        # Break the transform function

        if remote in self.cache and hash_method in self.cache[remote]:
            # logger.debug('Found remote {} with algo {} in cache'.format(remote, hash_method))
            digest_data = self.cache[remote][hash_method]
            if sign:
                digest_value.text = digest_data
            else:
                assert doc_digest_data == digest_data
        else:
            url = validate_hacienda_url(remote)
            if url is None:
                raise PolicyId2Exception('Invalid url')
            digest_data = request.urlopen(url).read()  # remote.encode()
            hash_calc = hashlib.new(xmlsig.constants.TransformUsageDigestMethod[hash_method])
            hash_calc.update(digest_data)
            digest_data = b64encode(hash_calc.digest()).decode()
            # logger.debug('New hash[{}] Digest[{}]'.format(hash_method, digest_data))
            if sign:
                digest_value.text = digest_data
            else:
                assert doc_digest_data == digest_data
            self.cache.setdefault(remote, {})[remote] = digest_data
        return policy_id

    def calculate_certificate(self, node, key_x509):
        cert = create_node('Cert', node, EtsiNS)
        cert_digest = create_node('CertDigest', cert, EtsiNS)
        digest_algorithm = create_node('DigestMethod', cert_digest, xmlsig.constants.DSigNs)
        digest_algorithm.set('Algorithm', self.hash_method)
        digest_value = create_node('DigestValue', cert_digest, xmlsig.constants.DSigNs)
        digest_value.text = b64encode(key_x509.fingerprint(MAP_HASHLIB[self.hash_method]()))
        issuer_serial = create_node('IssuerSerial', cert, EtsiNS)
        create_node('X509IssuerName', issuer_serial,
                    xmlsig.constants.DSigNs).text = get_reversed_rdns_name(key_x509.issuer.rdns)
        create_node('X509SerialNumber', issuer_serial, xmlsig.constants.DSigNs).text = str(key_x509.serial_number)
        return
