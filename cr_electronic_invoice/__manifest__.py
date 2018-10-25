# -*- coding: utf-8 -*-

{
	'name': 'Facturación electrónica Costa Rica',
	'version': '0.1',
	'author': 'CRLibre.org',
	'license': 'AGPL-3',
	'website': 'https://crlibre.org/',
	'category': 'Account',
	'description':
		'''
		Facturación electronica Costa Rica.
		''',
	'depends': ['base', 'account','product','sales_team','l10n_cr_country_codes','account_cancel'],
	'data': ['data/data.xml',
	         'data/code.type.product.csv',
	         'data/identification.type.csv',
	         'data/payment.methods.csv',
	         'data/reference.code.csv',
	         'data/reference.document.csv',
	         'data/sale.conditions.csv',
	         'data/product.uom.csv',
	         'data/account.tax.csv',
			 'data/sequence.xml',
			 'data/mail_template_data.xml',
			 'views/account_journal_views.xml',
			 'views/electronic_invoice_views.xml',
			 #'views/report_sales_invoice_qweb.xml',
	         'security/ir.model.access.csv',
	         ],
	'installable': True,
}
