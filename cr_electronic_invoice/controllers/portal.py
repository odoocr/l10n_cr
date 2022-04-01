
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class PortalAccount(CustomerPortal):

    # ------------------------------------------------------------
    # My Invoices
    # ------------------------------------------------------------

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = {
            'page_name': 'invoice',
            'invoice': invoice
        }

        domain = [('res_model', '=', invoice._name),
                  ('res_id', '=', invoice.id),
                  ('res_field', '=', 'xml_comprobante'),
                  ('name', '=', invoice.tipo_documento + '_' + invoice.number_electronic + '.xml')]
        domain_resp = [('res_model', '=', invoice._name),
                       ('res_id', '=', invoice.id),
                       ('res_field', '=', 'xml_respuesta_tributacion'),
                       ('name', '=', 'AHC_' + invoice.number_electronic + '.xml')]

        attachment = request.env['ir.attachment'].sudo().search(domain, limit=1)
        if attachment:
            values['xml_documento'] = attachment

        attachment_resp = request.env['ir.attachment'].sudo().search(domain_resp, limit=1)
        if attachment_resp:
            values['xml_AHC'] = attachment_resp

        return self._get_page_view_values(invoice, access_token, values, 'my_invoices_history', False, **kwargs)
