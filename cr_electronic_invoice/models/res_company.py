from odoo import models, fields, api


class CompanyElectronic(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'mail.thread', ]

    commercial_name = fields.Char(string="Nombre comercial", required=False, )
    # phone_code = fields.Char(string="Código de teléfono", required=False, size=3, default="506")
    phone_code = fields.Char(string="Código de teléfono", required=False, size=3,
    default = "506", help="Sin espacios ni guiones")
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
        help='Es el ambiente en al cual se le está actualizando el certificado. Para el ambiente de calidad (stag) c3RhZw==, '
             'para el ambiente de producción (prod) '
             'cHJvZA==. Requerido.')
    frm_pin = fields.Char(string="Pin", required=False, help='Es el pin correspondiente al certificado. Requerido')
    frm_callback_url = fields.Char(string="Callback Url", required=False, default="https://url_callback/repuesta.php?",
                                   help='Es la URL en a la cual se reenviarán las respuestas de Hacienda.')

    activated = fields.Boolean('Activado')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('started', 'Started'),
        ('progress', 'In progress'),
        ('finished', 'Done'),
    ], default='draft')

    frm_apicr_username = fields.Char(string="Usuario de Api", required=False, )
    frm_apicr_password = fields.Char(string="Password de Api", required=False, )
    frm_apicr_signaturecode = fields.Char(string="Codigo para Firmar API", required=False, )

    @api.onchange('email')
    def _onchange_email(self):
        pass