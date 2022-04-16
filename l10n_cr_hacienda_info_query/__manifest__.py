{
    "name": "Consultar Información de Clientes en Hacienda Costa Rica",
    "version": '14.0.1.0.0',
    "author": "Odoo Community Association (OCA), Odoo CR, Factura Sempai, FSS Solutions",
    "license": 'LGPL-3',
    "website": "https://github.com/odoocr/l10n_cr",
    "category": "API",
    "summary": """Consultar Nombre de Clientes en Hacienda Costa Rica""",
    "depends": [
        'base',
        'contacts',
        'point_of_sale',
        'base_setup'
    ],
    "data": [
        'data/res_config_settings.xml',
        'views/assets.xml',
        'views/res_config_settings_views.xml'
    ],
    "qweb": [
        'static/src/xml/Screens/ClientListScreen/ClientDetailsEdit.xml'
    ],
    "installable": True
}
