from datetime import datetime
import json
import requests

from odoo import http
from odoo.http import request


class ActualizarPosApi(http.Controller):
    # https://api.thunder.com.ve/control_rig/84:F3:EB:22:6E:D9
    @http.route(['/cedula/<vat>', ], type='http', auth="user", website=True)
    def index(self, vat):
        set_param = request.env['ir.config_parameter'].sudo().set_param
        get_param = request.env['ir.config_parameter'].sudo().get_param

        url_base = get_param('url_base')
        url_base_yo_contribuyo = get_param('url_base_yo_contribuyo')
        usuario_yo_contribuyo = get_param('usuario_yo_contribuyo')
        token_yo_contribuyo = get_param('token_yo_contribuyo')

        get_tributary_information = get_param('get_tributary_information')
        get_yo_contribuyo_information = get_param('get_yo_contribuyo_information')

        if url_base_yo_contribuyo and usuario_yo_contribuyo and token_yo_contribuyo and get_yo_contribuyo_information:
            url_base_yo_contribuyo = url_base_yo_contribuyo.strip()

            if url_base_yo_contribuyo[-1:] == '/':
                url_base_yo_contribuyo = url_base_yo_contribuyo[:-1]

            end_point = url_base_yo_contribuyo + 'identificacion=' + vat

            headers = {'access-user': usuario_yo_contribuyo, 'access-token': token_yo_contribuyo}
            try:
                peticion = requests.get(end_point, headers=headers, timeout=10)

                all_emails_yo_contribuyo = ''

                if peticion.status_code in (200, 202) and len(peticion._content) > 0:
                    contenido = json.loads(str(peticion._content, 'utf-8'))
                    emails_yo_contribuyo = contenido['Resultado']['Correos']
                    for email_yo_contribuyo in emails_yo_contribuyo:
                        all_emails_yo_contribuyo = all_emails_yo_contribuyo + email_yo_contribuyo['Correo'] + ','
                    all_emails_yo_contribuyo = all_emails_yo_contribuyo[:-1]
            except:
                _logger.info(_('The email query service is unavailable at this moment'))

        if url_base and get_tributary_information:
            # Elimina la barra al final de la URL para prevenir error al conectarse
            if url_base[-1:] == '/':
                url_base = url_base[:-1]

            end_point = url_base + 'identificacion=' + vat

            headers = {'content-type': 'application/json', }
            try:
                # Petición GET a la API
                peticion = requests.get(end_point, headers=headers, timeout=3)
                ultimo_mensaje = 'Fecha/Hora: ' + str(datetime.now()) + \
                                 ', Codigo: ' + str(peticion.status_code) + \
                                 ', Mensaje: ' + str(peticion._content.decode())
                set_param('ultima_respuesta', ultimo_mensaje)
                # Respuesta de la API
                if peticion.status_code in (200, 202) and len(peticion._content) > 0:
                    contenido = json.loads(str(peticion._content, 'utf-8'))

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

                            if 'tipoIdentificacion' in contenido:
                                clasificacion = contenido.get('tipoIdentificacion')
                                # Cedula Fisica
                                identification_id = request.env['identification.type'].search([('code',
                                                                                                '=',
                                                                                                clasificacion)],
                                                                                              limit=1).id
                        if contenido.get('nombre') is not None:
                            name = contenido.get('nombre')
                            if 'activity_id' in res_partner._fields:
                                retorno = {"nombre": str(name),
                                           "identification_id": str(identification_id),
                                           "email": str(all_emails_yo_contribuyo),
                                           "activity": act}
                            else:
                                retorno = {"nombre": str(name),
                                           "identification_id": str(identification_id),
                                           "email": str(all_emails_yo_contribuyo)}
                            return '%s' % str(retorno).replace("'", "\"")
            except:
                _logger.info(_('The name query service is unavailable at this moment'))
