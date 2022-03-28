

from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)


class ResCountryCounty(models.Model):
    _name = "res.country.county"
    _description = "Country State County Subdivision"
    _order = 'name'

    code = fields.Char(required=True)
    state_id = fields.Many2one("res.country.state", string="Province", required=True)
    name = fields.Char(required=True)


class ResCountryDistrict(models.Model):
    _name = "res.country.district"
    _description = "Country State County District Subdivision"
    _order = 'name'

    code = fields.Char(required=True)
    county_id = fields.Many2one("res.country.county", string="County", required=True)
    name = fields.Char(required=True)


class ResCountryNeighborhood(models.Model):
    _name = "res.country.neighborhood"
    _description = "Country State County District Neighborhood Subdivision"
    _order = 'name'

    code = fields.Char(required=True)
    district_id = fields.Many2one("res.country.district", string="District", required=True)
    name = fields.Char(required=True)
