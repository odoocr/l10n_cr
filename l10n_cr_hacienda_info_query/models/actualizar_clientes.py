from odoo import models, fields, api
from datetime import datetime
import json
import requests


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = ['res.company']

    ultima_respuesta = fields.Text(string="Latest API response",
                                   help="Last API Response, this allows debugging errors if they exist")
    url_base = fields.Char(string="URL Base",
                           required=False,
                           help="URL Base of the END POINT",
                           default="https://api.hacienda.go.cr/fe/ae?")


class ResPartner(models.Model):

    _name = 'res.partner'
    _inherit = "res.partner"

    def limpiar_cedula(self, vat):
        if vat:
            return ''.join(i for i in vat if i.isdigit())

    def definir_informacion(self, cedula):
        url_base = self.env.company.url_base
        if url_base:
            url_base = url_base.strip()

            if url_base[-1:] == '/':
                url_base = url_base[:-1]

            end_point = url_base + 'identificacion=' + cedula

            headers = {'content-type': 'application/json', }

            peticion = requests.get(end_point, headers=headers, timeout=10)

            ultimo_mensaje = 'Fecha/Hora: ' + str(datetime.now()) + \
                             ', Codigo: ' + str(peticion.status_code) + \
                             ', Mensaje: ' + str(peticion._content.decode())

            if peticion.status_code in (200, 202) and len(peticion._content) > 0:
                contenido = json.loads(str(peticion._content, 'utf-8'))
                self.env.company.ultima_respuesta = ultimo_mensaje

                if contenido.get('nombre') and contenido.get('tipoIdentificacion'):
                    self.name = contenido.get('nombre')
                    if 'identification_id' in self._fields:
                        clasificacion = contenido.get('tipoIdentificacion')

                        self.identification_id = self.env['identification.type'].search([('code',
                                                                                          '=',
                                                                                          clasificacion)], limit=1).id

                if contenido.get('actividades') and 'activity_id' in self._fields:
                    for act in contenido.get('actividades'):
                        if act.get('estado') == 'A':
                            self.activity_id = self.env['economic.activity'].search([('code',
                                                                                      '=',
                                                                                      str(act.get('codigo')))],
                                                                                    limit=1).id

    @api.onchange('vat')
    def onchange_vat(self):
        if self.vat:
            self.definir_informacion(self.vat)
