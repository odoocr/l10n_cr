# -*- coding: utf-8 -*-

from . import models
from . import extensions


def post_init_hook(cr, registry):

    
    cr.execute('update account_invoice_line set economic_activity_id = ai.economic_activity_id from account_invoice ai inner join account_invoice_line ail on ai.id = ail.invoice_id where ail.economic_activity_id is NULL')