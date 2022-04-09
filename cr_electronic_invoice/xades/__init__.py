import xmlsig
from lxml import etree
__all__ = ['get_reversed_rdns_name']

# This file should be imported after xmlsig or byitself if only XadesContext is used.


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


def b64_print(s_variable):
    return s_variable


# Monkey patching xmlsig functions to remove unecesary tail and body newlines
xmlsig.signature_context.b64_print = b64_print
xmlsig.algorithms.rsa.b64_print = b64_print
