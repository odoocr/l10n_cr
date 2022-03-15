# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.translate import _
from odoo.exceptions import UserError

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from lxml import etree
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    reference_code_id = fields.Many2one("reference.code", string="Reference Code", required=True, )
    reference_document_id = fields.Many2one("reference.document", string="Reference Document Id", required=True, )

    def _prepare_default_reversal(self, move):
        default_values = super(AccountMoveReversal, self)._prepare_default_reversal(move)

        if move.tipo_documento in ('FE', 'TE') and move.state_tributacion == 'rechazado':
            type_override = 'out_invoice'
            tipo_doc = move.tipo_documento
        elif move.type == 'out_refund':
            type_override = 'out_invoice'
            tipo_doc = 'ND'
        elif move.type == 'out_invoice':
            type_override = 'out_refund'
            tipo_doc = 'NC'
        elif move.type == 'in_invoice':
            type_override = 'in_refund'
            tipo_doc = 'NC'
        else:
            tipo_doc = 'ND'
            type_override = 'in_invoice'

        fe_values = {'invoice_id': move.id,
                       'type_override': type_override,
                       'tipo_documento': tipo_doc,
                       'reference_code_id': self.reference_code_id.id,
                       'reference_document_id': self.reference_document_id.id,
                       'economic_activity_id': move.economic_activity_id.id,
                       'payment_methods_id': move.payment_methods_id.id,
                       'state_tributacion': False}

        return {**default_values, **fe_values}
    """
    ### MAB - CHECK IF NOT NEEDED !!!!!
    ### FE logic has been moved to _prepare_default_reversal, and number_electronic is assigned on post() so no need to call here
    def reverse_moves(self, mode='refund'):
        if self.env.user.company_id.frm_ws_ambiente == 'disabled':
            return super(AccountInvoiceRefund, self).reverse_moves(mode)
        moves = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.move_id

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        batches = [
            [self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], False],  # Others.
        ]
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = bool(default_vals.get('auto_post'))
            is_cancel_needed = not is_auto_post and self.refund_method in ('cancel', 'modify')
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)

            if self.refund_method == 'modify':
                moves_vals_list = []
                for move in moves.with_context(include_business_fields=True):
                    moves_vals_list.append(move.copy_data({'date': self.date or move.date})[0])
                new_moves = self.env['account.move'].create(moves_vals_list)

            moves_to_redirect |= new_moves

            for new_move in new_moves:
                if not new_move.number_electronic:
                    # if journal doesn't have sucursal use default from company
                    sucursal_id = new_move.journal_id.sucursal or self.env.user.company_id.sucursal_MR

                    # if journal doesn't have terminal use default from company
                    terminal_id = new_move.journal_id.terminal or self.env.user.company_id.terminal_MR

                    response_json = api_facturae.get_clave_hacienda(new_move,
                                                                new_move.tipo_documento,
                                                                new_move.name,
                                                                sucursal_id,
                                                                terminal_id)

                    new_move.number_electronic = response_json.get('clave')
                    new_move.sequence = response_json.get('consecutivo')
                    new_move.name = new_move.sequence

        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(moves_to_redirect) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': moves_to_redirect.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_to_redirect.ids)],
            })
        return action
    """
