# -*- coding: utf-8 -*-

{
    'name': 'Codigos Pais para Facturación electrónica Costa Rica',
    'version': '13.0.1.0.0',
    'author': 'Odoo CR',
    'license': 'AGPL-3',
    'website': 'https://github.com/odoocr',
    'category': 'Account',
    'description': '''Codigos Pais para Facturación electronica Costa Rica.''',
    'depends': ['base', 'account', 'product', ],
    'data': [
             'data/res.country.state.csv',
             'data/res.country.county.csv',
             'data/res.country.district.csv',
             'data/res.country.neighborhood.csv',
             'security/ir.model.access.csv',
             'views/country_codes_views.xml',
             'views/res_company_views.xml',
             'views/res_partner_views.xml',
             ],
    #"pre_init_hook": "pre_init_hook",
    'installable': True,
}
