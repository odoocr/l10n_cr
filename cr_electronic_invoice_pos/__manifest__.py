{
    'name': 'Facturación electrónica Costa Rica POS',
    'version': '14.0.1.0.0',
    'author': 'TechMicro Inc S.A.',
    'license': 'OPL-1',
    'website': 'http://www.techmicrocr.com',
    'category': 'Account',
    'depends': [
        'cr_electronic_invoice',
        'point_of_sale',
    ],
    'data': [
        'views/electronic_invoice_views.xml',
        'data/data.xml',
        'data/payment_methods_data.xml',
        'views/pos_payment_method.xml',
        'views/pos_templates.xml'
    ],
    'qweb': [
        'static/src/xml/pos.xml',
        ],
    'installable': True,
}
