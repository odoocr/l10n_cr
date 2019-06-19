# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
	_inherit = 'res.company'

	html_bank_account1 = fields.Html(string="HTML Cuenta CRC")
	html_bank_account2 = fields.Html(string="HTML Cuenta USD")

