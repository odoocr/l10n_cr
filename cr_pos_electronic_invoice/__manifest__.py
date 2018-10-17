# -*- coding: utf-8 -*-

{
	'name': 'Tiquete Electronico Costa Rica',
	'version': '0.1',
	'author': 'JackDevelopers',
	'license': 'OPL-1',
	'website': 'https://www.jackdevelopers.com',
	'category': 'pos',
	'description':
		'''
		Tiquete Electronico Costa Rica.
		''',
	'depends': ['base', 'cr_electronic_invoice', 'point_of_sale'],
	'data': ['views/pos_templates.xml','views/pos_views.xml','data/data.xml'],
    'qweb': ['static/src/xml/*.xml'],
	'installable': True,
}
