
class AccountInvoiceImportConfig(models.Model):
    _inherit = "account.invoice.import.config"

    totals_rounding = fields.Integer(string="Digits to round total amounts")