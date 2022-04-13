from datetime import datetime
import json
import requests
import logging

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class ActualizarPosApi(http.Controller):
    # https://api.thunder.com.ve/control_rig/84:F3:EB:22:6E:D9
    @http.route(['/cedula/<vat>', ], type='http', auth="user", website=True)
    def index(self, vat):

        company_id = http.request.env['res.company'].sudo().search([], limit=1)

        url_base_yo_contribuyo = company_id.url_base_yo_contribuyo
        usuario_yo_contribuyo = company_id.usuario_yo_contribuyo
        token_yo_contribuyo = company_id.token_yo_contribuyo
        if url_base_yo_contribuyo and usuario_yo_contribuyo and token_yo_contribuyo:
            url_base_yo_contribuyo = url_base_yo_contribuyo.strip()

            if url_base_yo_contribuyo[-1:] == '/':
                url_base_yo_contribuyo = url_base_yo_contribuyo[:-1]

            end_point = url_base_yo_contribuyo + 'identificacion=' + vat

            headers = {'access-user': usuario_yo_contribuyo, 'access-token': token_yo_contribuyo }

            peticion = requests.get(end_point, headers=headers, timeout=10)
            all_emails_yo_contribuyo = ''

            if peticion.status_code in (200, 202) and len(peticion._content) > 0:
                contenido = json.loads(str(peticion._content, 'utf-8'))
                emails_yo_contribuyo = contenido['Resultado']['Correos']
                for email_yo_contribuyo in emails_yo_contribuyo:
                    all_emails_yo_contribuyo = all_emails_yo_contribuyo + email_yo_contribuyo['Correo'] + ','
                all_emails_yo_contribuyo = all_emails_yo_contribuyo[:-1]

        url_base = company_id.url_base

        if url_base:
            # Elimina la barra al final de la URL para prevenir error al conectarse
            if url_base[-1:] == '/':
                url_base = url_base[:-1]

            end_point = url_base + 'identificacion=' + vat

            headers = {'content-type': 'application/json', }

            # Petición GET a la API
            peticion = requests.get(end_point, headers=headers, timeout=3)
            ultimo_mensaje = 'Fecha/Hora: ' + str(datetime.now()) + \
                             ', Codigo: ' + str(peticion.status_code) + \
                             ', Mensaje: ' + str(peticion._content.decode())

            # Respuesta de la API
            if peticion.status_code in (200, 202) and len(peticion._content) > 0:
                contenido = json.loads(str(peticion._content, 'utf-8'))

                request.env.company.ultima_respuesta = ultimo_mensaje

                if 'nombre' in contenido:

                    identification_id = ''
                    res_partner = http.request.env['res.partner']

                    if 'activity_id' in res_partner._fields:
                        actividades = contenido.get('actividades')
                        act = []
                        for actividad in actividades:
                            activity = http.request.env['economic.activity'].sudo().search([(
                                'code', '=', actividad.get('codigo')),
                                ('active', 'in', [False, True])])
                            acti = {'id': activity.id, 'name': activity.name}
                            act.insert(len(act), acti)

                    if 'identification_id' in res_partner._fields:

                        id_type = http.request.env['identification.type']

                        if 'tipoIdentificacion' in contenido:
                            clasificacion = contenido.get('tipoIdentificacion')
                            # Cedula Fisica
                            if clasificacion == '01':
                                identification_id = id_type.search([('code', '=', '01')], limit=1).id
                            # Cedula Juridica
                            elif clasificacion == '02':
                                identification_id = id_type.search([('code', '=', '02')], limit=1).id
                            # Cedula Juridica
                            elif clasificacion == '03':
                                identification_id = id_type.search([('code', '=', '03')], limit=1).id
                            # Cedula Juridica
                            elif clasificacion == '04':
                                identification_id = id_type.search([('code', '=', '04')], limit=1).id
                            # Cedula Juridica
                            elif clasificacion == '05':
                                identification_id = id_type.search([('code', '=', '05')], limit=1).id
                    if contenido.get('nombre') is not None:
                        name = contenido.get('nombre')
                        if 'activity_id' in res_partner._fields:
                            retorno = {"nombre": str(name),
                                       "identification_id": str(identification_id),
                                       "email": str(all_emails_yo_contribuyo),
                                       "activity": act}
                        else:
                            retorno = {"nombre": str(name)}
                        return '%s' % str(retorno).replace("'", "\"")

            else:
                request.env.company.ultima_respuesta = ultimo_mensaje