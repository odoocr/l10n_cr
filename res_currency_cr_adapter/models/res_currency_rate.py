# copyright  2018 Carlos Wong, Akurey S.A.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from zeep import Client
from datetime import timedelta, datetime
import xml.etree.ElementTree
import logging
import requests
from lxml import etree

_logger = logging.getLogger(__name__)


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    rate = fields.Float(digits='Currency Rate Precision')

    # === Deprecated === #
    # Now Odoo has the company_rate and inverse_company_rate
    original_rate = fields.Float(
        string='Selling Rate in Costa Rica',
        digits=0,
        group_operator="avg",
        help='The selling exchange rate from CRC to USD as it is send from BCCR')

    # ==============================================================================================
    #                                          Currency Rate - Buy
    # ==============================================================================================

    rate_2 = fields.Float(
        digits='Currency Rate Precision',
        group_operator="avg",
        help='The buying rate of the currency to the currency of rate 1.')

    original_rate_2 = fields.Float(
        digits=0,
        compute="_compute_original_rate_2",
        inverse="_inverse_original_rate_2",
        group_operator="avg",
        help='The buying exchange rate from CRC to USD as it is send from BCCR')

    inverse_original_rate_2 = fields.Float(
        digits=0,
        string='Technical Rate - Buy',
        compute="_compute_inverse_original_rate_2",
        inverse="_inverse_inverse_original_rate_2",
        group_operator="avg",
        help="The rate of the currency to the currency of rate 1 ",
    )

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_latest_rate_2(self):
        # Make sure 'name' is defined when creating a new rate.
        if not self.name:
            raise UserError(_("The date for the current rate is empty.\nPlease set it."))
        return self.currency_id.rate_ids.sudo().filtered(lambda x: (
            x.rate_2
            and x.company_id == (self.company_id or self.env.company)
            and x.name < (self.name or fields.Date.today())
        )).sorted('name')[-1:]

    def _get_last_rates_for_companies_2(self, companies):
        return {
            company: company.currency_id.rate_ids.sudo().filtered(lambda x: (
                x.rate_2
                and x.company_id == company or not x.company_id
            )).sorted('name')[-1:].rate_2 or 1
            for company in companies
        }

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('rate_2', 'name', 'currency_id', 'company_id', 'currency_id.rate_ids.rate_2')
    @api.depends_context('company')
    def _compute_original_rate_2(self):
        last_rate = self.env['res.currency.rate']._get_last_rates_for_companies_2(self.company_id | self.env.company)
        for currency_rate in self:
            company = currency_rate.company_id or self.env.company
            currency_rate.original_rate_2 = (currency_rate.rate_2 or self._get_latest_rate_2().rate_2 or 1.0) / last_rate[company]

    @api.depends('original_rate_2')
    def _compute_inverse_original_rate_2(self):
        for currency_rate in self:
            currency_rate.inverse_original_rate_2 = 1.0 / currency_rate.original_rate_2

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('original_rate_2')
    def _inverse_original_rate_2(self):
        last_rate = self.env['res.currency.rate']._get_last_rates_for_companies_2(self.company_id | self.env.company)
        for currency_rate in self:
            company = currency_rate.company_id or self.env.company
            currency_rate.rate_2 = currency_rate.original_rate_2 * last_rate[company]

    @api.onchange('inverse_original_rate_2')
    def _inverse_inverse_original_rate_2(self):
        for currency_rate in self:
            currency_rate.original_rate_2 = 1.0 / currency_rate.inverse_original_rate_2

    @api.onchange('original_rate_2')
    def _onchange_rate_2_warning(self):
        latest_rate = self._get_latest_rate_2()
        if latest_rate:
            diff = (latest_rate.rate_2 - self.rate_2) / latest_rate.rate_2
            if abs(diff) > 0.2:
                return {
                    'warning': {
                        'title': _("Warning for %s", self.currency_id.name),
                        'message': _(
                            "The new rate is quite far from the previous rate.\n"
                            "Incorrect currency rates may cause critical problems, make sure the rate is correct !"
                        )
                    }
                }

    # -------------------------------------------------------------------------
    # CRON
    # -------------------------------------------------------------------------

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
                        companies = self.env['res.company'].search([])
                        for company in companies:
                            _logger.error(company.id)
                            rates_ids = self.env['res.currency.rate'].search([('name', '=', current_date_str),
                                                                              ('company_id', '=', company.id)],
                                                                             limit=1)

                            if len(rates_ids) > 0:
                                rates_ids.sudo().write({
                                    'rate': selling_rate,
                                    'inverse_company_rate': selling_original_rate,
                                    'original_rate': selling_original_rate,
                                    'rate_2': buying_rate,
                                    'original_rate_2': buying_original_rate,
                                    'currency_id': currency_id.id,
                                    'company_id': company.id
                                    })
                            else:
                                self.sudo().create(
                                    {'name': current_date_str,
                                    'rate': selling_rate,
                                    'inverse_company_rate': selling_original_rate,
                                    'original_rate': selling_original_rate,
                                    'rate_2': buying_rate,
                                    'original_rate_2': buying_original_rate,
                                    'currency_id': currency_id.id,
                                    'company_id': company.id})

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

                        companies = self.env['res.company'].search([])
                        for company in companies:
                            _logger.error(company.id)
                            rate_id = self.env['res.currency.rate'].search([('name', '=', today.date()),
                                                                            ('company_id', '=', company.id)], limit=1)
                            vals['company_id'] = company.id
                            if rate_id:
                                rate_id.sudo().write(vals)
                            else:
                                vals['name'] = today.date()
                                self.sudo().create(vals)
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

                    companies = self.env['res.company'].search([])
                    for company in companies:
                        _logger.error(company.id)
                        rate_id = self.env['res.currency.rate'].search([('name', '=', today),
                                                                        ('company_id', '=', company.id)], limit=1)
                        vals['company_id'] = company.id
                        if rate_id:
                            rate_id.sudo().write(vals)
                        else:
                            vals['name'] = today
                            self.sudo().create(vals)

                _logger.info(vals)

        _logger.info("=========================================================")

    def _create_the_latest_exchange_rate_to_date(self, currency, date=None):
        name = date or datetime.now()
        companies = self.env['res.company'].search([])
        for company in companies:
            currency_rate_obj = self.env['res.currency.rate'].search([
                ('company_id', '=', company.id),
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
                'currency_id': currency_rate_obj.currency_id.id,
                'company_id': company.id,
            })

    # -------------------------------------------------------------------------
    # TOOLING
    # -------------------------------------------------------------------------

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super()._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type in ('tree'):
            names = {
                'company_currency_name': (self.env['res.company'].browse(self._context.get('company_id')) or self.env.company).currency_id.name,
                'rate_currency_name': self.env['res.currency'].browse(self._context.get('active_id')).name or 'Unit',
            }
            doc = etree.XML(result['arch'])
            for field in [['original_rate_2', _('%(company_currency_name)s per %(rate_currency_name)s - Buy', **names)],
                          ['inverse_original_rate_2', _('%(rate_currency_name)s per %(company_currency_name)s - Buy', **names)],
                          ]:
                node = doc.xpath("//tree//field[@name='%s']" % field[0])
                if node:
                    node[0].set('string', field[1])
            result['arch'] = etree.tostring(doc, encoding='unicode')
        return result
