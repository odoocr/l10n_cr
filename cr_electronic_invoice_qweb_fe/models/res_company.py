
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    html_bank_account1 = fields.Html(string="HTML Cuenta CRC")
    html_bank_account2 = fields.Html(string="HTML Cuenta USD")
    cr_invoice_color = fields.Selection([('green', 'Green'),
                                         ('sempai', 'Sempai'),
                                         ('moresempai', 'More Sempai'),
                                         ('blue', 'Blue'),
                                         ('black', 'Black')],
                                        required=True,
                                        default='black')
