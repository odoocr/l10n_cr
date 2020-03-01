# copyright  2018 Carlos Wong, Akurey S.A.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from zeep import Client
import datetime
import xml.etree.ElementTree
import logging
import requests

_logger = logging.getLogger(__name__)


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency'

    rate = fields.Float(digits=dp.get_precision('Currency Rate Precision'))


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    # Change decimal presicion to work with CRC where 1 USD is more de 555 CRC
    rate = fields.Float(string='Selling Rate',
                        digits=dp.get_precision('Currency Rate Precision'))

    # Costa Rica uses two exchange rates:
    #   - Buying exchange rate - used when a financial institutions buy USD from you (rate)
    #   - Selling exchange rate - used when financial institutions sell USD to you (rate_2)
    rate_2 = fields.Float(string='Buying Rate', digits=dp.get_precision('Currency Rate Precision'),
                          help='The buying rate of the currency to the currency of rate 1.')

    # Rate as it is get
    original_rate = fields.Float(string='Selling Rate in Costa Rica', digits=(6, 2),
                                 help='The selling exchange rate from CRC to USD as it is send from BCCR')

    # Rate as it is get
    original_rate_2 = fields.Float(string='Buying Rate in Costa Rica', digits=(6, 2),
                                   help='The buying exchange rate from CRC to USD as it is send from BCCR')

    @api.model
    def _cron_update(self, first_date=False, last_date=False):

        _logger.debug("=========================================================")
        _logger.debug("Executing exchange rate update from 1 CRC = X USD")

        exchange_source = self.env['ir.config_parameter'].sudo().get_param('exchange_source')
        if exchange_source == 'bccr':
            bccr_username = self.env['ir.config_parameter'].sudo().get_param('bccr_username')
            bccr_email = self.env['ir.config_parameter'].sudo().get_param('bccr_email')
            bccr_token = self.env['ir.config_parameter'].sudo().get_param('bccr_token')

            # Get current date to get exchange rate for today
            currentDate = datetime.datetime.now().date()
            # formato requerido por el BCCR dd/mm/yy
            today = currentDate.strftime('%d/%m/%Y')

            # Get XML Schema for BCCR webservice SOAP
            imp = Import('http://www.w3.org/2001/XMLSchema', location='http://www.w3.org/2001/XMLSchema.xsd')
            imp.filter.add('http://ws.sdde.bccr.fi.cr')

            # Web Service Connection using the XML schema from BCCRR
            client = Client('https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx?WSDL', doctor=ImportDoctor(imp))

            # The response is a string we need to convert it to XML to extract value

            response = client.service.ObtenerIndicadoresEconomicosXML(Indicador='318',
                                                                      FechaInicio=today,
                                                                      FechaFinal=today,
                                                                      Nombre=bccr_username,
                                                                      SubNiveles='N',
                                                                      CorreoElectronico=bccr_email,
                                                                      Token=bccr_token)
            xmlResponse = xml.etree.ElementTree.fromstring(response)
            rateNodes = xmlResponse.findall("./INGC011_CAT_INDICADORECONOMIC/NUM_VALOR")
            sellingRate = 0
            if len(rateNodes) > 0:
                sellingOriginalRate = float(rateNodes[0].text)
                # Odoo uses the value of 1 unit of the base currency divided between the exchage rate
                sellingRate = 1 / sellingOriginalRate

            # Get Buying exchange Rate from BCCR
            response = client.service.ObtenerIndicadoresEconomicosXML(Indicador='317',
                                                                      FechaInicio=today,
                                                                      FechaFinal=today,
                                                                      Nombre=bccr_username,
                                                                      SubNiveles='N',
                                                                      CorreoElectronico=bccr_email,
                                                                      Token=bccr_token)

            xmlResponse = xml.etree.ElementTree.fromstring(response)
            rateNodes = xmlResponse.findall("./INGC011_CAT_INDICADORECONOMIC/NUM_VALOR")
            buyingRate = 0
            if len(rateNodes) > 0:
                buyingOriginalRate = float(rateNodes[0].text)
                # Odoo uses the value of 1 unit of the base currency divided between the exchage rate
                buyingRate = 1 / buyingOriginalRate

            # Save the exchange rate in database
            today = currentDate.strftime('%Y-%m-%d')

            # GET THE CURRENCY ID
            currency_id = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)

            # Get the rate for this date to know it is already registered
            ratesIds = self.env['res.currency.rate'].search([('name', '=', today)], limit=1)

            if len(ratesIds) > 0:
                newRate = ratesIds.write({'rate': sellingRate,
                                          'original_rate': sellingOriginalRate,
                                          'rate_2': buyingRate,
                                          'original_rate_2': buyingOriginalRate,
                                          'currency_id': currency_id.id})
                _logger.debug({'name': today,
                               'rate': sellingRate,
                               'original_rate': sellingOriginalRate,
                               'rate_2': buyingRate,
                               'original_rate_2': buyingOriginalRate,
                               'currency_id': currency_id.id})
            else:
                newRate = self.create({'name': today,
                                       'rate': sellingRate,
                                       'original_rate': sellingOriginalRate,
                                       'rate_2': buyingRate,
                                       'original_rate_2': buyingOriginalRate,
                                       'currency_id': currency_id.id})
                _logger.debug({'name': today,
                               'rate': sellingRate,
                               'original_rate': sellingOriginalRate,
                               'rate_2': buyingRate,
                               'original_rate_2': buyingOriginalRate,
                               'currency_id': currency_id.id})

            _logger.debug(
                "=========================================================")

        if exchange_source == 'hacienda':
            _logger.info("=========================================================")
            _logger.info("Executing exchange rate update")

            try:
                url = 'https://api.hacienda.go.cr/indicadores/tc'
                response = requests.get(url, timeout=5, verify=False)

            except requests.exceptions.RequestException as e:
                _logger.info('RequestException %s' % e)
                return False

            if response.status_code in (200,):
                # Save the exchange rate in database
                today = datetime.datetime.now().strftime('%Y-%m-%d')
                data = response.json()

                vals = {}
                vals['original_rate'] = data['dolar']['venta']['valor']
                # Odoo utiliza un valor inverso, a cuantos dólares equivale 1 colón, por eso se divide 1 / tipo de cambio.
                vals['rate'] =  1 / vals['original_rate']
                vals['original_rate_2'] = data['dolar']['compra']['valor']
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
