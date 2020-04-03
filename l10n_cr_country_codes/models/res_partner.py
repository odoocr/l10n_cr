# copyright  2018 Carlos Wong, Akurey SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _

class PartnerElectronic(models.Model):
    _inherit = "res.partner"

    state_id = fields.Many2one("res.country.state", string="Province", required=False, )
    district_id = fields.Many2one("res.country.district", string="District", required=False, )
    county_id = fields.Many2one("res.country.county", string="Canton", required=False, )
    neighborhood_id = fields.Many2one("res.country.neighborhood", string="Neighborhood", required=False, )