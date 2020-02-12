# copyright  2018 Carlos Wong, Akurey S.A.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from zeep import Client
import datetime
import xml.etree.ElementTree
import logging

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

        bccr_username = self.env['ir.config_parameter'].sudo().get_param('bccr_username')
        bccr_email = self.env['ir.config_parameter'].sudo().get_param('bccr_email')
        bccr_token = self.env['ir.config_parameter'].sudo().get_param('bccr_token')

        # Get current date to get exchange rate for today
        if not first_date:
            initial_date = datetime.datetime.now().date().strftime('%d/%m/%Y')
            end_date = initial_date
        else:
            initial_date = first_date.strftime('%d/%m/%Y')
            end_date = last_date.strftime('%d/%m/%Y')

        # Web Service Connection using the XML schema from BCCRR
        client = Client('https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/wsindicadoreseconomicos.asmx?WSDL')

        response = client.service.ObtenerIndicadoresEconomicosXML(Indicador='318',
                                                                  FechaInicio=initial_date,
                                                                  FechaFinal=end_date,
                                                                  Nombre=bccr_username,
                                                                  SubNiveles='N',
                                                                  CorreoElectronico=bccr_email,
                                                                  Token=bccr_token)
        xmlResponse = xml.etree.ElementTree.fromstring(response)
        sellingRateNodes = xmlResponse.findall("./INGC011_CAT_INDICADORECONOMIC")

        # Get Buying exchange Rate from BCCR
        response = client.service.ObtenerIndicadoresEconomicosXML(Indicador='317',
                                                                  FechaInicio=initial_date,
                                                                  FechaFinal=end_date,
                                                                  Nombre=bccr_username,
                                                                  SubNiveles='N',
                                                                  CorreoElectronico=bccr_email,
                                                                  Token=bccr_token)

        xmlResponse = xml.etree.ElementTree.fromstring(response)
        buyingRateNodes = xmlResponse.findall("./INGC011_CAT_INDICADORECONOMIC")

        sellingRate = 0
        buyingRate = 0
        nodeIndex = 0
        if len(sellingRateNodes) > 0 and len(sellingRateNodes) == len(buyingRateNodes):
            while nodeIndex < len(sellingRateNodes):
                if sellingRateNodes[nodeIndex].find("DES_FECHA").text == buyingRateNodes[nodeIndex].find("DES_FECHA").text:
                    currentDateStr = datetime.datetime.strptime(sellingRateNodes[nodeIndex].find("DES_FECHA").text, "%Y-%m-%dT%H:%M:%S-06:00").strftime('%Y-%m-%d')

                    sellingOriginalRate = float(sellingRateNodes[nodeIndex].find("NUM_VALOR").text)
                    buyingOriginalRate = float(buyingRateNodes[nodeIndex].find("NUM_VALOR").text)

                    # Odoo uses the value of 1 unit of the base currency divided between the exchage rate
                    sellingRate = 1 / sellingOriginalRate
                    buyingRate = 1 / buyingOriginalRate

                    # GET THE CURRENCY ID
                    currency_id = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)

                    # Get the rate for this date to know it is already registered
                    ratesIds = self.env['res.currency.rate'].search([('name', '=', currentDateStr)], limit=1)

                    if len(ratesIds) > 0:
                        newRate = ratesIds.write({'rate': sellingRate,
                                                'original_rate': sellingOriginalRate,
                                                'rate_2': buyingRate,
                                                'original_rate_2': buyingOriginalRate,
                                                'currency_id': currency_id.id})
                    else:
                        newRate = self.create({'name': currentDateStr,
                                            'rate': sellingRate,
                                            'original_rate': sellingOriginalRate,
                                            'rate_2': buyingRate,
                                            'original_rate_2': buyingOriginalRate,
                                            'currency_id': currency_id.id})

                    _logger.debug({'name': currentDateStr,
                                'rate': sellingRate,
                                'original_rate': sellingOriginalRate,
                                'rate_2': buyingRate,
                                'original_rate_2': buyingOriginalRate,
                                'currency_id': currency_id.id})
                else:
                   _logger.debug("Error loading currency rates, dates for a buying and selling rate don't match") 
                nodeIndex += 1
        else:
            _logger.debug("Error loading currency rates, dates for buying and selling rates don't match")

        _logger.debug("=========================================================")