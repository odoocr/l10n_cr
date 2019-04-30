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


class ResCompany(models.Model):
	_inherit = 'res.company'

	bank_account1 = fields.Html(string="HTML Cuenta CRC")
	bank_account2 = fields.Html(string="HTML Cuenta USD")

