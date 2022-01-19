# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class IdentificationType(models.Model):
    _name = "identification.type"

    code = fields.Char(string="Code", required=False, )
    name = fields.Char(string="Name", required=False, )
    notes = fields.Text(string="Notes", required=False, )
