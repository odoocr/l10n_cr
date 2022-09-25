# copyright  2018 Carlos Wong, Akurey S.A.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from zeep import Client
from datetime import timedelta, datetime
import xml.etree.ElementTree
import logging
import requests

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    rate = fields.Float(digits='Currency Rate Precision')

    # -------------------------------------------------------------------------
    # CRON
    # -------------------------------------------------------------------------

    def _cron_create_missing_exchange_rates(self):
        for currency in self.env['res.currency'].search([('id', '!=', self.env.user.company_id.currency_id.id)]):
            currency.action_create_missing_exchange_rates()

    # -------------------------------------------------------------------------
    # PUBLIC ACTIONS
    # -------------------------------------------------------------------------

    def action_create_missing_exchange_rates(self):
        currency_rate_obj = self.env['res.currency.rate']
        # A day is added to fix the loss of the current day
        today = datetime.today().date()
        last_day = today + timedelta(days=1)

        first_day = currency_rate_obj.search([
            ('company_id', '=', self.env.user.company_id.id),
            ('currency_id', '=', self.id)
        ], limit=1, order='name asc')
        # If there is no record, you must fill the table with the current day
        if not first_day:
            # It is validated that the currency is dollars
            if self.id == self.env.ref('base.USD').id:
                # This will create the record of the day the option is run manually
                currency_rate_obj._cron_update()
        else:
            range_day = last_day - first_day.name
            date = first_day.name
            for day in range(range_day.days):
                if self.id == self.env.ref('base.USD').id:
                    # It is validated if the exchange rate of that day really not exists
                    if not currency_rate_obj.search([('name', '=', date)], limit=1):
                        # TODO: It could be improved to make only one request and avoid one per day
                        currency_rate_obj._cron_update(date, date)
                    # If after updating it does not exist, it will be loaded on the last available day
                    if not currency_rate_obj.search([('name', '=', date)], limit=1):
                        currency_rate_obj._create_the_latest_exchange_rate_to_date(self, date)
                date += timedelta(days=1)
