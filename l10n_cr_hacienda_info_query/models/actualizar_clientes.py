# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from odoo.exceptions import UserError, Warning
from datetime import datetime, date, timedelta
import json, requests, re
#import logging

#_logger = logging.getLogger(__name__)

class res_company(models.Model):
    _name = 'res.company'
    _inherit = ['res.company']

    ultima_respuesta = fields.Text(string="Última Respuesta de API", help="Última Respuesta de API, esto permite depurar errores en caso de existir")
    url_base = fields.Char(string="URL Base", required=False, help="URL Base del END POINT", default="https://api.hacienda.go.cr/fe/ae?")

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = "res.partner"

    def limpiar_cedula(self,vat):
        if vat:
            return ''.join(i for i in vat if i.isdigit())

    def definir_informacion(self,cedula):
        url_base = self.env.company.url_base
        if url_base:
            url_base = url_base.strip()

            if url_base[-1:] == '/':
                url_base = url_base[:-1]

            end_point = url_base + 'identificacion=' + cedula 


            headers = {
                          'content-type': 'application/json',
                            }

            peticion = requests.get(end_point, headers=headers, timeout=10)

            ultimo_mensaje = 'Fecha/Hora: ' + str(datetime.now()) + ', Codigo: ' + str(peticion.status_code) + ', Mensaje: ' + str(peticion._content.decode())

            if peticion.status_code in (200,202) and len(peticion._content) > 0:
                contenido = json.loads(str(peticion._content,'utf-8'))
                actividades = contenido.get('actividades')
#                _logger.info(contenido)
                self.env.company.ultima_respuesta = ultimo_mensaje

                if 'nombre' in contenido:
                    if 'identification_id' in self._fields:
                        if 'tipoIdentificacion' in contenido:
                            clasificacion = contenido.get('tipoIdentificacion')
                            if clasificacion == '01':#Cedula Fisica
                                self.identification_id = self.env['identification.type'].search([('code', '=', '01')], limit=1).id
                            elif clasificacion == '02':#Cedula Juridica
                                self.identification_id = self.env['identification.type'].search([('code', '=', '02')], limit=1).id
                            elif clasificacion == '03':#Cedula Juridica
                                self.identification_id = self.env['identification.type'].search([('code', '=', '03')], limit=1).id
                            elif clasificacion == '04':#Cedula Juridica
                                self.identification_id = self.env['identification.type'].search([('code', '=', '04')], limit=1).id
                            elif clasificacion == '05':#Cedula Juridica
                                self.identification_id = self.env['identification.type'].search([('code', '=', '05')], limit=1).id

                    if contenido.get('nombre') != None:
                       name = contenido.get('nombre')
                       self.name = name
                       for act in actividades:
                          if act.get('estado') == 'A':
                                  self.activity_id = self.env['economic.activity'].search([('code', '=', str(act.get('codigo')))], limit=1).id
            else:
                self.activity_id = self.env['economic.activity'].search([('code', '=', str(act.get('codigo')))], limit=1).id

    @api.onchange('vat')
    def onchange_vat(self):
        if not self.vat:
            self.name = self.name
        else:
            self.definir_informacion(self.vat)

