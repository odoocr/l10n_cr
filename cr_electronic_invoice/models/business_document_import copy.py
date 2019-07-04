from odoo import models, api, _
from odoo.tools import float_compare
from odoo.addons.base_iban.models.res_partner_bank import validate_iban
from odoo.exceptions import UserError
from lxml import etree
from io import BytesIO
import mimetypes
from urllib.parse import urlparse
import logging
logger = logging.getLogger(__name__)

try:
    import PyPDF2
except ImportError:
    logger.debug('Cannot import PyPDF2')

class PartnerHookBusinessDocImport(models.AbstractModel):
    _inherit = 'business.document.import'
    _description = 'Hook to create a supplier while importing electronic invoices'

    @api.model
    def _hook_match_partner(
            self, partner_dict, chatter_msg, domain, partner_type_label):

        partner = self.env['res.partner'].search([
            ('vat', '=', partner_dict.get('vat'))])
        if not partner:
            country_id = self.env['res.country'].search([
                ('code', '=', partner_dict.get('country_code'))]).id
            county_id = self.env['res.country.county'].search([
                ('id', '=', partner_dict.get('county_code'))]).id
            district_id = self.env['res.country.district'].search([
                ('id', '=', partner_dict.get('district_code'))]).id
            partner = self.env['res.partner'].sudo().create({
                'name': partner_dict.get('name'),
                'commercial_name': partner_dict.get('name'),
                'vat': partner_dict.get('vat'),
                'country_id': country_id,
                'county_id': county_id,
                'district_id': district_id,
                'phone': partner_dict.get('phone'),
                'email': partner_dict.get('email'),
                'supplier': True,
                'customer': False,
            })
        return partner

    @api.model
    def _match_tax(
            self, tax_dict, chatter_msg,
            type_tax_use='purchase', price_include=False):
        """Example:
        tax_dict = {
            'amount_type': 'percent',  # required param, 'fixed' or 'percent'
            'amount': 20.0,  # required
            'unece_type_code': 'VAT',
            'unece_categ_code': 'S',
            'unece_due_date_code': '432',
            }
        """
        ato = self.env['account.tax']
        self._strip_cleanup_dict(tax_dict)
        if tax_dict.get('recordset'):
            return tax_dict['recordset']
        if tax_dict.get('id'):
            return ato.browse(tax_dict['id'])
        domain = []
        prec = self.env['decimal.precision'].precision_get('Account')
        # we should not use the Account prec directly, but...
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
        if tax_dict.get('unece_type_code'):
            domain.append(
                ('unece_type_code', '=', tax_dict['unece_type_code']))
        if tax_dict.get('unece_categ_code'):
            domain.append(
                ('unece_categ_code', '=', tax_dict['unece_categ_code']))
        if tax_dict.get('unece_due_date_code'):
            domain += [
                '|',
                ('unece_due_date_code', '=', tax_dict['unece_due_date_code']),
                ('unece_due_date_code', '=', False)]
        taxes = ato.search(domain, order='unece_due_date_code')
        for tax in taxes:
            tax_amount = tax.amount
            if not float_compare(tax_dict['amount'], tax_amount, precision_digits=prec):
                return tax
            tax_code = tax.tax_code
        tax_name = ('Type: ' + type_tax_use + ', Ammount: ' + repr(tax_dict['amount']))
        new_tax = self.env['account.tax'].sudo().create({
            'tax_code': tax_dict['tax_code'],
            'type_tax_use': type_tax_use,
            'name': tax_name,
            'amount_type': tax_dict['amount_type'],
            'amount': tax_dict['amount'],
        })
        return new_tax


class DocumentDefaultConfig(models.TransientModel):
    _inherit = 'account.invoice.import'
    _description = 'Create a default configuration if it doesnt exists in the \
                    system when importing electronic invoices'

    @api.model
    def _default_config(self, partner, company_id):
        account = self.env['account.account'].search([
            ('code', '=', '20-01-01-02-01')])
        import_configs = self.env['account.invoice.import.config'].sudo().create({
            'name': _("Default import configuration: %s") % (partner.name),
            'partner_id': partner.id,
            'invoice_line_method': 'nline_no_product',
            'account_id': account.id,
            'company_id': company_id,
        })
        import_conf = import_configs.convert_to_import_config()
        return import_conf
