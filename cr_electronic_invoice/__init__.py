# -*- coding: utf-8 -*-

from . import models
from . import extensions

def post_init_check(cr, registry):
    cr.execute("UPDATE account_invoice SET state_tributacion = state_send_invoice WHERE state_tributacion is null and type in ('in_invoice', 'in_refund') and state_send_invoice is not null;")
    cr.execute('UPDATE account_invoice_line ail SET economic_activity_id = ai.economic_activity_id FROM account_invoice ai WHERE ai.id = ail.invoice_id AND ail.economic_activity_id is NULL and ai.economic_activity_id is not NULL;')
