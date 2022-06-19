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

    def _cron_create_missing_exchange_rates(self):
        for currency in self.env['res.currency'].search([('id', '!=', self.env.user.company_id.currency_id.id)]):
            currency.action_create_missing_exchange_rates()

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


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    # Change decimal presicion to work with CRC where 1 USD is more de 555 CRC
    rate = fields.Float(string='Selling Rate',
                        digits='Currency Rate Precision')

    # Costa Rica uses two exchange rates:
    #   - Buying exchange rate - used when a financial institutions buy USD from you (rate)
    #   - Selling exchange rate - used when financial institutions sell USD to you (rate_2)
    rate_2 = fields.Float(string='Buying Rate', digits='Currency Rate Precision',
                          help='The buying rate of the currency to the currency of rate 1.')

    # Rate as it is get
    original_rate = fields.Float(string='Selling Rate in Costa Rica', digits=(6, 2),
                                 help='The selling exchange rate from CRC to USD as it is send from BCCR')

    # Rate as it is get
    original_rate_2 = fields.Float(string='Buying Rate in Costa Rica', digits=(6, 2),
                                   help='The buying exchange rate from CRC to USD as it is send from BCCR')

    @api.model
    def _cron_update(self, first_date=False, last_date=False):

        _logger.info("=========================================================")
        _logger.info("Executing exchange rate update from 1 CRC = X USD")

        exchange_source = self.env['ir.config_parameter'].sudo().get_param('exchange_source')
        if exchange_source == 'bccr':
            _logger.info("Getting exchange rates from BCCR")
            bccr_username = self.env['ir.config_parameter'].sudo().get_param('bccr_username')
            bccr_email = self.env['ir.config_parameter'].sudo().get_param('bccr_email')
            bccr_token = self.env['ir.config_parameter'].sudo().get_param('bccr_token')

            # Get current date to get exchange rate for today
            if first_date:
                initial_date = first_date.strftime('%d/%m/%Y')
                end_date = last_date.strftime('%d/%m/%Y')
            else:
                initial_date = datetime.now().date().strftime('%d/%m/%Y')
                end_date = initial_date

            # Web Service Connection using the XML schema from BCCRR
            client = Client('https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx?WSDL')

            response = client.service.ObtenerIndicadoresEconomicosXML(
                Indicador='318', FechaInicio=initial_date, FechaFinal=end_date,
                Nombre=bccr_username, SubNiveles='N', CorreoElectronico=bccr_email, Token=bccr_token)

            xml_response = xml.etree.ElementTree.fromstring(response)
            selling_rate_nodes = xml_response.findall("./INGC011_CAT_INDICADORECONOMIC")

            # Get Buying exchange Rate from BCCR
            response = client.service.ObtenerIndicadoresEconomicosXML(
                Indicador='317', FechaInicio=initial_date, FechaFinal=end_date,
                Nombre=bccr_username, SubNiveles='N', CorreoElectronico=bccr_email, Token=bccr_token)

            xml_response = xml.etree.ElementTree.fromstring(response)
            buying_rate_nodes = xml_response.findall("./INGC011_CAT_INDICADORECONOMIC")

            selling_rate = 0
            buying_rate = 0
            node_index = 0
            if len(selling_rate_nodes) > 0 and len(selling_rate_nodes) == len(buying_rate_nodes):
                while node_index < len(selling_rate_nodes):
                    if selling_rate_nodes[node_index].find("DES_FECHA").text == \
                       buying_rate_nodes[node_index].find("DES_FECHA").text:
                        current_date_str = datetime.strptime(selling_rate_nodes[node_index].find("DES_FECHA").text,
                                                             "%Y-%m-%dT%H:%M:%S-06:00").strftime('%Y-%m-%d')

                        selling_original_rate = float(selling_rate_nodes[node_index].find("NUM_VALOR").text)
                        buying_original_rate = float(buying_rate_nodes[node_index].find("NUM_VALOR").text)

                        # Odoo uses the value of 1 unit of the base currency divided between the exchage rate
                        selling_rate = 1 / selling_original_rate
                        buying_rate = 1 / buying_original_rate

                        # GET THE CURRENCY ID
                        currency_id = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)

                        # Get the rate for this date to know it is already registered
                        rates_ids = self.env['res.currency.rate'].search([('name', '=', current_date_str)], limit=1)

                        if len(rates_ids) > 0:
                            rates_ids.write(
                                {'rate': selling_rate,
                                 'inverse_company_rate': selling_original_rate,
                                 'original_rate': selling_original_rate,
                                 'rate_2': buying_rate,
                                 # 'inverse_company_rate_2': buying_original_rate,
                                 'original_rate_2': buying_original_rate,
                                 'currency_id': currency_id.id}
                                )
                        else:
                            self.create(
                                {'name': current_date_str,
                                 'rate': selling_rate,
                                 'inverse_company_rate': selling_original_rate,
                                 'original_rate': selling_original_rate,
                                 'rate_2': buying_rate,
                                 'original_rate_2': buying_original_rate,
                                 # 'inverse_company_rate_2': buying_original_rate,
                                 'currency_id': currency_id.id})

                        _logger.info({'name': current_date_str,
                                      'rate': selling_rate,
                                      'inverse_company_rate': selling_original_rate,
                                      'original_rate': selling_original_rate,
                                      'rate_2': buying_rate,
                                      'original_rate_2': buying_original_rate,
                                      # 'inverse_company_rate_2': buying_original_rate,
                                      'currency_id': currency_id.id})
                    else:
                        buy_des_fecha = buying_rate_nodes[node_index].find("DES_FECHA").text
                        sell_des_fecha = selling_rate_nodes[node_index].find("DES_FECHA").text
                        _logger.error("Error loading currency rates, dates for a buying (%s) ", buy_des_fecha)
                        _logger.error("and selling (%s) rates don't match", sell_des_fecha)

                    node_index += 1
            else:
                _logger.error("Error loading currency rates,dates range data for buying and selling rates don't match")

        if exchange_source == 'hacienda':
            _logger.info("Getting exchange rates from HACIENDA")

            # Get current date to get exchange rate for today
            if first_date:
                initial_date = first_date.strftime('%Y-%m-%d')
                end_date = last_date.strftime('%Y-%m-%d')

                try:
                    url = 'https://api.hacienda.go.cr/indicadores/tc/dolar/historico/?d='+initial_date+'&h='+end_date
                    response = requests.get(url, timeout=5, verify=False)

                except requests.exceptions.RequestException as e:
                    _logger.error('RequestException %s', e)
                    return False
                if response.status_code in (200,):
                    data = response.json()
                    companies = self.env['res.company'].search([])
                    for company in companies:
                        _logger.error(company.id)

                        for rate_line in data:
                            today = datetime.strptime(rate_line['fecha'], '%Y-%m-%d %H:%M:%S')
                            vals = {}
                            vals['original_rate'] = rate_line['venta']
                            vals['inverse_company_rate'] = rate_line['venta']
                            # Odoo utiliza un valor inverso,
                            # a cuantos dólares equivale 1 colón, por eso se divide 1 / tipo de cambio.
                            vals['rate'] = 1 / rate_line['original_rate']
                            vals['original_rate_2'] = rate_line['compra']
                            # vals['inverse_company_rate_2'] = rate_line['compra']
                            vals['rate_2'] = 1 / rate_line['original_rate_2']
                            vals['currency_id'] = self.env.ref('base.USD').id

                            rate_id = self.env['res.currency.rate'].search([('name', '=', today.date())], limit=1)

                            if rate_id:
                                rate_id.write(vals)
                            else:
                                vals['name'] = today.date()
                                self.create(vals)
            else:
                try:
                    url = 'https://api.hacienda.go.cr/indicadores/tc'
                    response = requests.get(url, timeout=5, verify=False)

                except requests.exceptions.RequestException as e:
                    _logger.error('RequestException %s', e)
                    return False

                if response.status_code in (200,):
                    # Save the exchange rate in database
                    today = datetime.now().strftime('%Y-%m-%d')
                    data = response.json()
                    companies = self.env['res.company'].search([])
                    for company in companies:
                        _logger.error(company.id)
                        vals = {}
                        vals['original_rate'] = data['dolar']['venta']['valor']
                        vals['inverse_company_rate'] = data['dolar']['venta']['valor']

                        # Odoo utiliza un valor inverso,
                        # a cuantos dólares equivale 1 colón, por eso se divide 1 / tipo de cambio.

                        vals['rate'] = 1 / vals['original_rate']
                        vals['original_rate_2'] = data['dolar']['compra']['valor']
                        # vals['inverse_company_rate_2'] = data['dolar']['compra']['valor']
                        vals['rate_2'] = 1 / vals['original_rate_2']
                        vals['currency_id'] = self.env.ref('base.USD').id

                        rate_id = self.env['res.currency.rate'].search([('name', '=', today)], limit=1)

                        if rate_id:
                            rate_id.write(vals)
                        else:
                            vals['name'] = today
                            self.create(vals)

                _logger.info(vals)

        _logger.info("=========================================================")

    def _create_the_latest_exchange_rate_to_date(self, currency, date=None):
        name = date or datetime.now()
        currency_rate_obj = self.env['res.currency.rate'].search([
            ('company_id', '=', self.env.user.company_id.id),
            ('currency_id', '=', currency.id),
            ('name', '<=', name),
        ], limit=1, order='name desc')

        if currency_rate_obj.name == name:
            return

        self.create({
            'name': name,
            'rate': currency_rate_obj.rate,
            'inverse_company_rate': currency_rate_obj.inverse_company_rate,
            'original_rate': currency_rate_obj.original_rate,
            'rate_2': currency_rate_obj.rate_2,
            'original_rate_2': currency_rate_obj.original_rate_2,
            # 'inverse_company_rate_2': currency_rate_obj.inverse_company_rate_2,
            'currency_id': currency_rate_obj.currency_id.id,
            'company_id': currency_rate_obj.company_id.id,
        })
