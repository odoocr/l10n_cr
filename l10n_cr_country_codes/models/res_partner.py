# copyright  2018 Carlos Wong, Akurey SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)..

from odoo import models, fields, api


class PartnerElectronic(models.Model):
    _inherit = "res.partner"

    # Province
    state_id = fields.Many2one("res.country.state", string="Province")

    # Canton
    county_id = fields.Many2one("res.country.county", string="Canton")

    # District
    district_id = fields.Many2one("res.country.district", string="District")

    # Neighborhood
    neighborhood_id = fields.Many2one("res.country.neighborhood", string="Neighborhood")

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
