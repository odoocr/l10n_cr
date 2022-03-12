import time
from odoo.osv import osv
from odoo.report import report_sxw


# from common_report_header import common_report_header

class SalesInvoicePrint(report_sxw.rml_parse):  # , common_report_header):
    # _name = 'report.sales.invoice.print'
    def __init__(self, cr, uid, name, context):
        super(SalesInvoicePrint, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_digits': self.get_digits,
            'time': time,
        })
        self.context = context


class ReportSalesInvoiceQWeb(osv.AbstractModel):
    _name = 'report.sales_invoice_qweb.report_sales_invoice_qweb'
    _inherit = 'report.abstract_report'
    _template = 'account.report_invoice_document'
    _wrapped_report_class = SalesInvoicePrint
