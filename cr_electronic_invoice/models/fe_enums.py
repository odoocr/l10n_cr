from enum import Enum


UrlHaciendaToken = {
    'api-stag' : 'https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token',
    'api-prod' : 'https://idp.comprobanteselectronicos.go.cr/auth/realms/rut/protocol/openid-connect/token',
}

UrlHaciendaRecepcion = {
    'api-stag' : 'https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/recepcion/',
    'api-prod' : 'https://api.comprobanteselectronicos.go.cr/recepcion/v1/recepcion/',
}

TipoCedula = {   # no se está usando !!
    'Fisico' : 'fisico',
    'Juridico' : 'juridico',
    'Dimex' : 'dimex',
    'Nite' : 'nite',
    'Extranjero' : 'extranjero',
}

SituacionComprobante = {
    'normal' : '1',
    'contingencia' : '2',
    'sininternet' : '3',
}

TipoDocumento = {
    'FE' : '01',  # Factura Electrónica
    'ND' : '02',  # Nota de Débito
    'NC' : '03',  # Nota de Crédito
    'TE' : '04',  # Tiquete Electrónico
    'CCE' : '05',  # confirmacion comprobante electronico
    'CPCE' : '06',  # confirmacion parcial comprobante electronico
    'RCE' : '07',  # rechazo comprobante electronico
    'FEC' : '08',  # Factura Electrónica de Compra
    'FEE' : '09',  # Factura Electrónica de Exportación
}
