try:
    from BytesIO import BytesIO
except ImportError:
    from io import BytesIO
import zipfile
from datetime import datetime
from odoo import http
from odoo.http import request
from odoo.http import content_disposition
import ast


class Binary(http.Controller):
    @http.route('/web/binary/download_document', type='http', auth="public")
    def download_document(self, **kw):
        new_tab = ast.literal_eval(kw['tab_id'])
        # Validate that you are only trying to download what corresponds to the invoice
        invoice = request.env['account.move'].sudo().browse(int(kw['invoice_id']))
        domain = [('res_model', '=', invoice._name),
                  ('res_id', '=', invoice.id),
                  ('res_field', '=', 'xml_comprobante'),
                  ('name', '=', invoice.tipo_documento + '_' + invoice.number_electronic + '.xml')]
        attachment = request.env['ir.attachment'].sudo().search(domain, limit=1)
        domain_resp = [('res_model', '=', invoice._name),
                       ('res_id', '=', invoice.id),
                       ('res_field', '=', 'xml_respuesta_tributacion'),
                       ('name', '=', 'AHC_' + invoice.number_electronic + '.xml')]
        attachment_resp = request.env['ir.attachment'].sudo().search(domain_resp, limit=1)

        attachment_ids = request.env['ir.attachment'].sudo().search([('id', 'in', new_tab)])
        file_dict = {}
        for attachment_id in attachment_ids:
            if attachment_id.id == attachment.id or attachment_id.id == attachment_resp.id:
                file_store = attachment_id.store_fname
                if file_store:
                    file_name = attachment_id.name
                    file_path = attachment_id._full_path(file_store)
                    file_dict["%s:%s" % (file_store, file_name)] = dict(path=file_path, name=file_name)
        zip_filename = datetime.now()
        zip_filename = "%s.zip" % zip_filename
        bitIO = BytesIO()
        zip_file = zipfile.ZipFile(bitIO, "w", zipfile.ZIP_DEFLATED)
        for file_info in file_dict.values():
            zip_file.write(file_info["path"], file_info["name"])
        zip_file.close()
        return request.make_response(bitIO.getvalue(),
                                     headers=[('Content-Type', 'application/x-zip-compressed'),
                                              ('Content-Disposition', content_disposition(zip_filename))])
