UrlHaciendaToken = {
    'api-stag': 'https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token',
    'api-prod': 'https://idp.comprobanteselectronicos.go.cr/auth/realms/rut/protocol/openid-connect/token',
}

UrlHaciendaRecepcion = {
    'api-stag': 'https://api-sandbox.comprobanteselectronicos.go.cr/recepcion/v1/recepcion/',
    'api-prod': 'https://api.comprobanteselectronicos.go.cr/recepcion/v1/recepcion/',
}

TipoCedula = {   # no se está usando !!
    'Fisico': 'fisico',
    'Juridico': 'juridico',
    'Dimex': 'dimex',
    'Nite': 'nite',
    'Extranjero': 'extranjero',
}

SituacionComprobante = {
    'normal': '1',
    'contingencia': '2',
    'sininternet': '3',
}

TipoDocumento = {
    'FE': '01',  # Factura Electrónica
    'ND': '02',  # Nota de Débito
    'NC': '03',  # Nota de Crédito
    'TE': '04',  # Tiquete Electrónico
    'CCE': '05',  # confirmacion comprobante electronico
    'CPCE': '06',  # confirmacion parcial comprobante electronico
    'RCE': '07',  # rechazo comprobante electronico
    'FEC': '08',  # Factura Electrónica de Compra
    'FEE': '09',  # Factura Electrónica de Exportación
}

# Xmlns used by Hacienda
XmlnsHacienda = {
    'FE': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica',
    'ND': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/notaDebitoElectronica',
    'NC': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/notaCreditoElectronica',
    'TE': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/tiqueteElectronico',
    'FEC': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronicaCompra',
    'FEE': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronicaExportacion'
}

schemaLocation = {
    'FE': 'https://atv.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2024/v4.4/FacturaElectronica_V4.4.xsd',
    'ND': 'https://atv.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2024/v4.4/NotaDebitoElectronica_V4.4.xsd',
    'NC': 'https://atv.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2024/v4.4/NotaCreditoElectronica_V4.4.xsd',
    'TE': 'https://atv.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2024/v4.4/TiqueteElectronico_V4.4.xsd',
    'FEC': 'https://atv.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2024/v4.4/FacturaElectronicaCompra_V4.4.xsd',
    'FEE': 'https://atv.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2024/v4.4/FacturaElectronicaExportacion_V4.4.xsd',
    'REP': 'https://atv.hacienda.go.cr/ATV/ComprobanteElectronico/docs/esquemas/2024/v4.4/ReciboElectronicoPago_V4.4.xsd'
}

tagName = {
    'FE': 'FacturaElectronica',  # Factura Electrónica
    'ND': 'NotaDebitoElectronica',  # Nota de Débito
    'NC': 'NotaCreditoElectronica',  # Nota de Crédito
    'TE': 'TiqueteElectronico',  # Tiquete Electrónico
    'FEC': 'FacturaElectronicaCompra',  # Factura Electrónica de Compra
    'FEE': 'FacturaElectronicaExportacion'  # Factura Electrónica de Exportación
}
