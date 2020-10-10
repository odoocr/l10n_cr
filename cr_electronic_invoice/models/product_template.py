 # -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import requests
from datetime import datetime
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class ProductElectronic(models.Model):
    _inherit = "product.template"

    @api.model
    def _default_code_type_id(self):
        code_type_id = self.env['code.type.product'].search(
            [('code', '=', '04')], limit=1)
        return code_type_id or False

    commercial_measurement = fields.Char(string="Commercial Unit", )
    code_type_id = fields.Many2one("code.type.product", string="Code Type", default=_default_code_type_id)

    tariff_head = fields.Char(string="Export Tax rate", help='Tax rate to apply for exporting invoices' )
    
    cabys_code = fields.Char(string="CAByS Code", help='CAByS code from Ministerio de Hacienda')

    economic_activity_id = fields.Many2one("economic.activity", string="Economic Activity", help='Economic activity code from Ministerio de Hacienda')

    non_tax_deductible = fields.Boolean(string='Non Tax Deductible', default=False, help='Indicates if this product is non-tax deductible')

    @api.onchange('cabys_code')
    def _cabys_code_changed(self):
        if self.cabys_code:
            url_base = self.company_id.url_base_cabys
            id_product = self.id

            # Valida que existan el campo url_base
            if url_base:
                # Limpia caracteres en blanco en los extremos
                url_base = url_base.strip()

                # Elimina la barra al final de la URL para prevenir error al conectarse
                if url_base[-1:] == '/':
                    url_base = url_base[:-1]

                end_point = url_base + 'codigo=' + self.cabys_code

                headers = {
                    'content-type': 'application/json',
                }

                # Petición GET a la API
                peticion = requests.get(end_point, headers=headers, timeout=10)

                ultimo_mensaje = 'Fecha/Hora: ' + str(datetime.now()) + ', Codigo: ' + str(peticion.status_code) + ', Mensaje: ' + str(peticion._content.decode())
                self.env.cr.execute("UPDATE  res_company SET ultima_respuesta_cabys='%s' WHERE id=%s" % (ultimo_mensaje, self.company_id.id))


                if peticion.status_code == 200:
                    obj_json = peticion.json()
                    if (len(obj_json)) > 0:
                        for etiquetas in obj_json:
                            # Busco los impuestos que puedan utilizarse para FE
                            tax = self.env['account.tax'].search([('type_tax_use', '=', 'sale'),
                                                                  ('amount', '=', float(etiquetas['impuesto'])),
                                                                   ('tax_code','!=',''),
                                                                   ('iva_tax_desc','!=',''),
                                                                   ('iva_tax_code','!=','')], limit=1)
                            # Guardo el impuesto que concuerda mejor para el producto
                            self.taxes_id = tax
                    else:
                        # Por mejorar -> Se debe limpiar el campo de impuestos
                        raise UserError(_('Ocurrió un error al consultar el código: ' + str(self.cabys_code) + ', por favor verifiquelo y vuelva a intentarlo'))
                else:
                    # Por mejorar -> Se debe limpiar el campo de impuestos
                    raise UserError(_('El servicio de Hacienda no está disponible en este momento'))

class ProductCategory(models.Model):
    _inherit = "product.category"

    economic_activity_id = fields.Many2one("economic.activity", string="Actividad Económica", help='Economic activity code from Ministerio de Hacienda')

    cabys_code = fields.Char(string="CAByS Code", help='CAByS code from Ministerio de Hacienda')
