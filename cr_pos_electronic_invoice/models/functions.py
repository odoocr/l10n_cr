import json
import requests
import logging
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import datetime
import pytz
import base64
import xml.etree.ElementTree as ET
import random

_logger = logging.getLogger(__name__)


def get_clave(self, url, tipo_documento, next_number):
    payload = {}
    headers = {}
    # get Clave MH
    payload['w'] = 'clave'
    payload['r'] = 'clave'
    if self.company_id.identification_id.id == 1:
        payload['tipoCedula'] = 'fisico'
    elif self.company_id.identification_id.id == 2:
        payload['tipoCedula'] = 'juridico'
    payload['tipoDocumento'] = tipo_documento
    payload['cedula'] = self.company_id.vat
    payload['codigoPais'] = self.company_id.phone_code
    payload['consecutivo'] = next_number
    payload['situacion'] = 'normal'
    #payload['codigoSeguridad'] = self.company_id.security_code
    payload['codigoSeguridad'] = str(random.randint(1, 99999999))
    payload['sucursal'] = self.sale_journal.sucursal
    payload['terminal'] = self.sale_journal.terminal

    response = requests.request("POST", url, data=payload, headers=headers)
    #response_json = json.loads(response._content)
    response_json = response.json()
    return response_json

def token_hacienda(inv, env, url):
    payload = {}
    headers = {}
    payload['w'] = 'token'
    payload['r'] = 'gettoken'
    payload['grant_type'] = 'password'
    payload['client_id'] = env
    payload['username'] = inv.company_id.frm_ws_identificador
    payload['password'] = inv.company_id.frm_ws_password

    response = requests.request("POST", url, data=payload, headers=headers)
    response_json = response.json()
    return response_json
