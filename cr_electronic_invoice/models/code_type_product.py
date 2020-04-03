# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class CodeTypeProduct(models.Model):
    _name = "code.type.product"

    code = fields.Char(string="Code", required=False, )
    name = fields.Char(string="Name", required=False, )
