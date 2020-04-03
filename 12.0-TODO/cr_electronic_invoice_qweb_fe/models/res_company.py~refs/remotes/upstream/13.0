# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
<<<<<<< refs/remotes/upstream/13.0:12.0-TODO/cr_electronic_invoice_qweb_fe/models/res_company.py
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import datetime
import pytz
import base64
import xml.etree.ElementTree as ET

=======
>>>>>>> Many Fixes:cr_electronic_invoice_qweb_fe/models/res_company.py

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    html_bank_account1 = fields.Html(string="HTML Cuenta CRC")
    html_bank_account2 = fields.Html(string="HTML Cuenta USD")

class res_company(models.Model):
        _name = 'res.company'
        _inherit = ['res.company']

        cr_invoice_color = fields.Selection([('green','Green'),('sempai','Sempai'),('moresempai','More Sempai'),('blue', 'Blue'),('black', 'Black')],required=True,default='black')
