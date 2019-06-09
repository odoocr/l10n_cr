# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


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

    frm_ws_api = fields.Selection(
        selection=[('api-interna', 'API Interna'), ('api-hacienda', 'API Hacienda')],
        string="Procesar Utilizando",
        required=True, default='api-interna',
        help='Es la forma en la cual se procesarán las peticiones hacia el Ministerio de Hacienda. API Interna: signifca'
             ' que las peticiones se realizarán utilizando el API definida en PYTHON, excepto el firmado. API Hacienda:'
             'significa que todas las peticiones se procesarán con el API de CRLIBRE')

    frm_pin = fields.Char(string="Pin", required=False, help='Es el pin correspondiente al certificado. Requerido')
    frm_callback_url = fields.Char(string="Callback Url", required=False, default="https://url_callback/repuesta.php?",
                                   help='Es la URL en a la cual se reenviarán las respuestas de Hacienda.')
