# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
import odoo.addons.decimal_precision as dp


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.depends('ticket_hacienda_invoice_sequence_id.number_next_actual',
                 'ticket_hacienda_invoice_sequence_id.prefix',
                 'ticket_hacienda_invoice_sequence_id.padding')

    def _compute_ticket_hacienda_invoice_sequence(self):
        for pos in self:
            seq = pos.ticket_hacienda_invoice_sequence_id

            pos.ticket_hacienda_invoice_number = (
                seq._get_current_sequence().number_next_actual)

            pos.ticket_hacienda_invoice_prefix = (
                seq._get_prefix_suffix()[0])

            pos.ticket_hacienda_invoice_padding = seq.padding

    iface_ticket_hacienda_simplified_invoice = fields.Boolean(
        string='Use simplified invoices for this POS',
    )

    ticket_hacienda_invoice_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Simplified Invoice IDs Sequence',
        help="Autogenerate for each POS created",
        copy=False,
        readonly=True,
    )

    ticket_hacienda_invoice_limit = fields.Float(
        string='Sim.Inv limit amount',
        digits=dp.get_precision('Account'),
        help='Over this amount is not legally posible to create '
             'a simplified invoice',
        default=3000,  # Spanish legal limit
        oldname='ticket_hacienda_invoice_limit',
    )

    ticket_hacienda_invoice_prefix = fields.Char(
        'Simplified Invoice prefix',
        readonly=True,
        compute='_compute_ticket_hacienda_invoice_sequence',
        oldname='ticket_hacienda_invoice_prefix',
    )

    ticket_hacienda_invoice_padding = fields.Integer(
        'Simplified Invoice padding',
        readonly=True,
        compute='_compute_ticket_hacienda_invoice_sequence',
        oldname='ticket_hacienda_invoice_padding',
    )

    ticket_hacienda_invoice_number = fields.Integer(
        'Sim.Inv number',
        readonly=True,
        compute='_compute_ticket_hacienda_invoice_sequence',
        oldname='simple_invoice_number',
    )

    @api.model
    def create(self, vals):
        # Auto create simp. inv. sequence
        prefix = "%s%s" % (vals['name'], self._get_default_prefix())
        simp_inv_seq_id = self.env['ir.sequence'].create({
            'name': _('Ticket_Hacienda %s') % vals['name'],
            'implementation': 'no_gap',
            'padding': self._get_default_padding(),
            'prefix': prefix,
            'code': 'pos.config.ticket_hacienda_invoice',
            'company_id': vals.get('company_id', False),
        })
        vals['ticket_hacienda_invoice_sequence_id'] = simp_inv_seq_id.id
        return super(PosConfig, self).create(vals)

    def copy(self, default=None):
        ctx = dict(self._context)
        ctx.update(copy_pos_config=True)
        return super(PosConfig, self.with_context(ctx)).copy(default)

    def write(self, vals):
        if not self._context.get('copy_pos_config') and 'name' not in vals:
            for pos in self:
                pos.ticket_hacienda_invoice_sequence_id\
                    .check_simplified_invoice_unique_prefix()
        if 'name' in vals:
            prefix = self.ticket_hacienda_invoice_prefix.replace(
                self.name, vals['name'])
            if prefix != self.ticket_hacienda_invoice_prefix:
                self.ticket_hacienda_invoice_sequence_id.update({
                    'prefix': prefix,
                    'name': (self.ticket_hacienda_invoice_sequence_id
                             .name.replace(self.name, vals['name'])),
                })
        return super(PosConfig, self).write(vals)

    def unlink(self):
        self.mapped('ticket_hacienda_invoice_sequence_id').unlink()
        return super(PosConfig, self).unlink()

    def _get_default_padding(self):
        return self.env['ir.config_parameter'].get_param(
            'cr_pos_electronic_invoice.simplified_invoice_sequence.padding', 4)

    def _get_default_prefix(self):
        return self.env['ir.config_parameter'].get_param(
            'cr_pos_electronic_invoice.simplified_invoice_sequence.prefix', '')

    def _get_l10n_es_sequence_name(self):
        """HACK: This is done for getting the proper translation."""
        return _('Simplified Invoice %s')
