# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class AccountJournalInherit(models.Model):
    _name = 'account.journal'
    _inherit = ['account.journal']

    sucursal = fields.Integer(string="Sucursal", required=False, default="1")
    terminal = fields.Integer(string="Terminal", required=False, default="1")
    nd = fields.Boolean(string="Nota de Débito", required=False, )
