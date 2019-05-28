
from odoo import models, api, tools, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round

class BusinessDocumentImportCR(models.AbstractModel):
    _inherit = ['business.document.import']

    @api.model
    def _match_uom(self, uom_dict, chatter_msg, product=False):
        uuo = self.env['uom.uom']
        uoms = uuo.search([('code', '=', uom_dict['cr_code'])])

        if uoms:
            return uoms[0]
        else:
            chatter_msg.append(_(
                "The analysis of the business document returned '%s' "
                "as the unit of measure Hacienda code, but there is no "
                "unit of measure with that Hacienda code in Odoo. Please "
                "check the configuration of the units of measures in "
                "Odoo.") % uom_dict['cr_code'])
            return self.env.ref('uom.product_uom_unit')