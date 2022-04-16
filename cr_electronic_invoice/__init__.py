# -*- coding: utf-8 -*-

from . import models
from . import extensions
from . import wizard

def post_init_check(cr, registry):
    cr.execute("UPDATE account_move SET state_tributacion = state_send_invoice WHERE state_tributacion is null and type in ('in_invoice', 'in_refund') and state_send_invoice is not null;")
    cr.execute('UPDATE account_move_line ail SET economic_activity_id = ai.economic_activity_id FROM account_move ai WHERE ai.id = ail.move_id AND ail.economic_activity_id is NULL and ai.economic_activity_id is not NULL;')
