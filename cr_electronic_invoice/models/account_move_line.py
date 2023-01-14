from odoo import models, fields, api, _
from odoo.exceptions import UserError

from xml.sax.saxutils import escape


class InvoiceLineElectronic(models.Model):
    _inherit = "account.move.line"

    # ==============================================================================================
    #                                          INVOICE LINE
    # ==============================================================================================

    discount_note = fields.Char()
    total_tax = fields.Float()
    third_party_id = fields.Many2one(
        comodel_name="res.partner",
        string="Third - other charges"
    )
    tariff_head = fields.Char(
        string="Tariff item for export invoice"
    )
    categ_name = fields.Char(
        related='product_id.categ_id.name'
    )
    product_code = fields.Char(
        related='product_id.default_code'
    )
    economic_activity_id = fields.Many2one(
        comodel_name="economic.activity",
        string="Economic activity",
        store=True,
        context={
            'active_test': False
        },
        default=False
    )
    non_tax_deductible = fields.Boolean(
        string='Indicates if this invoice is non-tax deductible'
    )
    cabys_code = fields.Char(
        related="product_id.cabys_code",
    )

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('product_id')
    def product_changed(self):
        # Check if the product is non deductible to use a non_deductible tax
        if self.product_id.non_tax_deductible:
            taxes = []
            self.non_tax_deductible = True
            for tax in self.tax_ids:
                new_tax = self.env['account.tax'].search(
                    [
                        ('tax_code', '=', tax.tax_code),
                        ('amount', '=', tax.amount),
                        ('type_tax_use', '=', 'purchase'),
                        ('non_tax_deductible', '=', True),
                        ('active', '=', True)
                    ],
                    limit=1
                )
                if new_tax:
                    taxes.append((3, tax.id))
                    taxes.append((4, new_tax.id))
                else:
                    raise UserError(_('There is no "Non tax deductible" tax with the tax percentage of this product'))
            self.tax_ids = taxes
        else:
            self.non_tax_deductible = False

        # Check for the economic activity in the product or
        # product category or company respectively (already set in the invoice when partner selected)
        if self.product_id and self.product_id.economic_activity_id:
            self.economic_activity_id = self.product_id.economic_activity_id
        elif self.product_id and self.product_id.categ_id and self.product_id.categ_id.economic_activity_id:
            self.economic_activity_id = self.product_id.categ_id.economic_activity_id
        else:
            self.economic_activity_id = self.move_id.economic_activity_id

    # -------------------------------------------------------------------------
    # TOOLING
    # -------------------------------------------------------------------------

    @api.model
    def _get_default_activity_id(self):
        for line in self:
            line.economic_activity_id = line.product_id and line.product_id.categ_id and \
                line.product_id.categ_id.economic_activity_id and line.product_id.categ_id.economic_activity_id.id
