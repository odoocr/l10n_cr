# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "POS Electronico Costa Rica",
    "category": "Point Of Sale",
    "author": "Jason Ulloa Hernandez, "
              "TechMicro Inc S.A.",
    "website": "https://www.techmicrocr.com",
    "license": "AGPL-3",
    "version": "1.0",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "views/pos_templates.xml",
        "views/pos_views.xml",
    ],
    "qweb": [
        "static/src/xml/pos.xml",
    ],
    "installable": True,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
