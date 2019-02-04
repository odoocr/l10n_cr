# -*- coding: utf-8 -*-
# © 2017 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from cryptography.hazmat.primitives import hashes

from .algorithms import RSAAlgorithm, HMACAlgorithm
from .ns import DSigNs, DSigNs11, NS_MAP, DSignNsMore, EncNs

ID_ATTR = 'Id'

TransformInclC14N = 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315'
TransformInclC14NWithComments = TransformInclC14N + '#WithComments'
TransformInclC14N11 = ''
TransformInclC14N11WithComments = ''
TransformExclC14N = 'http://www.w3.org/2001/10/xml-exc-c14n#'
TransformExclC14NWithComments = TransformExclC14N + 'WithComments'
TransformEnveloped = DSigNs + 'enveloped-signature'
TransformXPath = 'http://www.w3.org/TR/1999/REC-xpath-19991116'
TransformXPath2 = ''
TransformXPointer = ''
TransformXslt = 'http://www.w3.org/TR/1999/REC-xslt-19991116'
TransformRemoveXmlTagsC14N = ''
TransformBase64 = DSigNs + 'base64'
TransformVisa3DHack = ''
TransformAes128Cbc = ''
TransformAes192Cbc = ''
TransformAes256Cbc = ''
TransformKWAes128 = ''
TransformKWAes192 = ''
TransformKWAes256 = ''
TransformDes3Cbc = ''
TransformKWDes3 = ''
TransformDsaSha1 = DSigNs + 'dsa-sha1'
TransformDsaSha256 = DSigNs11 + 'dsa-sha256'
TransformEcdsaSha1 = DSignNsMore + 'ecdsa-sha1'
TransformEcdsaSha224 = DSignNsMore + 'ecdsa-sha224'
TransformEcdsaSha256 = DSignNsMore + 'ecdsa-sha256'
TransformEcdsaSha384 = DSignNsMore +'cdsa-sha384'
TransformEcdsaSha512 = DSignNsMore + 'ecdsa-sha512'
TransformHmacRipemd160 = DSignNsMore + 'hmac-ripemd160'
TransformHmacSha1 = DSigNs + 'hmac-sha1'
TransformHmacSha224 = DSignNsMore + 'hmac-sha224'
TransformHmacSha256 = DSignNsMore + 'hmac-sha256'
TransformHmacSha384 = DSignNsMore + 'hmac-sha384'
TransformHmacSha512 = DSignNsMore + 'hmac-sha512'
TransformRsaMd5 = DSignNsMore + 'rsa-md5'
TransformRsaRipemd160 = DSignNsMore + 'rsa-ripemd160'
TransformRsaSha1 = DSigNs + 'rsa-sha1'
TransformRsaSha224 = DSignNsMore + 'rsa-sha224'
TransformRsaSha256 = DSignNsMore + 'rsa-sha256'
TransformRsaSha384 = DSignNsMore + 'rsa-sha384'
TransformRsaSha512 = DSignNsMore + 'rsa-sha512'
TransformRsaPkcs1 = ''
TransformRsaOaep = ''
TransformMd5 = DSignNsMore + 'md5'
TransformRipemd160 = EncNs + 'ripemd160'
TransformSha1 = DSigNs + 'sha1'
TransformSha224 = DSignNsMore + 'sha224'
TransformSha256 = EncNs + 'sha256'
TransformSha384 = DSignNsMore + 'sha384'
TransformSha512 = EncNs + 'sha512'

TransformUsageUnknown = {

}
TransformUsageDSigTransform = [
    TransformEnveloped,
    TransformBase64
]
TransformUsageC14NMethod = {
    TransformInclC14N: {
        'method': 'c14n',
        'exclusive': False,
        'comments': False
    },
    TransformInclC14NWithComments: {
        'method': 'c14n',
        'exclusive': False,
        'comments': True
    },
    TransformExclC14N: {
        'method': 'c14n',
        'exclusive': True,
        'comments': False
    },
    TransformExclC14NWithComments: {
        'method': 'c14n',
        'exclusive': True,
        'comments': False
    }
}

TransformUsageDSigTransform.extend(TransformUsageC14NMethod.keys())

TransformUsageDigestMethod = {
    TransformMd5: 'md5',
    TransformSha1: 'sha1',
    TransformSha224: 'sha224',
    TransformSha256: 'sha256',
    TransformSha384: 'sha384',
    TransformSha512: 'sha512',
    TransformRipemd160: 'ripemd160',
}

TransformUsageSignatureMethod = {
    TransformRsaMd5: {
        'digest': hashes.MD5, 'method': RSAAlgorithm
    },
    TransformRsaSha1: {
        'digest': hashes.SHA1, 'method': RSAAlgorithm
    },
    TransformRsaSha224: {
        'digest': hashes.SHA224, 'method': RSAAlgorithm
    },
    TransformRsaSha256: {
        'digest': hashes.SHA256, 'method': RSAAlgorithm
    },
    TransformRsaSha384: {
        'digest': hashes.SHA384, 'method': RSAAlgorithm
    },
    TransformRsaSha512: {
        'digest': hashes.SHA512, 'method': RSAAlgorithm
    },
    TransformHmacSha1: {
        'digest': hashes.SHA1, 'method': HMACAlgorithm
    },
    TransformHmacSha224: {
        'digest': hashes.SHA256, 'method': HMACAlgorithm
    },
    TransformHmacSha256: {
        'digest': hashes.SHA256, 'method': HMACAlgorithm
    },
    TransformHmacSha384: {
        'digest': hashes.SHA384, 'method': HMACAlgorithm
    },
    TransformHmacSha512: {
        'digest': hashes.SHA512, 'method': HMACAlgorithm
    }
}

TransformUsageEncryptionMethod = {}
TransformUsageAny = {}