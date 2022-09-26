
from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)

class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """

    reference_code_id = fields.Many2one("reference.code", string="Reference Code", required=True)
    reference_document_id = fields.Many2one("reference.document", string="Reference Document", required=True)

    def _prepare_default_reversal(self, move):
        default_values = super()._prepare_default_reversal(move)

        # Se realiza de esta forma ya que se pueden revertir documentos de tipo "entry" (asientos contables),
        # y no es necesario completar la información electrónica en estos documentos
        if move.move_type == 'entry':
            return {**default_values}
        # R1705(no-else-return)
        tipo_doc = False
        type_override = False
        if move.state_tributacion == 'rechazado':
            tipo_doc = 'disabled'
        elif move.move_type == 'out_refund':
            type_override = 'out_invoice'
            tipo_doc = 'ND'
        elif move.move_type == 'out_invoice':
            type_override = 'out_refund'
            tipo_doc = 'NC'
        elif move.move_type == 'in_invoice':
            type_override = 'in_refund'
            tipo_doc = 'NC'
        elif move.move_type == 'in_refund':
            tipo_doc = 'ND'
            type_override = 'in_invoice'
        else:
            return {**default_values}

        fe_values = {'invoice_id': move.id,
                     'tipo_documento': tipo_doc,
                     'reference_code_id': self.reference_code_id.id,
                     'reference_document_id': self.reference_document_id.id,
                     'economic_activity_id': move.economic_activity_id.id,
                     'payment_methods_id': move.payment_methods_id.id,
                     'state_tributacion': False}
        if type_override:
            fe_values['type_override'] = type_override

        return {**default_values, **fe_values}
