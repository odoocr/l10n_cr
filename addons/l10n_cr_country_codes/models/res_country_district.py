from odoo import models, fields


class ResCountryDistrict(models.Model):
    _name = "res.country.district"
    _description = "Country State County District Subdivision"
    _order = 'name'

    code = fields.Char(required=True)
    county_id = fields.Many2one("res.country.county", string="County", required=True)
    name = fields.Char(required=True)
