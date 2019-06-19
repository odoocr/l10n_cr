# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from odoo.exceptions import UserError, Warning
from datetime import datetime, date, timedelta
import json, requests, re, logging

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class actualizar_pos_api(http.Controller):

    #https://api.thunder.com.ve/control_rig/84:F3:EB:22:6E:D9
    @http.route(['/cedula/<cedula>',], type='http', auth="user", website=True)
    def index(self,cedula):

        company_id = http.request.env['res.company'].sudo().search([],limit=1)
        url_base = company_id.url_base
        token = str(company_id.token)


        #Valida que existan los campos url_base y token
        if url_base and token :
            #Limpia caracteres en blanco en los extremos
            url_base = url_base.strip()
            token = token.strip()

            #Elimina la barra al final de la URL para prevenir error al conectarse
            if url_base[-1:] == '/':
                url_base = url_base[:-1]

            end_point = url_base + '/cedula/' + cedula

            headers = {
                      'content-type': 'application/json',
                      'token': token
                        }

            #Petición GET a la API
            peticion = requests.get(end_point, headers=headers, timeout=3)
            ultimo_mensaje = 'Fecha/Hora: ' + str(datetime.now()) + ', Codigo: ' + str(peticion.status_code) + ', Mensaje: ' + str(peticion._content.decode())

            #Respuesta de la API
            if peticion.status_code in (200,202) and len(peticion._content) > 0:
                contenido = json.loads(str(peticion._content,'utf-8'))
                http.request.env.cr.execute("UPDATE  res_company SET ultima_respuesta='%s' WHERE id=%s" % (ultimo_mensaje,company_id.id))

                if 'nombre' in contenido and 'nombre_juri' in contenido and 'apellidos' in contenido:

                    identification_id = ''
                    res_partner = http.request.env['res.partner']

                    if 'identification_id' in res_partner:

                        id_type = http.request.env['identification.type']

                        if 'clasificacion' in contenido:
                                clasificacion = contenido.get('clasificacion')
                                if clasificacion == 'F':#Cedula Fisicaclasificacion
                                    identification_id = id_type.search([('code', '=', '01')], limit=1).id
                                elif clasificacion == 'J':#Cedula Juridica
                                    identification_id = id_type.search([('code', '=', '02')], limit=1).id
                                elif clasificacion == 'D':#Cedula Juridica
                                    identification_id = id_type.search([('code', '=', '03')], limit=1).id
                                elif clasificacion == 'N':#Cedula Juridica
                                    identification_id = id_type.search([('code', '=', '04')], limit=1).id
                                elif clasificacion == 'E':#Cedula Juridica
                                    identification_id = id_type.search([('code', '=', '05')], limit=1).id

                    if contenido.get('nombre') != None:
                        #self.company_type = 'person'
                        name = contenido.get('nombre')

                        if contenido.get('apellidos') != None:
                            name +=  ' ' + contenido.get('apellidos')

                        retorno = {"nombre":str(name),"identification_id":str(identification_id)}
                        return '%s' % str(retorno).replace("'","\"")

                    elif contenido.get('nombre_juri') != None:
                        #self.company_type = 'company'
                        retorno = {"nombre":str(name),"identification_id":str(identification_id)}
                        return "'%s'" % str(retorno).replace("'","\"")

            #Si la petición arroja error se almacena en el campo ultima_respuesta de res_company. Nota: se usa execute ya que el metodo por objeto no funciono
            else:
                http.request.env.cr.execute("UPDATE  res_company SET ultima_respuesta='%s' WHERE id=%s" % (ultimo_mensaje,self.company_id.id))

