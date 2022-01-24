# -*- coding: utf-8 -*-

import logging
from typing import Sequence

from odoo import api, fields, models,_
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

class invoiceQrFields(models.Model):
    _name = 'invoice.qr.fields'
    _order = 'sequence'

    sequence = fields.Integer()
    field_id = fields.Many2one('ir.model.fields',domain=[('model_id.model','=','account.move'),('ttype','not in',['many2many','one2many','binary'])])
    company_id = fields.Many2one('res.company')