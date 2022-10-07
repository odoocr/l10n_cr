from odoo import models, fields, api, _
from odoo.exceptions import UserError

from xml.sax.saxutils import escape


class InvoiceLineElectronic(models.Model):
    _inherit = "account.move.line"

    # ==============================================================================================
    #                                          INVOICE LINE
    # ==============================================================================================

    discount_note = fields.Char()
    total_tax = fields.Float()
    third_party_id = fields.Many2one(
        comodel_name="res.partner",
        string="Third - other charges"
    )
    tariff_head = fields.Char(
        string="Tariff item for export invoice"
    )
    categ_name = fields.Char(
        related='product_id.categ_id.name'
    )
    product_code = fields.Char(
        related='product_id.default_code'
    )
    economic_activity_id = fields.Many2one(
        comodel_name="economic.activity",
        string="Economic activity",
        store=True,
        context={
            'active_test': False
        },
        default=False
    )
    non_tax_deductible = fields.Boolean(
        string='Indicates if this invoice is non-tax deductible'
    )

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('product_id')
    def product_changed(self):
        # Check if the product is non deductible to use a non_deductible tax
        if self.product_id.non_tax_deductible:
            taxes = []
            self.non_tax_deductible = True
            for tax in self.tax_ids:
                new_tax = self.env['account.tax'].search([('tax_code', '=', tax.tax_code),
                                                          ('amount', '=', tax.amount),
                                                          ('type_tax_use', '=', 'purchase'),
                                                          ('non_tax_deductible', '=', True),
                                                          ('active', '=', True)], limit=1)
                if new_tax:
                    taxes.append((3, tax.id))
                    taxes.append((4, new_tax.id))
                else:
                    raise UserError(_('There is no "Non tax deductible" tax with the tax percentage of this product'))
            self.tax_ids = taxes
        else:
            self.non_tax_deductible = False

        # Check for the economic activity in the product or
        # product category or company respectively (already set in the invoice when partner selected)
        if self.product_id and self.product_id.economic_activity_id:
            self.economic_activity_id = self.product_id.economic_activity_id
        elif self.product_id and self.product_id.categ_id and self.product_id.categ_id.economic_activity_id:
            self.economic_activity_id = self.product_id.categ_id.economic_activity_id
        else:
            self.economic_activity_id = self.move_id.economic_activity_id

    # -------------------------------------------------------------------------
    # TOOLING
    # -------------------------------------------------------------------------

    @api.model
    def _get_default_activity_id(self):
        for line in self:
            line.economic_activity_id = line.product_id and line.product_id.categ_id and \
                line.product_id.categ_id.economic_activity_id and line.product_id.categ_id.economic_activity_id.id

    def _get_electronic_invoice_info(self):
        self.ensure_one()
        total_servicio_salon = 0.0
        total_servicio_gravado = 0.0
        total_servicio_exento = 0.0
        total_servicio_exonerado = 0.0
        total_mercaderia_gravado = 0.0
        total_mercaderia_exento = 0.0
        total_mercaderia_exonerado = 0.0
        total_descuento = 0.0
        total_impuestos = 0.0
        base_subtotal = 0.0
        _no_cabys_code = False
        inv = self.move_id
        currency = self.currency_id
        price = self.price_unit
        quantity = self.quantity
        if not quantity:
            return False, False, False

        line_taxes = self.tax_ids.compute_all(
            price, currency, 1,
            product=self.product_id,
            partner=self.move_id.partner_id)

        price_unit = round(line_taxes['total_excluded'], 5)

        base_line = round(price_unit * quantity, 5)
        descuento = self.discount and round(
            price_unit * quantity * self.discount / 100.0,
            5) or 0.0

        subtotal_line = round(base_line - descuento, 5)

        # Corregir error cuando un producto trae en el nombre "", por ejemplo: "disco duro"
        # Esto no debería suceder, pero, si sucede, lo corregimos
        if self.name[:156].find('"'):
            detalle_linea = self.name[:160].replace(
                '"', '')

        line = {
            "cantidad": quantity,
            "detalle": escape(detalle_linea),
            "precioUnitario": price_unit,
            "montoTotal": base_line,
            "subtotal": subtotal_line,
            "BaseImponible": subtotal_line,
            "unidadMedida": self.product_uom_id and self.product_uom_id.code or 'Sp'
        }

        if self.product_id:
            line["codigo"] = self.product_id.default_code or ''
            line["codigoProducto"] = self.product_id.code or ''

            if self.product_id.cabys_code:
                line["codigoCabys"] = self.product_id.cabys_code
            elif self.product_id.categ_id and self.product_id.categ_id.cabys_code:
                line["codigoCabys"] = self.product_id.categ_id.cabys_code
            elif inv.tipo_documento != 'NC':
                _no_cabys_code = _(f'Warning!.\nLine without CABYS code: {self.name}')
                return False, _no_cabys_code, False
        elif inv.tipo_documento != 'NC':
            _no_cabys_code = _(f'Warning!.\nLine without CABYS code: {self.name}')
            return False, _no_cabys_code, False

        if inv.tipo_documento == 'FEE' and self.tariff_head:
            line["partidaArancelaria"] = self.tariff_head

        if self.discount and price_unit > 0:
            total_descuento += descuento
            line["montoDescuento"] = descuento
            line["naturalezaDescuento"] = self.discount_note or 'Descuento Comercial'

        # Se generan los impuestos
        taxes = dict([])
        _line_tax = 0.0
        _tax_exoneration = False
        _percentage_exoneration = 0
        if self.tax_ids:
            tax_index = 0

            taxes_lookup = {}
            for i in self.tax_ids:
                if i.has_exoneration:
                    _tax_exoneration = True
                    _tax_rate = i.tax_root.amount
                    _tax_exoneration_rate = min(i.percentage_exoneration, _tax_rate)
                    _percentage_exoneration = _tax_exoneration_rate / _tax_rate
                    taxes_lookup[i.id] = {'tax_code': i.tax_root.tax_code,
                                            'tarifa': _tax_rate,
                                            'iva_tax_desc': i.tax_root.iva_tax_desc,
                                            'iva_tax_code': i.tax_root.iva_tax_code,
                                            'exoneration_percentage': _tax_exoneration_rate,
                                            'amount_exoneration': i.amount}
                else:
                    taxes_lookup[i.id] = {'tax_code': i.tax_code,
                                            'tarifa': i.amount,
                                            'iva_tax_desc': i.iva_tax_desc,
                                            'iva_tax_code': i.iva_tax_code}

            for i in line_taxes['taxes']:
                if taxes_lookup[i['id']]['tax_code'] == 'service':
                    total_servicio_salon += round(
                        subtotal_line * taxes_lookup[i['id']]['tarifa'] / 100, 5)

                elif taxes_lookup[i['id']]['tax_code'] != '00':
                    tax_index += 1
                    tax_amount = round(subtotal_line * taxes_lookup[i['id']]['tarifa'] / 100, 5)
                    _line_tax += tax_amount
                    tax = {
                        'codigo': taxes_lookup[i['id']]['tax_code'],
                        'tarifa': taxes_lookup[i['id']]['tarifa'],
                        'monto': tax_amount,
                        'iva_tax_desc': taxes_lookup[i['id']]['iva_tax_desc'],
                        'iva_tax_code': taxes_lookup[i['id']]['iva_tax_code'],
                    }
                    # Se genera la exoneración si existe para este impuesto
                    if _tax_exoneration:
                        exoneration_percentage = taxes_lookup[i['id']]['exoneration_percentage']
                        _tax_amount_exoneration = round(subtotal_line *
                                                        exoneration_percentage / 100, 5)

                        _line_tax -= _tax_amount_exoneration

                        tax["exoneracion"] = {
                            "montoImpuesto": _tax_amount_exoneration,
                            "porcentajeCompra": int(exoneration_percentage)
                        }

                    taxes[tax_index] = tax

            line["impuesto"] = taxes
            line["impuestoNeto"] = round(_line_tax, 5)

        # Si no hay product_uom_id se asume como Servicio
        if not self.product_uom_id or \
            self.product_uom_id.category_id.name in ('Service',
                                                            'Services',
                                                            'Servicio',
                                                            'Servicios'):
            if taxes:
                if _tax_exoneration:
                    if _percentage_exoneration < 1:
                        total_servicio_gravado += (base_line * (1 - _percentage_exoneration))
                    total_servicio_exonerado += (base_line * _percentage_exoneration)

                else:
                    total_servicio_gravado += base_line

                total_impuestos += _line_tax
            else:
                total_servicio_exento += base_line
        else:
            if taxes:
                if _tax_exoneration:
                    if _percentage_exoneration < 1:
                        total_mercaderia_gravado += (base_line * (1 - _percentage_exoneration))
                    total_mercaderia_exonerado += (base_line * _percentage_exoneration)

                else:
                    total_mercaderia_gravado += base_line

                total_impuestos += _line_tax
            else:
                total_mercaderia_exento += base_line

        base_subtotal += subtotal_line

        line["montoTotalLinea"] = round(subtotal_line + _line_tax, 5)

        totales = {
            'total_servicio_salon': total_servicio_salon,
            'total_servicio_gravado': total_servicio_gravado,
            'total_servicio_exento': total_servicio_exento,
            'total_servicio_exonerado': total_servicio_exonerado,
            'total_mercaderia_gravado': total_mercaderia_gravado,
            'total_mercaderia_exento': total_mercaderia_exento,
            'total_mercaderia_exonerado': total_mercaderia_exonerado,
            'total_descuento': total_descuento,
            'total_impuestos': total_impuestos,
            'base_subtotal': base_subtotal,
        }
        return line, _no_cabys_code, totales