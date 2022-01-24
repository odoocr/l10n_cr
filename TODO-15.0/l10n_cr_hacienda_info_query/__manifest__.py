# -*- coding: utf-8 -*-
{
        "name" : "Consultar Información de Clientes en Hacienda Costa Rica",
        'version': '15.0.1.0.0',
        "author" : "Odoo CR, Factura Sempai, FSS Solutions",
        'license': 'LGPL-3',
        "website" : "https://github.com/odoocr/l10n_cr",
        "category" : "API",
        "summary": """Consultar Nombre de Clientes en Hacienda Costa Rica""",
        "description": """Actualización automática de nombre de clientes a partir del API de Hacienda""",
        "depends" : ['base','contacts', 'point_of_sale'],
        "data" : [
                'views/res_company.xml'
                ],
        'assets': {
                'point_of_sale.assets': [
                        'l10n_cr_hacienda_info_query/static/src/js/actualizar_pos.js',
                        'l10n_cr_hacienda_info_query/static/src/js/models.js',
                        'l10n_cr_hacienda_info_query/static/src/js/Screens/ClientListScreen/ClientDetailsEdit.js'
                ],
                'web.assets_qweb': [
                        'l10n_cr_hacienda_info_query/static/src/xml/**/*',
                ]
        },
        "installable": True
}
