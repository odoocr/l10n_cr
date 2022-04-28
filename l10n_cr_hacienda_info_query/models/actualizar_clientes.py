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

    ultima_respuesta = fields.Text(string="Latest API response", help="Last API Response, this allows debugging errors if they exist")
    url_base = fields.Char(string="URL Base", required=False, help="URL Base of the END POINT", default="https://api.hacienda.go.cr/fe/ae?")

    url_base_yo_contribuyo = fields.Char(string="URL Base Yo Contribuyo",
                           required=False,
                           help="URL Base Yo Contribuyo",
                           default="https://api.hacienda.go.cr/fe/mifacturacorreo?")
    
    usuario_yo_contribuyo = fields.Char(string="Usuario Yo Contribuyo",
                           required=False,
                           help="Usuario Yo Contribuyo")

    token_yo_contribuyo = fields.Char(string="Token Yo Contribuyo",
                           required=False,
                           help="Token Yo Contribuyo")
class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = "res.partner"

    def limpiar_cedula(self,vat):
        if vat:
            return ''.join(i for i in vat if i.isdigit())

    def definir_informacion(self,cedula):
        url_base_yo_contribuyo = self.env.company.url_base_yo_contribuyo
        usuario_yo_contribuyo = self.env.company.usuario_yo_contribuyo
        token_yo_contribuyo = self.env.company.token_yo_contribuyo
        if url_base_yo_contribuyo and usuario_yo_contribuyo and token_yo_contribuyo:
            url_base_yo_contribuyo = url_base_yo_contribuyo.strip()

            if url_base_yo_contribuyo[-1:] == '/':
                url_base_yo_contribuyo = url_base_yo_contribuyo[:-1]

            end_point = url_base_yo_contribuyo + 'identificacion=' + cedula

            headers = {'access-user': usuario_yo_contribuyo, 'access-token': token_yo_contribuyo }

            peticion = requests.get(end_point, headers=headers, timeout=10)
            all_emails_yo_contribuyo = ''

            if peticion.status_code in (200, 202) and len(peticion._content) > 0:
                contenido = json.loads(str(peticion._content, 'utf-8'))
                emails_yo_contribuyo = contenido['Resultado']['Correos']
                for email_yo_contribuyo in emails_yo_contribuyo:
                    all_emails_yo_contribuyo = all_emails_yo_contribuyo + email_yo_contribuyo['Correo'] + ','
                all_emails_yo_contribuyo = all_emails_yo_contribuyo[:-1]
                self.email = all_emails_yo_contribuyo 

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

