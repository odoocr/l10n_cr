# -*- coding: utf-8 -*-

import json
import requests
import logging
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import datetime
import pytz
import base64
import xml.etree.ElementTree as ET


_logger = logging.getLogger(__name__)


class res_company(models.Model):
        _name = 'res.company'
        _inherit = ['res.company']

        html_bank_account1 = fields.Html(string="HTML Cuenta CRC")
        html_bank_account2 = fields.Html(string="HTML Cuenta USD")
        cr_invoice_color = fields.Selection([('green','Green'),('sempai','Sempai'),('moresempai','More Sempai'),('blue', 'Blue'),('black', 'Black')],required=True,default='black')
