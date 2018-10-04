# -*- coding: utf-8 -*-

{
    "name": "Punto de venta adaptado Costa Rica",
    "category": "Point Of Sale",
    "author": "Jason Ulloa Hernandez, "
              "Techmicro Inc, "
              "Techmicro International Company S.A., "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-spain",
    "license": "AGPL-3",
    "version": "11.0.1.0.1",
    "depends": [
        "point_of_sale","base", "cr_electronic_invoice",
    ],
    "data": [
        "views/pos_templates.xml",
        "views/pos_views.xml",
    ],
    "qweb": [
        "static/src/xml/pos.xml",
    ],
    "installable": True
}