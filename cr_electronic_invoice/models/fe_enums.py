# -*- coding: utf-8 -*-
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
    Normal = '1'
    Contingencia = '2'
    SinInternet = '3'


class TipoDocumento(Enum):
    FE = '01'
    ND = '02'
    NC = '03'
    TE = '04'
    CCE = '05' #confirmacion comprobante electronico
    CPCE = '06' #confirmacion parcial comprobante electronico
    RCE = '07' #rechazo comprobante electronico
