# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class AccountJournalInherit(models.Model):
    _name = 'account.journal'
    _inherit = 'account.journal'

    sucursal = fields.Integer(string="Branch", required=False, default="1")
    terminal = fields.Integer(string="Terminal", required=False, default="1")

    FE_sequence_id = fields.Many2one("ir.sequence",
                                     string="Electronic Invoice Sequence",
                                     required=False)

    TE_sequence_id = fields.Many2one("ir.sequence",
                                     string="Electronic Ticket Sequence",
                                     required=False)

    FEE_sequence_id = fields.Many2one("ir.sequence",
                                      string="Sequence of Electronic Export Invoices",
                                      required=False)

    NC_sequence_id = fields.Many2one("ir.sequence",
                                     string="Electronic Credit Notes Sequence",
                                     required=False)

    ND_sequence_id = fields.Many2one("ir.sequence",
                                     string="Electronic Debit Notes Sequence",
                                     required=False)

