
from odoo import models, api, tools, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, float_is_zero, config


class BusinessDocumentImportCR(models.AbstractModel):
    _inherit = ['business.document.import']

    @api.model
    def _match_uom(self, uom_dict, chatter_msg, product=False):
        uuo = self.env['product.uom']
        uoms = uuo.search([('code', '=', uom_dict['cr_code'])])

        if uoms:
            return uoms[0]
        else:
            chatter_msg.append(_(
                "The analysis of the business document returned '%s' "
                "as the unit of measure Hacienda code, but there is no "
                "unit of measure with that Hacienda code in Odoo. Please "
                "check the configuration of the units of measures in "
                "Odoo.") % uom_dict['cr_code'])
            return self.env.ref('uom.product_uom_unit')

    @api.model
    def _match_tax(self, tax_dict, chatter_msg, type_tax_use='purchase', price_include=False):
        ato = self.env['account.tax']
        self._strip_cleanup_dict(tax_dict)
        if tax_dict.get('recordset'):
            return tax_dict['recordset']
        if tax_dict.get('id'):
            return ato.browse(tax_dict['id'])
        company_id = self._context.get('force_company') or\
            self.env.user.company_id.id
        domain = [('company_id', '=', company_id)]
        if type_tax_use == 'purchase':
            domain.append(('type_tax_use', '=', 'purchase'))
        elif type_tax_use == 'sale':
            domain.append(('type_tax_use', '=', 'sale'))
        if price_include is False:
            domain.append(('price_include', '=', False))
        elif price_include is True:
            domain.append(('price_include', '=', True))
        # with the code above, if you set price_include=None, it will
        # won't depend on the value of the price_include parameter
        assert tax_dict.get('amount_type') in ['fixed', 'percent'],\
            'bad tax type'
        assert 'amount' in tax_dict, 'Missing amount key in tax_dict'
        domain.append(('amount_type', '=', tax_dict['amount_type']))

        taxes = ato.search(domain, order='unece_due_date_code')
        for tax in taxes:
            tax_amount = tax.amount  # 'amount' field : digits=(16, 4)
            if not float_compare(tax_dict['amount'], tax_amount, precision_digits=4):
                return tax
        raise self.user_error_wrap(_(
            "Odoo couldn't find any tax with 'Tax Application' = '%s' "
            "and 'Tax Included in Price' = '%s' which correspond to the "
            "following information extracted from the business document:\n"
            "Tax Type code: %s\n"
            "Tax Category code: %s\n"
            "Tax amount: %s %s") % (
                type_tax_use,
                price_include,
                tax_dict['amount'],
                tax_dict['amount_type'] == 'percent' and '%' or _('(fixed)')))
