# -*- coding: utf-8 -*-

{
    'name': 'QR Facturación Electrónica Costa Rica',
    'version': '0.1',
    'author': 'TechMicro Inc S.A.',
    'website': 'https://www.techmicrocr.com',
    'category': 'Account',
    'description':'''Este módulo ayuda a generar el código QR basado en la URL del documento.''',
    'depends': ['cr_electronic_invoice'],
    'data': [
        #'report/account_invoice_report_template.xml',
        'views/qr_code_invoice_view.xml',
        'views/qr_code_purchase_view.xml',
        'views/qr_code_sale_view.xml',
             ],
    'installable': True,
}
