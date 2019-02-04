# -*- coding: utf-8 -*-
# © 2017 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hmac

from .base import Algorithm


class HMACAlgorithm(Algorithm):
    @staticmethod
    def sign(data, private_key, digest):
        h = hmac.HMAC(
            private_key,
            digest(),
            backend=backends.default_backend()
        )
        h.update(data)
        return h.finalize()

    @staticmethod
    def verify(signature_value, data, public_key, digest):
        h = hmac.HMAC(
            public_key, digest(), backend=backends.default_backend()
        )
        h.update(data)
        h.verify(base64.b64decode(signature_value))