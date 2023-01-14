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
        company_id = self.company_id if self.company_id else self.env.user.company_id
        url_base_yo_contribuyo = company_id.url_base_yo_contribuyo
        usuario_yo_contribuyo = company_id.usuario_yo_contribuyo
        token_yo_contribuyo = company_id.token_yo_contribuyo
        url_base = company_id.url_base

        get_tributary_information = company_id.get_tributary_information
        get_yo_contribuyo_information = company_id.get_yo_contribuyo_information

        if url_base_yo_contribuyo and usuario_yo_contribuyo and token_yo_contribuyo and get_yo_contribuyo_information:
            url_base_yo_contribuyo = url_base_yo_contribuyo.strip()

            if url_base_yo_contribuyo[-1:] == '/':
                url_base_yo_contribuyo = url_base_yo_contribuyo[:-1]

            end_point = url_base_yo_contribuyo + 'identificacion=' + cedula

            headers = {
                'access-user': usuario_yo_contribuyo,
                'access-token': token_yo_contribuyo
            }

            try:
                peticion = requests.get(end_point, headers=headers, timeout=10)
                all_emails_yo_contribuyo = ''
                ultimo_mensaje = 'Datetime: %s\n' % str(datetime.now())
                ultimo_mensaje += 'Code: %s\n' % str(peticion.status_code)
                ultimo_mensaje += 'Message: %s' % str(peticion._content.decode())

                company_id.ultima_respuesta_yo_contribuyo = ultimo_mensaje

                if peticion.status_code in (200, 202) and len(peticion._content) > 0:
                    contenido = json.loads(str(peticion._content, 'utf-8'))
                    emails_yo_contribuyo = contenido['Resultado']['Correos']
                    for email_yo_contribuyo in emails_yo_contribuyo:
                        all_emails_yo_contribuyo = all_emails_yo_contribuyo + email_yo_contribuyo['Correo'] + ','
                    all_emails_yo_contribuyo = all_emails_yo_contribuyo[:-1]
                    self.email = all_emails_yo_contribuyo

            except:
                message = _('The email query service is unavailable at this moment')
                _logger.info(message)
                ultimo_mensaje = 'Datetime: %s\n' % str(datetime.now())
                ultimo_mensaje += 'Message: %s' % message

                company_id.ultima_respuesta_yo_contribuyo = ultimo_mensaje

        if url_base and get_tributary_information:
            url_base = url_base.strip()

            if url_base[-1:] == '/':
                url_base = url_base[:-1]

            end_point = url_base + 'identificacion=' + cedula

            headers = {
                'content-type': 'application/json'
            }
            try:
                peticion = requests.get(end_point, headers=headers, timeout=10)

                ultimo_mensaje = 'Datetime: %s\n' % str(datetime.now())
                ultimo_mensaje += 'Code: %s\n' % str(peticion.status_code)
                ultimo_mensaje += 'Message: %s' % str(peticion._content.decode())

                company_id.ultima_respuesta = ultimo_mensaje

                if peticion.status_code in (200, 202) and len(peticion._content) > 0:
                    contenido = json.loads(str(peticion._content, 'utf-8'))

                    if contenido.get('nombre') and contenido.get('tipoIdentificacion'):
                        self.name = contenido.get('nombre')
                        if 'identification_id' in self._fields:
                            clasificacion = contenido.get('tipoIdentificacion')

                            self.identification_id = self.env['identification.type'].search(
                                [
                                    ('code', '=', clasificacion)
                                ],
                                limit=1
                            ).id

                    if contenido.get('actividades') and 'activity_id' in self._fields:
                        for act in contenido.get('actividades'):
                            if act.get('estado') == 'A':
                                self.activity_id = self.env['economic.activity'].search(
                                    [
                                        ('code', '=', str(act.get('codigo')))
                                    ],
                                    limit=1
                                ).id
            except:
                message = _('The email query service is unavailable at this moment')
                _logger.info(message)
                ultimo_mensaje = 'Datetime: %s\n' % str(datetime.now())
                ultimo_mensaje += 'Message: %s' % message

                company_id.ultima_respuesta_yo_contribuyo = ultimo_mensaje

    @api.onchange('vat')
    def onchange_vat(self):
        if self.vat:
            self.definir_informacion(self.vat)
