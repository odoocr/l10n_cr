from odoo import models, fields, api, tools
from odoo.exceptions import UserError, Warning
from datetime import datetime, date, timedelta
import json, requests, re

class res_company(models.Model):
    _name = 'res.company'
    _inherit = ['res.company']

    token = fields.Text(string="Token", required=False, help="Token de acceso a la API", default="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2dpbiI6ImNvY28iLCJpZCI6bnVsbCwidGltZSI6IjIwMTktMDUtMTdUMDQ6Mjk6NDYuNjAxWiIsImlhdCI6MTU1ODA2NzM4NiwiZXhwIjoyMDAxNTU4MDY3Mzg2fQ.k75fI4AqWaxWW69AUAWVADrlsjQT--hfEo2MOvDewvY")
    ultima_respuesta = fields.Text(string="Última Respuesta de API", help="Última Respuesta de API, esto permite depurar errores en caso de existir")
    url_base = fields.Char(string="URL Base", required=False, help="URL Base del END POINT", default="http://")

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = "res.partner"

    cedula = fields.Char(related="vat")

    def limpiar_cedula(self,cedula):
        if cedula:
            return ''.join(i for i in cedula if i.isdigit())

    @api.onchange('cedula')
    def onchange_cedula(self):
        self.name = ''
        self.identification_id = ''
        self.vat = self.cedula

    #Funcion ejecutada al haber un cambio en el campo vat(cedula)
    @api.onchange('vat','cedula')
    def onchange_vat(self):

        #Valida que el campo vat(cedula) este llenom esto evita que se ejecute el codigo al inicio
        if self.vat:
            self.vat = self.limpiar_cedula(self.vat)
            self.cedula = self.vat
            url_base = self.company_id.url_base
            token = str(self.company_id.token)
            self.name = ''

            #Valida que existan los campos url_base y token
            if url_base and token :
                #Limpia caracteres en blanco en los extremos
                url_base = url_base.strip()
                token = token.strip()

                #Elimina la barra al final de la URL para prevenir error al conectarse
                if url_base[-1:] == '/':
                    url_base = url_base[:-1]

                end_point = url_base + '/cedula/' + self.vat

                headers = {
                          'content-type': 'application/json',
                          'token': token
                            }

                #Petición GET a la API
                peticion = requests.get(end_point, headers=headers, timeout=10)

                ultimo_mensaje = 'Fecha/Hora: ' + str(datetime.now()) + ', Codigo: ' + str(peticion.status_code) + ', Mensaje: ' + str(peticion._content.decode())

                #Respuesta de la API
                if peticion.status_code in (200,202) and len(peticion._content) > 0:
                    contenido = json.loads(str(peticion._content,'utf-8'))
                    self.env.cr.execute("UPDATE  res_company SET ultima_respuesta='%s' WHERE id=%s" % (ultimo_mensaje,self.company_id.id))

                    if 'nombre' in contenido and 'nombre_juri' in contenido and 'apellidos' in contenido:

                        #Compatibilidad con FE
                        if 'identification_id' in self._fields:
                            if 'clasificacion' in contenido:
                                clasificacion = contenido.get('clasificacion')
                                if clasificacion == 'F':#Cedula Fisicaclasificacion
                                    self.identification_id = self.env['identification.type'].search([('code', '=', '01')], limit=1).id
                                elif clasificacion == 'J':#Cedula Juridica
                                    self.identification_id = self.env['identification.type'].search([('code', '=', '02')], limit=1).id
                                elif clasificacion == 'D':#Cedula Juridica
                                    self.identification_id = self.env['identification.type'].search([('code', '=', '03')], limit=1).id
                                elif clasificacion == 'N':#Cedula Juridica
                                    self.identification_id = self.env['identification.type'].search([('code', '=', '04')], limit=1).id
                                elif clasificacion == 'E':#Cedula Juridica
                                    self.identification_id = self.env['identification.type'].search([('code', '=', '05')], limit=1).id

                        if contenido.get('nombre') != None:
                            name = contenido.get('nombre')
                            self.company_type = 'person'

                            if contenido.get('apellidos') != None:
                                name +=  ' ' + contenido.get('apellidos')

                            self.name = name

                        elif contenido.get('nombre_juri') != None:
                            self.name = contenido.get('nombre_juri')
                            self.company_type = 'company'

                #Si la petición arroja error se almacena en el campo ultima_respuesta de res_company. Nota: se usa execute ya que el metodo por objeto no funciono
                else:
                    self.env.cr.execute("UPDATE  res_company SET ultima_respuesta='%s' WHERE id=%s" % (ultimo_mensaje,self.company_id.id))

