# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import phonenumbers
import logging
from datetime import datetime, timedelta, date
from . import api_facturae

_logger = logging.getLogger(__name__)


class PartnerElectronic(models.Model):
    _inherit = "res.partner"

    commercial_name = fields.Char(string="Commercial Name", required=False, )
    state_id = fields.Many2one("res.country.state", string="Province", required=False, )
    district_id = fields.Many2one("res.country.district", string="District", required=False, )
    county_id = fields.Many2one("res.country.county", string="Canton", required=False, )
    neighborhood_id = fields.Many2one("res.country.neighborhood", string="Neighborhood", required=False, )
    identification_id = fields.Many2one("identification.type", string="Id Type",required=False, )
    payment_methods_id = fields.Many2one("payment.methods", string="Payment Method", required=False, )
    has_exoneration = fields.Boolean(string="Has Exoneration?", required=False)
    type_exoneration = fields.Many2one("aut.ex", string="Authorization Type", required=False, )
    exoneration_number = fields.Char(string="Exoneration Number", required=False, )
    institution_name = fields.Char(string="Exoneration Issuer", required=False, )
    date_issue = fields.Date(string="Issue Date", required=False, )
    date_expiration = fields.Date(string="Expiration Date", required=False, )
    date_notification = fields.Date(string="Last notification date", required=False, )
    activity_id = fields.Many2one("economic.activity", string="Default Economic Activity", required=False, context={'active_test': False} )
    economic_activities_ids = fields.Many2many('economic.activity', string=u'Economic Activities', context={'active_test': False},relation='economic_activity_res_partner_rel',
                                       column1='res_partner_id',
                                       column2='economic_activity_id',)
    export = fields.Boolean(string="It's export", default=False)

    @api.onchange('phone')
    def _onchange_phone(self):
        if self.phone:
            phone = phonenumbers.parse(self.phone, self.country_id and self.country_id.code or 'CR')
            valid = phonenumbers.is_valid_number(phone)
            if not valid:
                alert = {
                    'title': 'Atención',
                    'message': _('Número de teléfono inválido')
                }
                return {'value': {'phone': ''}, 'warning': alert}

    @api.onchange('mobile')
    def _onchange_mobile(self):
        if self.mobile:
            mobile = phonenumbers.parse(self.mobile, self.country_id and self.country_id.code or 'CR')
            valid = phonenumbers.is_valid_number(mobile)
            if not valid:
                alert = {
                    'title': 'Atención',
                    'message': 'Número de teléfono inválido'
                }
                return {'value': {'mobile': ''}, 'warning': alert}

    @api.onchange('email')
    def _onchange_email(self):
        if self.email:
            if not re.match(r'^(\s?[^\s,]+@[^\s,]+\.[^\s,]+\s?,)*(\s?[^\s,]+@[^\s,]+\.[^\s,]+)$', self.email.lower()):
                vals = {'email': False}
                alerta = {
                    'title': 'Atención',
                    'message': 'El correo electrónico no cumple con una estructura válida. ' + str(self.email)
                }
                return {'value': vals, 'warning': alerta}

    @api.onchange('vat')
    def _onchange_vat(self):
        if self.identification_id and self.vat:
            if self.identification_id.code == '05':
                if len(self.vat) == 0 or len(self.vat) > 20:
                    raise UserError(
                        'La identificación debe tener menos de 20 carateres.')
            else:
                # Remove leters, dashes, dots or any other special character.
                self.vat = re.sub(r"[^0-9]+", "", self.vat)
                if self.identification_id.code == '01':
                    if self.vat.isdigit() and len(self.vat) != 9:
                        raise UserError(
                            'La identificación tipo Cédula física debe de contener 9 dígitos, sin cero al inicio y sin guiones.')
                elif self.identification_id.code == '02':
                    if self.vat.isdigit() and len(self.vat) != 10:
                        raise UserError(
                            'La identificación tipo Cédula jurídica debe contener 10 dígitos, sin cero al inicio y sin guiones.')
                elif self.identification_id.code == '03' and self.vat.isdigit():
                    if self.vat.isdigit() and len(self.vat) < 11 or len(self.vat) > 12:
                        raise UserError(
                            'La identificación tipo DIMEX debe contener 11 o 12 dígitos, sin ceros al inicio y sin guiones.')
                elif self.identification_id.code == '04' and self.vat.isdigit():
                    if self.vat.isdigit() and len(self.vat) != 9:
                        raise UserError(
                            'La identificación tipo NITE debe contener 10 dígitos, sin ceros al inicio y sin guiones.')

    @api.multi
    def action_get_economic_activities(self):
        if self.vat:
            json_response = api_facturae.get_economic_activities(self)
            _logger.debug('E-INV CR  - Economic Activities: %s', json_response)
            if json_response["status"] == 200:
                activities = json_response["activities"]
                activities_codes = list()
                for activity in activities:
                    if activity["estado"] == "A":
                        activities_codes.append(activity["codigo"])
                economic_activities = self.env['economic.activity'].with_context(active_test=False).search([('code', 'in', activities_codes)])

                self.economic_activities_ids = economic_activities
                self.name = json_response["name"]

                if len(activities_codes) >= 1:
                    self.activity_id = economic_activities[0]
            else:
                alert = {
                    'title': json_response["status"],
                    'message': json_response["text"]
                }
                return {'value': {'vat': ''}, 'warning': alert}
        else:
            alert = {
                'title': 'Atención',
                'message': _('Company VAT is invalid')
            }
            return {'value': {'vat': ''}, 'warning': alert}

    @api.multi
    def check_exonerations(self):
        clients = self.env["res.partner"].search([("has_exoneration", "=", True), ("date_expiration", "<", datetime.today())])
        for client in clients:
            if client.date_notification == False or (client.date_notification + timedelta(days=8)) < date.today():
                email_template = client.env.ref("cr_electronic_invoice.email_template_client_exoneration_expired")
                if email_template:
                    email_template.send_mail(client.id)
                    client.date_notification = date.today()
