# -*- coding: utf-8 -*-

{
    'name': 'Codigos Pais para Facturación electrónica Costa Rica',
    'version': '0.1',
    'author': 'CRLibre.org',
    'license': 'AGPL-3',
    'website': 'https://www.delfixcr.com',
    'category': 'Account',
    'description': '''Codigos Pais para Facturación electronica Costa Rica.''',
    'depends': ['base', 'account', 'product', 'l10n_cr'],
    'data': ['views/country_codes_views.xml',
             'data/res.country.county.csv',
             'data/res.country.state.csv',
             'data/res.country.district.csv',
             'data/res.country.neighborhood.csv',
             'security/ir.model.access.csv',
             ],
    'installable': True,
}
