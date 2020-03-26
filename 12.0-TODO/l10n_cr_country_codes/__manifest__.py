# -*- coding: utf-8 -*-

{
    'name': 'Codigos Pais para Facturación electrónica Costa Rica',
    'version': '12.0.2.0.0',
    'author': 'Odoo CR',
    'license': 'AGPL-3',
    'website': 'https://github.com/odoocr',
    'category': 'Account',
    'description': '''Codigos Pais para Facturación electronica Costa Rica.''',
    'depends': ['base', 'account', 'product', 'l10n_cr'],
    'data': [
             'data/res.country.state.csv',
             'data/res.country.county.csv',
             'data/res.country.district.csv',
             'data/res.country.neighborhood.csv',
             'security/ir.model.access.csv',
             'views/country_codes_views.xml',
             ],
    #"pre_init_hook": "pre_init_hook",
    'installable': True,
}
