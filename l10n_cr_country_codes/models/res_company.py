# copyright  2018 Carlos Wong, Akurey SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class CompanyElectronic(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'mail.thread', ]

    # Province
    state_id = fields.Many2one("res.country.state",
                               string="Province",
                               compute='_compute_address',
                               inverse='_inverse_state')

    # Canton
    county_id = fields.Many2one("res.country.county",
                                string="Canton",
                                compute='_compute_address',
                                inverse='_inverse_county')

    # District
    district_id = fields.Many2one("res.country.district",
                                  string="District",
                                  compute='_compute_address',
                                  inverse='_inverse_district')

    # Neighborhood
    neighborhood_id = fields.Many2one("res.country.neighborhood",
                                      string="Neighborhood",
                                      compute='_compute_address',
                                      inverse='_inverse_neighborhood')

    # When you change the province you must clean the other fields to avoid inconveniences
    @api.onchange('state_id')
    def _change_state_id(self):
        self.county_id = False
        self.district_id = False
        self.neighborhood_id = False

    # When you change the canton you must clean the other fields to avoid inconveniences

    @api.onchange('county_id')
    def _change_county_id(self):
        self.district_id = False
        self.neighborhood_id = False

    # When you change the district you must clean the other fields to avoid inconveniences

    @api.onchange('district_id')
    def _calculate_postal_code(self):
        if self.state_id.code and self.county_id.code and self.district_id.code:
            postal = str(self.state_id.code) + str(self.county_id.code) + str(self.district_id.code)
            self.zip = postal
        else:
            self.zip = False
        self.neighborhood_id = False

    # When the neighborhood changes, the city field of odoo is autocomplete

    @api.onchange('neighborhood_id')
    def _change_neighborhood_id(self):
        self.city = self.neighborhood_id.name

    def _get_company_address_field_names(self):
        """ Return a list of fields coming from the address partner to match
        on company address fields. Fields are labeled same on both models. """
        res = super()._get_company_address_field_names()
        res.append('neighborhood_id')
        res.append('district_id')
        res.append('county_id')
        return res

    def _compute_address(self):
        for company in self.filtered(lambda company: company.partner_id):
            address_data = company.partner_id.sudo().address_get(adr_pref=['contact'])
            if address_data['contact']:
                partner = company.partner_id.browse(address_data['contact']).sudo()
                company.update(company._get_company_address_update(partner))

    def _inverse_state(self):
        for company in self:
            company.partner_id.state_id = company.state_id

    def _inverse_county(self):
        for company in self:
            company.partner_id.county_id = company.county_id

    def _inverse_district(self):
        for company in self:
            company.partner_id.district_id = company.district_id

    def _inverse_neighborhood(self):
        for company in self:
            company.partner_id.neighborhood_id = company.neighborhood_id
