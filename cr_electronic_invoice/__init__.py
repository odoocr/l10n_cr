# -*- coding: utf-8 -*-

from . import models
from . import extensions


def post_init_hook(cr, registry):

    
    cr.execute('UPDATE account_invoice_line ail SET economic_activity_id = ai.economic_activity_id FROM account_invoice ai WHERE ai.id = ail.invoice_id AND ail.economic_activity_id is NULL')