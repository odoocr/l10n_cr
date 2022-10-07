from odoo import models, fields


class ResCountryNeighborhood(models.Model):
    _name = "res.country.neighborhood"
    _description = "Country State County District Neighborhood Subdivision"
    _order = 'name'

    code = fields.Char(required=True)
    district_id = fields.Many2one("res.country.district", string="District", required=True)
    name = fields.Char(required=True)
