from odoo import models, api, _
from datetime import datetime
import json
import requests
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def limpiar_cedula(self, vat):
        if vat:
            return ''.join(i for i in vat if i.isdigit())

    def definir_informacion(self, cedula):
        set_param = self.env['ir.config_parameter'].sudo().set_param
        get_param = self.env['ir.config_parameter'].sudo().get_param

        url_base_yo_contribuyo = get_param('url_base_yo_contribuyo')
        usuario_yo_contribuyo = get_param('usuario_yo_contribuyo')
        token_yo_contribuyo = get_param('token_yo_contribuyo')
        url_base = get_param('url_base')

        get_tributary_information = get_param('get_tributary_information')
        get_yo_contribuyo_information = get_param('get_yo_contribuyo_information')

        if url_base_yo_contribuyo and usuario_yo_contribuyo and token_yo_contribuyo and get_yo_contribuyo_information:
            url_base_yo_contribuyo = url_base_yo_contribuyo.strip()

            if url_base_yo_contribuyo[-1:] == '/':
                url_base_yo_contribuyo = url_base_yo_contribuyo[:-1]

            end_point = url_base_yo_contribuyo + 'identificacion=' + cedula

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
                    self.email = all_emails_yo_contribuyo

            except:
                _logger.info(_('The email query service is unavailable at this moment'))

        if url_base and get_tributary_information:
            url_base = url_base.strip()

            if url_base[-1:] == '/':
                url_base = url_base[:-1]

            end_point = url_base + 'identificacion=' + cedula

            headers = {'content-type': 'application/json', }
            try:
                peticion = requests.get(end_point, headers=headers, timeout=10)

                ultimo_mensaje = 'Fecha/Hora: ' + str(datetime.now()) + \
                                 ', Codigo: ' + str(peticion.status_code) + \
                                 ', Mensaje: ' + str(peticion._content.decode())
                set_param('ultima_respuesta', ultimo_mensaje)
                if peticion.status_code in (200, 202) and len(peticion._content) > 0:
                    contenido = json.loads(str(peticion._content, 'utf-8'))

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
            except:
                _logger.info(_('The name query service is unavailable at this moment'))

    @api.onchange('vat')
    def onchange_vat(self):
        if self.vat:
            self.definir_informacion(self.vat)
