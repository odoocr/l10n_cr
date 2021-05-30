# -*- coding: utf-8 -*-

from odoo import models, fields
import logging


_logger = logging.getLogger(__name__)


class ResCountryCounty(models.Model):
    _name = "res.country.county"
    _description = "Country State County Subdivision"
    _order = 'name'

    code = fields.Char(string="Código", required=True, )
    state_id = fields.Many2one("res.country.state", string="Provincia", required=True)
    name = fields.Char(string="Nombre", required=True, )


class ResCountryDistrict(models.Model):
    _name = "res.country.district"
    _description = "Country State County District Subdivision"
    _order = 'name'

    code = fields.Char(string="Código", required=True, )
    county_id = fields.Many2one("res.country.county", string="Cantón", required=True)
    name = fields.Char(string="Nombre", required=True, )


class ResCountryNeighborhood(models.Model):
    _name = "res.country.neighborhood"
    _description = "Country State County District Neighborhood Subdivision"
    _order = 'name'

    code = fields.Char(string="Código", required=True, )
    district_id = fields.Many2one("res.country.district", string="Distrito", required=True)
    name = fields.Char(string="Nombre", required=True, )


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    def try_migrate_old_l10n_cr(self):
        return
        _logger.info('Check if needed to migrate old l10n_cr states')
        self.env.cr.execute(
            "SELECT module FROM ir_model_data WHERE model=%s AND name='state_SJ'", (self._name,)
        )
        if self.env.cr.fetchone() == 'l10n_cr':
            _logger.info('Proceed to migrade old l10n_cr states')
            self.env.cr.execute(
                "UPDATE ir_model_data SET name=lower(name) WHERE model=%s AND module='l10n_cr'",
                (self._name,)
            )
            self.env.cr.execute(
                "UPDATE ir_model_data SET module='l10n_cr_country_codes' "
                "WHERE model=%s AMD module='l10n_cr'",
                (self._name,)
            )
