# copyright  2018 Carlos Wong, Akurey S.A.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Costa Rica Currency Adapter',
	'version': '12.0.0.1',
    'category': 'Account',
    'author': "Akurey S.A.",
    'website': 'https://github.com/akurey/ak-odoo',
    'license': 'AGPL-3',
    'depends': ['base'],
    'data': [
        'data/currency_data.xml',
        'views/res_currency_rate_view.xml'
    ],
    'installable': True,
    'auto_install': False,
}
