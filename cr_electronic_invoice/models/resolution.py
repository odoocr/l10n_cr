# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class Resolution(models.Model):
    _name = "resolution"

    active = fields.Boolean(string="Active", required=False, default=True)
    name = fields.Char(string="Name", required=False, )
    date_resolution = fields.Date(string="Resolution Date", required=False, )
