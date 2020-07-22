# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Service - Import vendor bill from Email

import zipfile
import io
import re
import logging
import email
import dateutil
import pytz
import base64
import pathlib
try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib


from lxml import etree
from datetime import datetime
import re


from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError,UserError
from odoo.tools import float_compare, pycompat
from odoo.tests.common import Form
from . import api_facturae

_logger = logging.getLogger(__name__)
MAX_POP_MESSAGES = 50
MAIL_TIMEOUT = 60



class FetchmailServer(models.Model):
    _inherit = 'fetchmail.server'

    @api.multi
    def _create_invoice_from_email(self):
        _logger.info("Test from ir.cron")
        res_companies_ids = self.env['res.company'].sudo().search([])
        for res_company_id in res_companies_ids:
            if res_company_id.import_bill_automatic:
                additionnal_context = {
                    'fetchmail_cron_running': True
                }
                MailThread = self.env['mail.thread']
                server = res_company_id.import_bill_mail_server_id
                additionnal_context['fetchmail_server_id'] = server.id
                additionnal_context['server_type'] = server.type
                # Buscar el mail, leer correos --- importar factura ...
                _logger.info('Start checking for new emails on %s server %s', server.type, server.name)
                count, failed = 0, 0
                imap_server = None
                pop_server = None
                if server.type == 'imap':
                    try:
                        imap_server = server.connect()
                        imap_server.select()
                        result, data = imap_server.search(None, '(UNSEEN)')

                        for num in data[0].split():
                            res_id = None
                            result, data = imap_server.fetch(num, '(RFC822)')
                            imap_server.store(num, '-FLAGS', '\\Seen')
                            message = data[0][1]
                            try:
                                # To leave the mail in the state in which they were.
                                if isinstance(message, xmlrpclib.Binary):
                                    message = bytes(message.data)
                                if isinstance(message, pycompat.text_type):
                                    message = message.encode('utf-8')
                                extract = getattr(email, 'message_from_bytes', email.message_from_string)
                                msg_txt = extract(message)

                                # parse the message, verify we are not in a loop by checking message_id is not duplicated
                                msg = MailThread.with_context(**additionnal_context).message_parse(msg_txt,
                                                                                                   save_original=True)
                                result = self.create_invoice_with_attamecth(msg, res_company_id)
                                if result:
                                    _logger.info("Invoice created correctly %s",result)
                            except Exception:
                                _logger.info('Failed to process mail from %s server %s.', server.type, server.name,
                                             exc_info=True)
                                failed += 1
                            imap_server.store(num, '+FLAGS', '\\Seen')
                            self._cr.commit()
                            count += 1

                        _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", count,
                                     server.type, server.name, (count - failed), failed)
                    except Exception:
                        _logger.info("General failure when trying to fetch mail from %s server %s.", server.type,
                                     server.name, exc_info=True)
                    finally:
                        if imap_server:
                            imap_server.close()
                            imap_server.logout()
                elif server.type == 'pop':
                    try:
                        while True:
                            pop_server = server.connect()
                            (num_messages, total_size) = pop_server.stat()
                            pop_server.list()
                            for num in range(1, min(MAX_POP_MESSAGES, num_messages) + 1):
                                (header, messages, octets) = pop_server.retr(num)
                                message = (b'\n').join(messages)
                                res_id = None
                                try:
                                    # res_id = MailThread.with_context(**additionnal_context).message_process(
                                    #    server.object_id.model, message, save_original=server.original,
                                    #    strip_attachments=(not server.attach))
                                    # To leave the mail in the state in which they were.
                                    if isinstance(message, xmlrpclib.Binary):
                                        message = bytes(message.data)
                                    if isinstance(message, pycompat.text_type):
                                        message = message.encode('utf-8')
                                    extract = getattr(email, 'message_from_bytes', email.message_from_string)
                                    msg_txt = extract(message)

                                    # parse the message, verify we are not in a loop by checking message_id is not duplicated
                                    msg = MailThread.with_context(**additionnal_context).message_parse(msg_txt, save_original=True)
                                    result = self.create_invoice_with_attamecth(msg,res_company_id)
                                    if result:
                                        pop_server.dele(num)
                                        _logger.info("Invoice created correctly %s", str(result))
                                except Exception:
                                    _logger.info('Failed to process mail from %s server %s.', server.type, server.name,
                                                 exc_info=True)
                                    failed += 1
                                self.env.cr.commit()
                            if num_messages < MAX_POP_MESSAGES:
                                break
                            pop_server.quit()
                            _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", num_messages,
                                         server.type, server.name, (num_messages - failed), failed)
                    except Exception:
                        _logger.info("General failure when trying to fetch mail from %s server %s.", server.type,
                                     server.name, exc_info=True)
                    finally:
                        if pop_server:
                            pop_server.quit()
                server.write({'date': fields.Datetime.now()})


    def is_xml_file_in_attachment(self, attach):
        file_name = attach.fname or 'item.ignore'
        if pathlib.Path(file_name.upper()).suffix == '.XML':
            return True
        return False

    def check_bill_exist(self, attach):
        if self.env['account.invoice'].search([('fname_xml_supplier_approval', '=', attach.fname)], limit=1):
            # invoice already exist
            _logger.info('E-invoice already exist: %s', attach.fname)
            return True
        return False


    def create_invoice_with_attamecth(self,msg,company_id):
        for attach in msg.get('attachments'):
            if self.is_xml_file_in_attachment(attach) and not self.check_bill_exist(attach):
                try:
                    attachencode = base64.encodestring(attach.content)
                    invoice_xml = etree.fromstring(base64.b64decode(attachencode))
                    document_type = re.search('FacturaElectronica|NotaCreditoElectronica|NotaDebitoElectronica|TiqueteElectronico', invoice_xml.tag).group(0)
                    if document_type == 'TiqueteElectronico':
                        _logger.info("This is a TICKET only invoices are valid for taxes")
                        continue

                    self = self.with_context(default_journal_id=company_id.import_bill_journal_id.id,default_type='in_invoice',type='in_invoice',journal_type='purchase')
                    invoice_form = Form(self.env['account.invoice'], view='account.invoice_supplier_form')
                    invoice = invoice_form.save()
                    invoice.fname_xml_supplier_approval = attach.fname
                    invoice.xml_supplier_approval = base64.encodestring(attach.content)
                    api_facturae.load_xml_data_from_mail(invoice, True, company_id.import_bill_account_id,
                                               company_id.import_bill_product_id,
                                               company_id.import_bill_account_analytic_id)


                    if invoice:
                        attachment_id = self.env['ir.attachment'].create({
                            'name': attach.fname,
                            'type': 'binary',
                            'datas': base64.b64encode(attach.content),
                            'res_model': 'account.invoice',
                            'res_id': invoice.id,
                            'mimetype': 'application/xml'
                        })
                        invoice.message_post(attachment_ids=[attachment_id.id])
                        return invoice
                    else:
                        False

                except Exception as e:
                    _logger.info("This XML file is not XML-compliant. Error: %s",e)
                    continue
        return False


