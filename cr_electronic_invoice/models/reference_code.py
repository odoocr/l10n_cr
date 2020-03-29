# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ReferenceCode(models.Model):
    _name = "reference.code"

    active = fields.Boolean(string="Active", required=False, default=True)
    code = fields.Char(string="Code", required=False, )
    name = fields.Char(string="Name", required=False, )
