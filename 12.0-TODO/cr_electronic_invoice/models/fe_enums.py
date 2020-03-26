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

# Xmlns used by Hacienda
XmlnsHacienda = {
    'FE': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronica',  # Factura Electrónica
    'ND': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/notaDebitoElectronica',  # Nota de Débito
    'NC': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/notaCreditoElectronica',  # Nota de Crédito
    'TE': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/tiqueteElectronico',  # Tiquete Electrónico
    'FEC': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronicaCompra',  # Factura Electrónica de Compra
    'FEE': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronicaExportacion',  # Factura Electrónica de Exportación
}

schemaLocation = {
    'FE': 'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/FacturaElectronica_V4.3.xsd',  # Factura Electrónica
    'ND': 'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/NotaDebitoElectronica_V4.3.xsd',  # Nota de Débito
    'NC': 'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/NotaCreditoElectronica_V4.3.xsd',  # Nota de Crédito
    'TE': 'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/TiqueteElectronico_V4.3.xsd',  # Tiquete Electrónico
    'FEC': 'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/FacturaElectronicaCompra_V4.3.xsd',  # Factura Electrónica de Compra
    'FEE': 'https://www.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2016/v4.3/FacturaElectronicaExportacion_V4.3.xsd',  # Factura Electrónica de Exportación
}

tagName = {
    'FE': 'FacturaElectronica',  # Factura Electrónica
    'ND': 'NotaDebitoElectronica',  # Nota de Débito
    'NC': 'NotaCreditoElectronica',  # Nota de Crédito
    'TE': 'TiqueteElectronico',  # Tiquete Electrónico
    'FEC': 'FacturaElectronicaCompra',  # Factura Electrónica de Compra
    'FEE': 'FacturaElectronicaExportacion',  # Factura Electrónica de Exportación
}