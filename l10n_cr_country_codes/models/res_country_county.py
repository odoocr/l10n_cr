from odoo import models, fields


class ResCountryCounty(models.Model):
    _name = "res.country.county"
    _description = "Country State County Subdivision"
    _order = 'name'

    code = fields.Char(required=True)
    state_id = fields.Many2one("res.country.state", string="Province", required=True)
    name = fields.Char(required=True)
