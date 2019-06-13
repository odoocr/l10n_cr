# -*- coding: utf-8 -*-

{
    'name': 'Codigos Pais para Facturación electrónica Costa Rica',
    'version': '12.0.2.0.0',
    'author': 'CRLibre.org',
    'license': 'AGPL-3',
    'website': 'https://www.delfixcr.com',
    'category': 'Account',
    'description':'''Codigos Pais para Facturación electronica Costa Rica.''',
    'depends': ['base', 'account', 'product'],
<<<<<<< HEAD
    'data': ['views/country_codes_views.xml',
             'data/res.country.state.xml',
             'data/res.country.county.xml',
             'data/res.country.district.xml',
             'data/res.country.neighborhood.xml',
=======
    'data': [
             'data/res.country.state.csv',
             'data/res.country.county.csv',
             'data/res.country.district.csv',
             'data/res.country.neighborhood.csv',
>>>>>>> ba2d0b3369c6b87a619abf1d387948690a8c1e7f
             'security/ir.model.access.csv',
             'views/country_codes_views.xml',
             ],
    'installable': True,
}
