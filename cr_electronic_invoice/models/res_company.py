# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

_TIPOS_CONFIRMACION = (
    # Provides listing of types of comprobante confirmations
    ('CCE_sequence_id', 'cce'),
    ('CPCE_sequence_id', 'cpe'),
    ('RCE_sequence_id', 'rce'),
)

class CompanyElectronic(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'mail.thread', ]

    commercial_name = fields.Char(string="Nombre comercial", required=False, )
    # phone_code = fields.Char(string="Código de teléfono", required=False, size=3, default="506")
    phone_code = fields.Char(string="Código de teléfono", required=False, size=3, default="506", help="Sin espacios ni guiones")
    signature = fields.Binary(string="Llave Criptográfica", )
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
    CCE_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia de Confirmación de Aceptación Comprobante Electrónico',
        readonly=False,
        copy=False,
        )
    CPCE_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia de Confirmación de Aceptación Parcial Comprobante Electrónico',
        readonly=False, copy=False)
    RCE_sequence_id = fields.Many2one(
        'ir.sequence', string='Secuencia de Rechazo Comprobante Electrónico',
        readonly=False, copy=False)

    @api.model
    def create(self, vals):
        """ Try to automatically add the Comprobante Confirmation sequence to the company. It will
            first try to search if an existing sequence exists with the same name of the company.
            If not it will attempt to create and assign before storing. The sequence that is
            created will be name with the following syntax: <CC type>-<company_name>, where CC-type
            is either: cce, cpe, rce
        """
        new_comp = super(CompanyElectronic, self).create(vals)
        company_subname = vals.get('name')
        company_subname = company_subname.split(' ')[0].lower()
        IrSequence = self.env['ir.sequence']
        to_write = {}
        _logger.info('Called create in CompanyElectronic')
        for field, tipo in _TIPOS_CONFIRMACION:
            if field not in vals:
                seq_name = '{}-{}'.format(tipo, company_subname)
                seq = IrSequence.search(('name', '=', seq_name), limit=1)
                if not seq:
                    seq = IrSequence.create({
                        'name': seq_name,
                        'implementation': 'statndard',
                        'padding': 10,
                        'use_date_range': False,
                        'company_id': new_comp.id,
                    })
                to_write[field] = seq.id

        if to_write:
            new_comp.write(to_write)
        return new_comp
