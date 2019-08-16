# -*- coding: utf-8 -*-
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class CodeTypeProduct(models.Model):
    _name = "code.type.product"

    code = fields.Char(string="Código", required=False, )
    name = fields.Char(string="Nombre", required=False, )
