import xmlsig
from lxml import etree
__all__ = ['xmlsig_create', 'create_node', 'get_reversed_rdns_name']

# This file should be imported after xmlsig or byitself if only XadesContext is used.


def xmlsig_create(c14n_method=False, sign_method=False, name=False, ns='ds', value_name=None):
    node = etree.Element(etree.QName(xmlsig.constants.DSigNs, 'Signature')
                         , nsmap={ns: xmlsig.constants.DSigNs})
    if name:
        node.set(xmlsig.constants.ID_ATTR, name)
    signed_info = xmlsig.utils.create_node('SignedInfo', node, xmlsig.constants.DSigNs)
    canonicalization = xmlsig.utils.create_node('CanonicalizationMethod'
                                                , signed_info, xmlsig.constants.DSigNs)
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
#xmlsig.template.create = xmlsig_create
#xmlsig.template.add_key_name = xmlsig_add_key_name
#xmlsig.template.add_x509_data = make_xmlsig_template_function('X509Data')
#xmlsig.template.x509_data_add_certificate = make_xmlsig_template_function('X509Certificate')
#xmlsig.template.x509_data_add_crl = make_xmlsig_template_function('X509CRL')
#xmlsig.template.x509_data_add_issuer_serial = make_xmlsig_template_function('X509IssuerSerial')
#xmlsig.template.x509_data_add_ski = make_xmlsig_template_function('X509SKI')
#xmlsig.template.x509_data_add_subject_name = make_xmlsig_template_function('X509SubjectName')
#xmlsig.template.x509_issuer_serial_add_issuer_name = make_xmlsig_template_function('X509IssuerName')
#xmlsig.template.x509_issuer_serial_add_serial_number = make_xmlsig_template_function('X509SerialNumber')
#xmlsig.template.create_node = create_node
xmlsig.signature_context.b64_print = b64_print
#xmlsig.algorithms.rsa.create_node = create_node
xmlsig.algorithms.rsa.b64_print = b64_print
