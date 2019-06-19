# -*- encoding: utf-8 -*-

{
    'name': 'Notas Debito Costa Rica',
    'version': '10.0.0.1.0',
    'author': "Jason Ulloa",
    'maintainer': 'TechMicro Inc S.A.',
    'website': 'http://www.techmicrocr.com',
    'license': 'AGPL-3',
    'category': 'Account',
    'summary': 'Habilita Notas de Débito para Costa Rica',
    'depends': ['cr_electronic_invoice'],
    'description': """
Contabilidad: Nota de Debito y Credito
=============================================================================
- Agrega el menú de "Nota Debito" en facturas de clientes y proveedores.
- Agregar opción en vista de formulario para crear Notas de Debito.
        """,
    'data': [
        'data/journal_data.xml',
        'wizards/account_invoice_debit_view.xml',
        'views/account_invoice_view.xml',
    ],
    'installable': True,
}
