

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class IdentificationType(models.Model):
    _name = "identification.type"

    code = fields.Char(help='Identification related code.')
    name = fields.Char(help='Identification code name.')
    notes = fields.Text(help='Identification notes.')
