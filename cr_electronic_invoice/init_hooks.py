from odoo import SUPERUSER_ID
from odoo.api import Environment

def post_init_hook(cr, pool):
    """
    Fetches all invoice and resets the sequence of their invoice line
    """
    env = Environment(cr, SUPERUSER_ID, {})

    env.cr.execute('update account_invoice_line set economic_activity_id = ai.economic_activity_id from account_invoice ai inner join account_invoice_line ail on ai.id = ail.invoice_id where ail.economic_activity_id = null')