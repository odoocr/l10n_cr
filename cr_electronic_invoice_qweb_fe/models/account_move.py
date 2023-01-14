#import base64
#import datetime
#import pytz

#import re
#from xml.sax.saxutils import escape
#from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import UserError
#from odoo.tools.misc import get_lang
#from odoo.http import request
#from odoo.tools import html2plaintext

#from .qr_generator import GenerateQrCode
#from . import api_facturae
#from .. import extensions

#import logging
#_logger = logging.getLogger(__name__)

class AccountInvoiceElectronic(models.Model):
    _inherit = "account.move"

    show_cabys_codes_invoice_qweb = fields.Boolean(
        string="Show CABYS codes on invoice",
        default=False
        )
