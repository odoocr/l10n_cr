# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api
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


class CompanyElectronic(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'mail.thread', ]

    commercial_name = fields.Char(string="Nombre comercial", required=False, )
    # phone_code = fields.Char(string="Código de teléfono", required=False, size=3, default="506")

    activity_id = fields.Many2one(comodel_name="economic_activity", string="Actividad Económica",
                                  required=False, )

    phone_code = fields.Char(string="Código de teléfono", required=False, size=3, default="506",
                             help="Sin espacios ni guiones")
    signature = fields.Binary(string="Llave Criptográfica", )
    identification_id = fields.Many2one(
        comodel_name="identification.type", string="Tipo de identificacion", required=False)
    district_id = fields.Many2one(comodel_name="res.country.district", string="Distrito",
                                  required=False)
    county_id = fields.Many2one(comodel_name="res.country.county", string="Cantón",
                                required=False)
    neighborhood_id = fields.Many2one(comodel_name="res.country.neighborhood", string="Barrios",
                                      required=False, )
    frm_ws_identificador = fields.Char(
        string="Usuario de Factura Electrónica", required=False)
    frm_ws_password = fields.Char(
        string="Password de Factura Electrónica", required=False)

    frm_ws_ambiente = fields.Selection(
        selection=[('disabled', 'Deshabilitado'), ('api-stag', 'Pruebas'),
                   ('api-prod', 'Producción')],
        string="Ambiente",
        required=True, default='disabled',
        help='Es el ambiente en al cual se le está actualizando el certificado. Para el ambiente '
             'de calidad (stag), para el ambiente de producción (prod). Requerido.')

    version_hacienda = fields.Selection(
        selection=[('4.2', 'Utilizar XMLs version 4.2'),
                   ('4.3', 'Utilizar XMLs version 4.3')],
        string="Versión de Hacienda a utilizar",
        required=True, default='4.2',
        help='Indica si se quiere utilizar la versión 4.2 o 4.3 de Hacienda')

    frm_pin = fields.Char(string="Pin", required=False,
                          help='Es el pin correspondiente al certificado. Requerido')

    sucursal_MR = fields.Integer(string="Sucursal para secuencias de MRs", required=False,
                                 default="1")
    terminal_MR = fields.Integer(string="Terminal para secuencias de MRs", required=False,
                                 default="1")

    CCE_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia Aceptación',
        help='Secuencia de confirmacion de aceptación de comprobante electrónico. Dejar en blanco '
        'y el sistema automaticamente se lo creará.',
        readonly=False, copy=False,
    )
    CPCE_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia Parcial',
        help='Secuencia de confirmación de aceptación parcial de comprobante electrónico. Dejar '
        'en blanco y el sistema automáticamente se lo creará.',
        readonly=False, copy=False,
    )
    RCE_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia Rechazo',
        help='Secuencia de confirmación de rechazo de comprobante electrónico. Dejar '
        'en blanco y el sistema automáticamente se lo creará.',
        readonly=False, copy=False,
    )
    FEC_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia de Facturas Electrónicas de Compra',
        readonly=False, copy=False,
    )

    @api.model
    def create(self, vals):
        """ Try to automatically add the Comprobante Confirmation sequence to the company.
            It will attempt to create and assign before storing. The sequence that is
            created will be coded with the following syntax:
                account.invoice.supplier.<tipo>.<company_name>
            where tipo is: accept, partial or reject, and company_name is either the first word
            of the name or commercial name.
        """
        new_comp_id = super(CompanyElectronic, self).create(vals)
        new_comp = self.browse(new_comp_id)
        new_comp.try_create_configuration_sequences()
        return new_comp.id

    def try_create_confirmation_sequeces(self):
        """ Try to automatically add the Comprobante Confirmation sequence to the company.
            It will first check if sequence already exists before attempt to create. The s
            equence is coded with the following syntax:
                account.invoice.supplier.<tipo>.<company_name>
            where tipo is: accept, partial or reject, and company_name is either the first word
            of the name or commercial name.
        """
        company_subname = self.commercial_name
        if not company_subname:
            company_subname = getattr(self, 'name')
        company_subname = company_subname.split(' ')[0].lower()
        ir_sequence = self.env['ir.sequence']
        to_write = {}
        for field, seq_code, seq_name in _TIPOS_CONFIRMACION:
            if not getattr(self, field, None):
                seq_code += company_subname
                seq = self.env.ref(seq_code, raise_if_not_found=False) or ir_sequence.create({
                    'name': seq_name,
                    'code': seq_code,
                    'implementation': 'standard',
                    'padding': 10,
                    'use_date_range': False,
                    'company_id': getattr(self, 'id'),
                })
                to_write[field] = seq.id

        if to_write:
            self.write(to_write)
