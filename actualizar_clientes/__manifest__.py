# -*- coding: utf-8 -*-
{
        "name" : "Actualizar Nombre de Clientes",
        "version" : "12.0.1.1",
        "author" : "FSS Solutions",
        'license': 'LGPL-3',
        "website" : "https://fss-cr.com",
        "category" : "API",
        "summary": """Actualizar Nombre de Clientes""",
        "description": """Actualización automática de nombre de clientes a partir de API""",
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