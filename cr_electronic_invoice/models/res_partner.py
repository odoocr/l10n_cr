# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class PartnerElectronic(models.Model):
    _inherit = "res.partner"

    commercial_name = fields.Char(string="Nombre comercial", required=False, )
    phone_code = fields.Char(string="Código de teléfono",
                             required=False, default="506")
    state_id = fields.Many2one(
        comodel_name="res.country.state", string="Provincia", required=False, )
    district_id = fields.Many2one(
        comodel_name="res.country.district", string="Distrito", required=False, )
    county_id = fields.Many2one(
        comodel_name="res.country.county", string="Cantón", required=False, )
    neighborhood_id = fields.Many2one(
        comodel_name="res.country.neighborhood", string="Barrios", required=False, )
    identification_id = fields.Many2one(comodel_name="identification.type", string="Tipo de identificacion",
                                        required=False, )
    payment_methods_id = fields.Many2one(
        comodel_name="payment.methods", string="Métodos de Pago", required=False, )

    has_exoneration = fields.Boolean( string="Posee exoneración", required=False )
    type_exoneration = fields.Many2one(
        comodel_name="aut.ex", string="Tipo Autorizacion", required=False, )
    exoneration_number = fields.Char(
        string="Número de exoneración", required=False, )
    institution_name = fields.Char(string="Institucion Emisora", required=False, )
    date_issue = fields.Date( string="Fecha de Emisión", required=False, )
    date_expiration = fields.Date( string="Fecha de Vencimiento", required=False, )

    @api.onchange('phone')
    def _onchange_phone(self):
        if self.phone:
            self.phone = re.sub(r"[^0-9]+", "", self.phone)
            if not self.phone.isdigit():
                alert = {
                    'title': 'Atención',
                    'message': 'Favor no introducir letras, espacios ni guiones en los números telefónicos.'
                }
                return {'value': {'phone': ''}, 'warning': alert}

    @api.onchange('mobile')
    def _onchange_mobile(self):
        if self.mobile:
            self.mobile = re.sub(r"[^0-9]+", "", self.mobile)
            if not self.mobile.isdigit():
                alert = {
                    'title': 'Atención',
                    'message': 'Favor no introducir letras, espacios ni guiones en los números telefónicos.'
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
