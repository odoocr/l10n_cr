# -*- coding: utf-8 -*-

import logging
import phonenumbers

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

from . import api_facturae
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
=======
>>>>>>> 13.0

_logger = logging.getLogger(__name__)

_TIPOS_CONFIRMACION = (
    # Provides listing of types of comprobante confirmations
    ('CCE_sequence_id', 'account.invoice.supplier.accept.',
     'Supplier invoice acceptance sequence'),
    ('CPCE_sequence_id', 'account.invoice.supplier.partial.',
     'Supplier invoice partial acceptance sequence'),
    ('RCE_sequence_id', 'account.invoice.supplier.reject.',
     'Supplier invoice rejection sequence'),
    ('FEC_sequence_id', 'account.invoice.supplier.reject.',
     'Supplier electronic purchase invoice sequence'),
)

<<<<<<< HEAD
=======

_logger = logging.getLogger(__name__)
>>>>>>> Updated

_TIPOS_CONFIRMACION = (
    # Provides listing of types of comprobante confirmations
    ('CCE_sequence_id', 'account.invoice.supplier.accept.',
     'Supplier invoice acceptance sequence'),
    ('CPCE_sequence_id', 'account.invoice.supplier.partial.',
     'Supplier invoice partial acceptance sequence'),
    ('RCE_sequence_id', 'account.invoice.supplier.reject.',
     'Supplier invoice rejection sequence'),
    ('FEC_sequence_id', 'account.invoice.supplier.reject.',
     'Supplier electronic purchase invoice sequence'),
)

=======
>>>>>>> 13.0

class CompanyElectronic(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'mail.thread', ]

    commercial_name = fields.Char(string="Commercial Name", required=False, )
    activity_id = fields.Many2one("economic.activity", string="Default economic activity", required=False, context={'active_test': False})
    signature = fields.Binary(string="Llave Criptográfica", )
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
<<<<<<< refs/remotes/upstream/13.0
=======
>>>>>>> Updated
=======
>>>>>>> 13.0
    identification_id = fields.Many2one("identification.type", string="Id Type", required=False)
    frm_ws_identificador = fields.Char(string="Electronic invoice user", required=False)
    frm_ws_password = fields.Char(string="Electronic invoice password", required=False)

    frm_ws_ambiente = fields.Selection(selection=[('disabled', 'Deshabilitado'), 
                                                  ('api-stag', 'Pruebas'),
                                                  ('api-prod', 'Producción')],
                                    string="Environment",
                                    required=True, 
                                    default='disabled',
                                    help='Es el ambiente en al cual se le está actualizando el certificado. Para el ambiente '
                                    'de calidad (stag), para el ambiente de producción (prod). Requerido.')

    frm_pin = fields.Char(string="Pin", 
                          required=False,
                          help='Es el pin correspondiente al certificado. Requerido')

    sucursal_MR = fields.Integer(string="Sucursal para secuencias de MRs", 
                                 required=False,
                                 default="1")

    terminal_MR = fields.Integer(string="Terminal para secuencias de MRs", 
                                 required=False,
                                 default="1")
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
=======
    identification_id = fields.Many2one(comodel_name="identification.type", string="Tipo de identificacion",
                                        required=False, )
    district_id = fields.Many2one(comodel_name="res.country.district", string="Distrito", required=False, )
    county_id = fields.Many2one(comodel_name="res.country.county", string="Cantón", required=False, )
    neighborhood_id = fields.Many2one(comodel_name="res.country.neighborhood", string="Barrios", required=False, )
    frm_ws_identificador = fields.Char(string="Usuario de Factura Electrónica", required=False, )     
    frm_ws_password = fields.Char(string="Password de Factura Electrónica", required=False, )
    
    frm_ws_ambiente = fields.Selection(
        selection=[('disabled', 'Deshabilitado'), ('api-stag', 'Pruebas'), ('api-prod', 'Producción'), ], string="Ambiente",
        required=True, default='disabled',
        help='Es el ambiente en al cual se le está actualizando el certificado. Para el ambiente de calidad (stag), '
             'para el ambiente de producción (prod). Requerido.')

    version_hacienda = fields.Selection(
        selection=[('4.2', 'Utilizar XMLs version 4.2'), ('4.3', 'Utilizar XMLs version 4.3')],
        string="Versión de Hacienda a utilizar",
        required=True, default='4.2',
        help='Indica si se quiere utilizar la versión 4.2 o 4.3 de Hacienda')

    frm_pin = fields.Char(string="Pin", required=False, help='Es el pin correspondiente al certificado. Requerido')

    sucursal_MR = fields.Integer(string="Sucursal para secuencias de MRs", required=False, default="1")

    terminal_MR = fields.Integer(string="Terminal para secuencias de MRs", required=False, default="1")

    #CCE_sequence_id = fields.Many2one('ir.sequence',
    #                                  string='Secuencia de Confirmación de Aceptación Comprobante Electrónico',
    #                                  readonly=False, copy=False)

    #CPCE_sequence_id = fields.Many2one('ir.sequence',
    #                                   string='Secuencia de Confirmación de Aceptación Parcial Comprobante Electrónico',
    #                                   readonly=False, copy=False)

    #RCE_sequence_id = fields.Many2one('ir.sequence', string='Secuencia de Rechazo Comprobante Electrónico',
    #                                  readonly=False, copy=False)
>>>>>>> Many Fixes
=======
>>>>>>> Updated
=======
>>>>>>> 13.0

    CCE_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia Aceptación',
        help='Secuencia de confirmacion de aceptación de comprobante electrónico. Dejar en blanco '
        'y el sistema automaticamente se lo creará.',
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
<<<<<<< refs/remotes/upstream/13.0
        readonly=False, copy=False,
    )
=======
        readonly=False,
        copy=False,
        )
>>>>>>> Many Fixes
=======
        readonly=False, copy=False,
    )
>>>>>>> Updated
=======
        readonly=False, copy=False,
    )
>>>>>>> 13.0

    CPCE_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia Parcial',
        help='Secuencia de confirmación de aceptación parcial de comprobante electrónico. Dejar '
        'en blanco y el sistema automáticamente se lo creará.',
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
<<<<<<< refs/remotes/upstream/13.0
        readonly=False, copy=False,
    )
=======
        readonly=False, copy=False)

>>>>>>> Many Fixes
=======
        readonly=False, copy=False,
    )
>>>>>>> Updated
=======
        readonly=False, copy=False,
    )
>>>>>>> 13.0
    RCE_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia Rechazo',
        help='Secuencia de confirmación de rechazo de comprobante electrónico. Dejar '
        'en blanco y el sistema automáticamente se lo creará.',
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
<<<<<<< refs/remotes/upstream/13.0
=======
>>>>>>> Updated
=======
>>>>>>> 13.0
        readonly=False, copy=False,
    )
    FEC_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia de Facturas Electrónicas de Compra',
        readonly=False, copy=False,
    )

    @api.onchange('mobile')
    def _onchange_mobile(self):
        if self.mobile:
            mobile = phonenumbers.parse(self.mobile, self.country_id.code)
            valid = phonenumbers.is_valid_number(mobile)
            if not valid:
                alert = {
                    'title': 'Atención',
                    'message': 'Número de teléfono inválido'
                }
                return {'value': {'mobile': ''}, 'warning': alert}

    @api.onchange('phone')
    def _onchange_phone(self):
        if self.phone:
            phone = phonenumbers.parse(self.phone, self.country_id.code)
            valid = phonenumbers.is_valid_number(phone)
            if not valid:
                alert = {
                    'title': 'Atención',
                    'message': _('Número de teléfono inválido')
                }
                return {'value': {'phone': ''}, 'warning': alert}
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
=======
        readonly=False, copy=False)
>>>>>>> Many Fixes
=======
>>>>>>> Updated
=======
>>>>>>> 13.0

    @api.model
    def create(self, vals):
        """ Try to automatically add the Comprobante Confirmation sequence to the company.
            It will attempt to create and assign before storing. The sequence that is
            created will be coded with the following syntax:
                account.invoice.supplier.<tipo>.<company_name>
            where tipo is: accept, partial or reject, and company_name is either the first word
            of the name or commercial name.
        """
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
<<<<<<< refs/remotes/upstream/13.0
=======
>>>>>>> Updated
=======
>>>>>>> 13.0
        new_comp_id = super(CompanyElectronic, self).create(vals)
        #new_comp = self.browse(new_comp_id)
        new_comp_id.try_create_configuration_sequences()
        return new_comp_id #new_comp.id

    def try_create_configuration_sequences(self):
        """ Try to automatically add the Comprobante Confirmation sequence to the company.
            It will first check if sequence already exists before attempt to create. The s
            equence is coded with the following syntax:
                account.invoice.supplier.<tipo>.<company_name>
            where tipo is: accept, partial or reject, and company_name is either the first word
            of the name or commercial name.
        """
        company_subname = self.commercial_name
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
        if not company_subname:
            company_subname = getattr(self, 'name')
=======
        new_comp = super(CompanyElectronic, self).create(vals)
        company_subname = vals.get('commercial_name')
        if not company_subname:
            company_subname = vals.get('name')
>>>>>>> Many Fixes
=======
        if not company_subname:
            company_subname = getattr(self, 'name')
>>>>>>> Updated
=======
        if not company_subname:
            company_subname = getattr(self, 'name')
>>>>>>> 13.0
        company_subname = company_subname.split(' ')[0].lower()
        ir_sequence = self.env['ir.sequence']
        to_write = {}
        for field, seq_code, seq_name in _TIPOS_CONFIRMACION:
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
<<<<<<< refs/remotes/upstream/13.0
            if not getattr(self, field, None):
                seq_code += company_subname
                seq = self.env.ref(seq_code, raise_if_not_found=False) or ir_sequence.create({
=======
            if field not in vals or not vals.get(field):
                seq_code += company_subname
                seq = ir_sequence.create({
>>>>>>> Many Fixes
=======
            if not getattr(self, field, None):
                seq_code += company_subname
                seq = self.env.ref(seq_code, raise_if_not_found=False) or ir_sequence.create({
>>>>>>> Updated
=======
            if not getattr(self, field, None):
                seq_code += company_subname
                seq = self.env.ref(seq_code, raise_if_not_found=False) or ir_sequence.create({
>>>>>>> 13.0
                    'name': seq_name,
                    'code': seq_code,
                    'implementation': 'standard',
                    'padding': 10,
                    'use_date_range': False,
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
<<<<<<< refs/remotes/upstream/13.0
                    'company_id': getattr(self, 'id'),
                })
                to_write[field] = seq.id

        if to_write:
            self.write(to_write)

    def test_get_token(self):
        token_m_h = api_facturae.get_token_hacienda(
            self.env.user, self.frm_ws_ambiente)
        if token_m_h:
           _logger.info('E-INV CR - I got the token')
        return 

    def action_get_economic_activities(self):
        if self.vat:
            json_response = api_facturae.get_economic_activities(self)

            self.env.cr.execute('update economic_activity set active=False')

            self.message_post(subject='Actividades Económicas',
                            body='Aviso!.\n Cargando actividades económicas desde Hacienda')

            if json_response["status"] == 200:
                activities = json_response["activities"]
                activities_codes = list()
                for activity in activities:
                    if activity["estado"] == "A":
                        activities_codes.append(activity["codigo"])

                economic_activities = self.env['economic.activity'].with_context(active_test=False).search([('code', 'in', activities_codes)])

                for activity in economic_activities:
                    activity.active = True

                self.name = json_response["name"]
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
=======
                    'company_id': new_comp.id,
=======
                    'company_id': getattr(self, 'id'),
>>>>>>> Updated
=======
                    'company_id': getattr(self, 'id'),
>>>>>>> 13.0
                })
                to_write[field] = seq.id

        if to_write:
<<<<<<< HEAD
<<<<<<< refs/remotes/upstream/13.0
            new_comp.write(to_write)
        return new_comp
>>>>>>> Many Fixes
=======
=======
>>>>>>> 13.0
            self.write(to_write)

    def test_get_token(self):
        token_m_h = api_facturae.get_token_hacienda(
            self.env.user, self.frm_ws_ambiente)
        if token_m_h:
           _logger.info('E-INV CR - I got the token')
        return 

    def action_get_economic_activities(self):
        if self.vat:
            json_response = api_facturae.get_economic_activities(self)

            self.env.cr.execute('update economic_activity set active=False')

            self.message_post(subject='Actividades Económicas',
                            body='Aviso!.\n Cargando actividades económicas desde Hacienda')

            if json_response["status"] == 200:
                activities = json_response["activities"]
                activities_codes = list()
                for activity in activities:
                    if activity["estado"] == "A":
                        activities_codes.append(activity["codigo"])

                economic_activities = self.env['economic.activity'].with_context(active_test=False).search([('code', 'in', activities_codes)])

                for activity in economic_activities:
                    activity.active = True

                self.name = json_response["name"]
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
<<<<<<< HEAD
>>>>>>> Updated
=======
>>>>>>> 13.0
