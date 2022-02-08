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
                                     string="Secuencia de Facturas Electrónicas",
                                     required=False)

    TE_sequence_id = fields.Many2one("ir.sequence",
                                     string="Secuencia de Tiquetes Electrónicos",
                                     required=False)

    FEE_sequence_id = fields.Many2one("ir.sequence",
                                      string="Secuencia de Facturas Electrónicas de Exportación",
                                      required=False)

    NC_sequence_id = fields.Many2one("ir.sequence",
                                     string="Secuencia de Notas de Crédito Electrónicas",
                                     required=False)

    ND_sequence_id = fields.Many2one("ir.sequence",
                                     string="Secuencia de Notas de Débito Electrónicas",
                                     required=False)
    
    expense_product_id = fields.Many2one(
        'product.product',
        string=_("Default product for expenses when loading data from XML"),
        help=_("The default product used when loading Costa Rican digital invoice"))

    expense_account_id = fields.Many2one(
        'account.account',
        string=_("Default Expense Account when loading data from XML"),
        help=_("The expense account used when loading Costa Rican digital invoice"))

    expense_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string=_("Default Analytic Account for expenses when loading data from XML"),
        help=_("The analytic account used when loading Costa Rican digital invoice"))

    load_lines = fields.Boolean(
        string=_('Indicates if invoice lines should be load when loading a Costa Rican Digital Invoice'),
        default=True
    )
