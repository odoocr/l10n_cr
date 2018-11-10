# -*- coding: utf-8 -*-

{
	'name': 'Facturación electrónica Costa Rica POS',
	'version': '0.1',
	'author': 'DelfixCR',
    'license': 'OPL-1',
	'website': 'http://www.delfixcr.com',
	'category': 'Account',
	'description':
		'''
		Facturación electronica POS Costa Rica.
		''',
	'depends': ['cr_electronic_invoice','point_of_sale'],
	'data': [
		'views/electronic_invoice_views.xml',
		'data/data.xml',
		'views/pos_templates.xml',
		#'views/pos_views.xml',
	],
	'qweb': ['static/src/xml/pos.xml'],
	'installable': True,
}
