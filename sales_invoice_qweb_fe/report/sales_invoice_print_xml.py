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

import time
from openerp.osv import osv
from openerp.report import report_sxw
from openerp.tools import amount_to_text_en
#from common_report_header import common_report_header

class sales_invoice_print(report_sxw.rml_parse): #, common_report_header):
    #_name = 'report.sales.invoice.print'
    def __init__(self, cr, uid, name, context):
        super(sales_invoice_print, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_digits':self.get_digits,
            'time': time,
        })
        self.context = context


class report_sales_invoice_qweb(osv.AbstractModel):
    _name = 'report.sales_invoice_qweb.report_sales_invoice_qweb'
    _inherit = 'report.abstract_report'
    _template = 'account.report_invoice_document'
    _wrapped_report_class = sales_invoice_print

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
