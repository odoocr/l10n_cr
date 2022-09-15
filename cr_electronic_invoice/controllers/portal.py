# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from collections import OrderedDict
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)


class PortalAccount(CustomerPortal):

    # ------------------------------------------------------------
    # My Invoices
    # ------------------------------------------------------------

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = {
            'page_name': 'invoice',
            'invoice': invoice
        }
        if invoice.number_electronic:
            domain = [('res_model', '=', 'account.move'), ('res_id', '=', invoice.id), ('name', 'like', invoice.tipo_documento + '_'+ invoice.number_electronic)]
            domain_resp = [('res_model', '=', 'account.move'), ('res_id', '=', invoice.id),
                                ('name', 'like', 'AHC_' + invoice.number_electronic)]

            attachment = request.env['ir.attachment'].sudo().search(domain, limit=1)
            if attachment:
                values['xml_documento'] = attachment

                
            attachment_resp = request.env['ir.attachment'].sudo().search(domain_resp, limit=1)
            if attachment_resp:
                values['xml_AHC'] = attachment_resp

        return self._get_page_view_values(invoice, access_token, values, 'my_invoices_history', False, **kwargs)