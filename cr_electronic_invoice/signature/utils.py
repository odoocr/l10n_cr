# -*- coding: utf-8 -*-
# © 2017 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import struct
import sys

from cryptography.x509 import oid
from lxml import etree

OID_NAMES = {
    oid.NameOID.COMMON_NAME: 'CN',
    oid.NameOID.COUNTRY_NAME: 'C',
    oid.NameOID.DOMAIN_COMPONENT: 'DC',
    oid.NameOID.EMAIL_ADDRESS: 'E',
    oid.NameOID.GIVEN_NAME: 'G',
    oid.NameOID.LOCALITY_NAME: 'L',
    oid.NameOID.ORGANIZATION_NAME: 'O',
    oid.NameOID.ORGANIZATIONAL_UNIT_NAME: 'OU',
    oid.NameOID.SURNAME: 'SN'
}

USING_PYTHON2 = True if sys.version_info < (3, 0) else False
b64_intro = 64


def b64_print(s):
    """
    Prints a string with spaces at every b64_intro characters
    :param s: String to print
    :return: String
    """
    if USING_PYTHON2:
        string = str(s)
    else:
        string = str(s, 'utf8')

    return ''.join(
        string[pos:pos + b64_intro] for pos in range(0, len(string), b64_intro)
    )

    #return '\n'.join(
    #    string[pos:pos + b64_intro] for pos in range(0, len(string), b64_intro)
    #)


def long_to_bytes(n, blocksize=0):
    """long_to_bytes(n:long, blocksize:int) : string
    Convert a long integer to a byte string.
    If optional blocksize is given and greater than zero, pad the front of the
    byte string with binary zeros so that the length is a multiple of
    blocksize.
    """
    # after much testing, this algorithm was deemed to be the fastest
    s = b''
    if USING_PYTHON2:
        n = long(n)  # noqa
    pack = struct.pack
    while n > 0:
        s = pack(b'>I', n & 0xffffffff) + s
        n = n >> 32
    # strip off leading zeros
    for i in range(len(s)):
        if s[i] != b'\000'[0]:
            break
    else:
        # only happens when n == 0
        s = b'\000'
        i = 0
    s = s[i:]
    # add back some pad bytes.  this could be done more efficiently w.r.t. the
    # de-padding being done above, but sigh...
    if blocksize > 0 and len(s) % blocksize:
        s = (blocksize - len(s) % blocksize) * b'\000' + s
    return s


def os2ip(arr):
    x_len = len(arr)
    x = 0
    for i in range(x_len):
        if USING_PYTHON2:
            val = struct.unpack('B', arr[i])[0]
        else:
            val = arr[i]
        x = x + (val * pow(256, x_len - i - 1))
    return x


def create_node(name, parent=None, ns='', tail=False, text=False):
    """
    Creates a new node
    :param name: Node name
    :param parent: Node parent
    :param ns: Namespace to use
    :param tail: Tail to add
    :param text: Text of the node
    :return: New node
    """
    node = etree.Element(etree.QName(ns, name))
    if parent is not None:
        parent.append(node)
    if tail:
        node.tail = tail
    if text:
        node.text = text
    return node


def get_rdns_name(rdns):
    """
    Gets the rdns String name
    :param rdns: RDNS object
    :type rdns: cryptography.x509.RelativeDistinguishedName
    :return: RDNS name
    """
    name = ''
    for rdn in rdns:
        for attr in rdn._attributes:
            if len(name) > 0:
                name = name + ','
            if attr.oid in OID_NAMES:
                name = name + OID_NAMES[attr.oid]
            else:
                name = name + attr.oid._name
            name = name + '=' + attr.value
    return name