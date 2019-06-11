# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCountryCounty(models.Model):
    _name = "res.country.county"
    _order = 'name'

    code = fields.Char(string="Código", required=True, )
    state_id = fields.Many2one(comodel_name="res.country.state", string="Provincia", required=True)
    name = fields.Char(string="Nombre", required=True, )


class ResCountryDistrict(models.Model):
    _name = "res.country.district"
    _order = 'name'

    code = fields.Char(string="Código", required=True, )
    county_id = fields.Many2one(comodel_name="res.country.county", string="Cantón", required=True)
    name = fields.Char(string="Nombre", required=True, )


class ResCountryNeighborhood(models.Model):
    _name = "res.country.neighborhood"
    _order = 'name'

    code = fields.Char(string="Código", required=True, )
    district_id = fields.Many2one(comodel_name="res.country.district", string="Distrito", required=True)
    name = fields.Char(string="Nombre", required=True, )
