# -*- coding: utf-8 -*-
# © 2016-2017 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Invoice Import FE Costa Rica',
    'version': '10.0.1.0.0',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Import FE Costa Rica XML supplier invoices/refunds',
    'author': 'Costa Rica Odoo Community',
    'website': 'http://www.crlibre.org',
    'depends': ['account_invoice_import', 'base_fe_cr'],
    'data': [
            'views/res_config_settings_views.xml',
            'wizard/account_invoice_import_view.xml'
        ],
    'installable': True,
}
