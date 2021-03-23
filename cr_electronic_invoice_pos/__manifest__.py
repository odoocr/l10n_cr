# -*- coding: utf-8 -*-

{
	'name': 'Facturación electrónica Costa Rica POS',
	'version': '12.0.2.0.0',
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
		'views/pos_templates.xml',
		'data/data.xml',
		#'views/pos_views.xml',
	],
	'qweb': ['static/src/xml/pos.xml'],
	'installable': True,
}
