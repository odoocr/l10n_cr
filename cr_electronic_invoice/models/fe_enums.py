from enum import Enum


class UrlHaciendaToken(Enum):
    apistag = 'https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token'
    apiprod = 'https://idp.comprobanteselectronicos.go.cr/auth/realms/rut/protocol/openid-connect/token'


class UrlHaciendaRecepcion(Enum):
    apistag = 'https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/recepcion/'
    apiprod = 'https://api.comprobanteselectronicos.go.cr/recepcion/v1/recepcion/'


class GrandTypes(Enum):
    TypePassword = 'password'
    TypeRefresh = 'refresh_token'


class TipoCedula(Enum):
    Fisico = 'fisico'
    Juridico = 'juridico'
    Dimex = 'dimex'
    Nite = 'nite'


class SituacionComprobante(Enum):
    normal = '1'
    contingencia = '2'
    sininternet = '3'

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)


class TipoDocumento(Enum):
    FE = '01'  # Factura Electrónica
    ND = '02'  # Nota de Débito
    NC = '03'  # Nota de Crédito
    TE = '04'  # Tiquete Electrónico
    CCE = '05'  # confirmacion comprobante electronico
    CPCE = '06'  # confirmacion parcial comprobante electronico
    RCE = '07'  # rechazo comprobante electronico

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)
