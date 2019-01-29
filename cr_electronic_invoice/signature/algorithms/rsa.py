# -*- coding: utf-8 -*-
# © 2017 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from base64 import b64encode, b64decode

from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

from .base import Algorithm
from ..ns import DSigNs, NS_MAP
from ..utils import create_node, long_to_bytes, b64_print, os2ip


class RSAAlgorithm(Algorithm):
    private_key_class = rsa.RSAPrivateKey
    public_key_class = rsa.RSAPublicKey

    @staticmethod
    def sign(data, private_key, digest):
        return private_key.sign(
            data,
            padding.PKCS1v15(),
            digest()
        )

    @staticmethod
    def verify(signature_value, data, public_key, digest):
        public_key.verify(
            b64decode(signature_value),
            data,
            padding.PKCS1v15(),
            digest()
        )

    @staticmethod
    def key_value(node, public_key):
        result = create_node(
            #'RSAKeyValue', node, DSigNs, '\n', '\n'
            'RSAKeyValue', node, DSigNs
        )
        create_node(
            'Modulus',
            result,
            DSigNs,
            #tail='\n',
            text=b64_print(b64encode(long_to_bytes(
                public_key.public_numbers().n
            )))
        )
        create_node(
            'Exponent',
            result,
            DSigNs,
            #tail='\n',
            text=b64encode(long_to_bytes(public_key.public_numbers().e))
        )
        return result

    @staticmethod
    def get_public_key(key_info, ctx):
        """
        Get the public key if its defined in X509Certificate node. Otherwise,
        take self.public_key element
        :param sign: Signature node
        :type sign: lxml.etree.Element
        :return: Public key to use
        """
        key = key_info.find(
            'ds:KeyInfo/ds:KeyValue/ds:RSAKeyValue', namespaces=NS_MAP
        )
        if key is not None:
            n = os2ip(b64decode(key.find(
                'ds:Modulus', namespaces=NS_MAP).text))
            e = os2ip(b64decode(key.find(
                'ds:Exponent', namespaces=NS_MAP).text))
            return rsa.RSAPublicNumbers(e, n).public_key(default_backend())
        return super(RSAAlgorithm, RSAAlgorithm).get_public_key(key_info, ctx)