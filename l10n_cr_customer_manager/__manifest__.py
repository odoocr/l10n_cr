# -*- coding: utf-8 -*-

{
    'name': 'Administración Clientes Costa Rica',
    'version': '12.0.2.0.0',
    'author': 'FSS Solutions',
    'license': 'AGPL-3',
    'website': 'https://www.delfixcr.com',
    'category': 'Account',
    'description':'''Codigos Pais para Facturación electronica Costa Rica.''',
    'depends': ['base', 'account', 'product'],
    'data': ['views/country_codes_views.xml',
             'data/res.country.county.csv',
             'data/res.country.state.xml',
             'data/res.country.district.csv',
             'data/res.country.neighborhood.csv',
             'security/ir.model.access.csv',
             ],
    'installable': True,
}
