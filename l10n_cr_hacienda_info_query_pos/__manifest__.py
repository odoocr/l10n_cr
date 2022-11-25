{
    "name": "Consultar Información de Clientes en Hacienda Costa Rica - TPV",
    'version': '15.0.1.0.0',
    "author": "Odoo CR, Factura Sempai, FSS Solutions",
    'license': 'LGPL-3',
    "website": "https://github.com/odoocr/l10n_cr",
    'category': 'Hidden',
    "summary": """Consultar Nombre de Clientes en Hacienda Costa Rica - TPV""",
    "description": """Actualización automática de nombre de clientes a partir del API de Hacienda - TPV""",
    "depends": ['base', 'contacts', 'point_of_sale', 'l10n_cr_hacienda_info_query'],
    'assets': {
        'point_of_sale.assets': [
            'l10n_cr_hacienda_info_query_pos/static/src/js/actualizar_pos.js',
            'l10n_cr_hacienda_info_query_pos/static/src/js/models.js',
            'l10n_cr_hacienda_info_query_pos/static/src/js/Screens/ClientListScreen/ClientDetailsEdit.js'
        ],
        'web.assets_qweb': [
            'l10n_cr_hacienda_info_query_pos/static/src/xml/**/*',
        ]
    },
    "installable": True
}
