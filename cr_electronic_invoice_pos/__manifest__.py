# -*- coding: utf-8 -*-

{
	'name': 'Facturación electrónica Costa Rica POS',
	'version': '14.0.1.0.0',
	'author': 'TechMicro Inc S.A.',
    'license': 'OPL-1',
	'website': 'http://www.techmicrocr.com',
	'category': 'Account',
	'description':
		'''
		Facturación electronica POS Costa Rica.
		''',
	'depends': ['cr_electronic_invoice','point_of_sale'],
	'data': [
		'views/electronic_invoice_views.xml',
		'data/data.xml',
		'data/payment_methods_data.xml',
		'views/pos_payment_method.xml'
	],
	'assets': {
                'point_of_sale.assets': [
						'cr_electronic_invoice_pos/static/src/js/models.js'
                ],
                'web.assets_qweb': [
                        'l10n_cr_hacienda_info_query/static/src/xml/**/*',
                ]
    },
	'installable': True,
}
