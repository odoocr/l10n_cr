# -*- coding: utf-8 -*-
# © 2017 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import base64

from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_der_x509_certificate

from .. import ns


class Algorithm(object):
    private_key_class = None
    public_key_class = None

    @staticmethod
    def sign(data, private_key, digest):
        raise Exception("Sign function must be redefined")

    @staticmethod
    def verify(signature_value, data, public_key, digest):
        raise Exception("Verify function must be redefined")

    @staticmethod
    def key_value(node, public_key):
        raise Exception("Key Value function must be redefined")

    @staticmethod
    def get_public_key(key_info, ctx):
        """
        Get the public key if its defined in X509Certificate node. Otherwise,
        take self.public_key element
        :param sign: Signature node
        :type sign: lxml.etree.Element
        :return: Public key to use
        """
        x509_certificate = key_info.find(
            'ds:KeyInfo/ds:X509Data/ds:X509Certificate',
            namespaces={'ds': ns.DSigNs}
        )
        if x509_certificate is not None:
            return load_der_x509_certificate(
                base64.b64decode(x509_certificate.text),
                default_backend()
            ).public_key()
        if ctx.public_key is not None:
            return ctx.public_key
        if isinstance(ctx.private_key, (str, bytes)):
            return ctx.private_key
        return ctx.private_key.public_key()