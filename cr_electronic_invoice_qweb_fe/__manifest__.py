# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name' : 'Costa Rica Electronic Invoice QWEB template',
    'version' : '10.0',
    'author' : 'CYSFuturo',
    'summary': 'Update Invoice QWEB template to meet DGT requirements for Costa Rica',
    'description': """
Update Invoice QWEB template to meet DGT requirements for Costa Rica
    """,
    'category': 'Accounting & Finance',
    'sequence': 4,
    'website' : 'http://cysfuturo.com',
    'depends' : ['cr_electronic_invoice', 'sale'],
    'demo' : [],
    'data' : [
        'views/res_company_view.xml',
        'views/report_sales_invoice_qweb.xml',
    ],
    'test' : [
    ],
    'auto_install': False,
    'application': True,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
