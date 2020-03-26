# -*- coding: utf-8 -*-
{
        "name" : "Consultar Información de Clientes en Hacienda Costa Rica",
        "version" : "12.0.1.1",
        "author" : "Odoo CR, Factura Sempai, FSS Solutions",
        'license': 'LGPL-3',
        "website" : "https://github.com/odoocr/l10n_cr",
        "category" : "API",
        "summary": """Consultar Nombre de Clientes en Hacienda Costa Rica""",
        "description": """Actualización automática de nombre de clientes a partir del API de Hacienda""",
        "depends" : ['base','contacts', 'point_of_sale'],
        "data" : [
                'views/actualizar_clientes_view.xml',
                'views/pos_templates.xml',
                ],
        'qweb':[
                'static/src/xml/actualizar_pos.xml',
                ],
        "installable": True
}
