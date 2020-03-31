# -*- coding: utf-8 -*-

from . import models
from . import extensions


def post_init_hook(cr, registry):

    
    cr.execute('UPDATE account_move_line aml SET economic_activity_id = am.economic_activity_id FROM account_move am WHERE am.id = aml.move_id AND aml.economic_activity_id is NULL')