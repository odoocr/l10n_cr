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


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    def try_migrate_old_l10n_cr(self):
        self.env.cr.execute(
            "SELECT module FROM ir_model_data WHERE model=%s AND name='state_SJ'", (self._name)
        )
        if self.env.cr.fetchone() == 'l10n_cr':
            self.env.cr.execute(
                "UPDATE ir_model_data SET name=lower(name) WHERE model=%s AND module='l10n_cr'",
                (self._name)
            )
            self.env.cr.execute(
                "UPDATE ir_model_data SET module='l10n_cr_country_codes' "
                "WHERE model=%s AMD module='l10n_cr'",
                (self._name)
            )
