class OrderElectronic(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _process_order(self, order):
        super(OrderElectronic, self)._process_order(order)
        if self.company_id.frm_ws_ambiente != 'disabled':
            company_info = self.env.user.company_id
            url = company_info.frm_callback_url
            payload = {}
            headers = {}
            tipo_documento = ''
            FacturaReferencia = ''
            now_utc = datetime.datetime.now(pytz.timezone('UTC'))
            now_cr = now_utc.astimezone(pytz.timezone('America/Costa_Rica'))
            date_cr = now_cr.strftime("%Y-%m-%dT%H:%M:%S-06:00")
            medio_pago = 1
            tipo_documento = 'TE'
            next_number = self.env['ir.sequence'].next_by_code('invoice_hacienda')
            if tipo_documento == 'FE':  # order.number.isdigit() and tipo_documento:
                currency_rate = 1 / order.currency_id.rate
                lines = '{'
                base_total = 0.0
                numero = 0
                indextax = 0
                total_servicio_gravado = 0.0
                total_servicio_exento = 0.0
                total_mercaderia_gravado = 0.0
                total_mercaderia_exento = 0.0
                # get Clave MH
                payload['w'] = 'clave'
                payload['r'] = 'clave'
                if self.company_id.identification_id.id == 1:
                    payload['tipoCedula'] = 'fisico'
                elif self.company_id.identification_id.id == 2:
                    payload['tipoCedula'] = 'juridico'
                payload['tipoDocumento'] = tipo_documento
                payload['cedula'] = self.company_id.vat
                payload['codigoPais'] = self.company_id.phone_code
                payload['consecutivo'] = next_number
                payload['situacion'] = 'normal'
                payload['codigoSeguridad'] = self.company_id.security_code

                response = requests.request("POST", url, data=payload, headers=headers)
                response_json = json.loads(response._content)
                _logger.info('Clave Documento')
                order.number_electronic = response_json.get('resp').get('clave')
                consecutivo = response_json.get('resp').get('consecutivo')

                for inv_line in order.invoice_line_ids:
                    impuestos_acumulados = 0.0
                    numero += 1
                    base_total += inv_line.price_unit * inv_line.quantity
                    impuestos = '{'
                    for i in inv_line.invoice_line_tax_ids:
                        indextax += 1
                        if i.tax_code != '00':
                            monto_impuesto = round(i.amount / 100 * inv_line.price_subtotal, 2)
                            impuestos = (impuestos + '"' + str(indextax) + '":' + '{"codigo": "'
                                         + str(i.tax_code or '01') + '",' + '"tarifa": "' + str(i.amount) + '",' +
                                         '"monto": "' + str(monto_impuesto))
                            if inv_line.exoneration_id:
                                monto_exonerado = round(
                                    monto_impuesto * inv_line.exoneration_id.percentage_exoneration / 100)
                                impuestos = (impuestos + ', ' +
                                             '"exoneracion": {'
                                             '"tipoDocumento": "' + inv_line.exoneration_id.type + '",' +
                                             '"numeroDocumento": "' + str(
                                            inv_line.exoneration_id.exoneration_number) + '",' +
                                             '"nombreInstitucion": "' + inv_line.exoneration_id.name_institution + '",' +
                                             '"fechaEmision": "' + str(inv_line.exoneration_id.date) + '",' +
                                             '"montoImpuesto": " -' + monto_exonerado + '",' +
                                             '"porcentajeCompra": "' + str(
                                            inv_line.exoneration_id.percentage_exoneration) + '"}')
                            impuestos_acumulados += round(i.amount / 100 * inv_line.price_subtotal, 2)
                            impuestos = impuestos + '"},'
                    impuestos = impuestos[:-1] + '}'
                    indextax = 0
                    if inv_line.product_id:
                        if inv_line.product_id.type == 'service':
                            if impuestos_acumulados:
                                total_servicio_gravado += inv_line.quantity * inv_line.price_unit
                            else:
                                total_servicio_exento += inv_line.quantity * inv_line.price_unit
                        else:
                            if impuestos_acumulados:
                                total_mercaderia_gravado += inv_line.quantity * inv_line.price_unit
                            else:
                                total_mercaderia_exento += inv_line.quantity * inv_line.price_unit
                    else:  # se asume que si no tiene producto setrata como un type product
                        if impuestos_acumulados:
                            total_mercaderia_gravado += inv_line.quantity * inv_line.price_unit
                        else:
                            total_mercaderia_exento += inv_line.quantity * inv_line.price_unit
                    unidad_medida = inv_line.product_id.commercial_measurement or 'Sp'
                    total = inv_line.quantity * inv_line.price_unit
                    total_linea = inv_line.price_subtotal + impuestos_acumulados
                    descuento = (round(inv_line.quantity * inv_line.price_unit, 2)
                                 - round(inv_line.price_subtotal, 2)) or 0
                    natu_descuento = inv_line.discount_note or ''
                    _logger.info(impuestos)
                    line = ('{' +
                            '"cantidad": "' + str(int(inv_line.quantity)) + '",' +
                            '"unidadMedida": "' + unidad_medida + '",' +
                            '"detalle": "' + inv_line.product_id.display_name + '",' +
                            '"precioUnitario": "' + str(inv_line.price_unit) + '",' +
                            '"montoTotal": "' + str(total) + '",' +
                            '"subtotal": "' + str(inv_line.price_subtotal) + '",')
                    if descuento != 0:
                        line = (line + '"montoDescuento": "' + str(descuento) + '",' +
                                '"naturalezaDescuento": "' + natu_descuento + '",')
                    line = (line + '"impuesto": ' + str(impuestos) + ',' +
                            '"montoTotalLinea": "' + str(total_linea) + '"' +
                            '}'
                            )

                    lines = lines + '"' + str(numero) + '":' + line + ","
                lines = lines[:-1] + "}"
                payload = {}
                # Generar FE payload
                payload['w'] = 'genXML'
                if tipo_documento == 'FE':
                    payload['r'] = 'gen_xml_fe'
                elif tipo_documento == 'NC':
                    payload['r'] = 'gen_xml_nc'
                payload['clave'] = self.number_electronic
                payload['consecutivo'] = consecutivo
                payload['fecha_emision'] = date_cr
                payload['emisor_nombre'] = self.company_id.name
                payload['emisor_tipo_indetif'] = self.company_id.identification_id.code
                payload['emisor_num_identif'] = self.company_id.vat
                payload['nombre_comercial'] = self.company_id.commercial_name or ''
                payload['emisor_provincia'] = self.company_id.state_id.code
                payload['emisor_canton'] = self.company_id.county_id.code
                payload['emisor_distrito'] = self.company_id.district_id.code
                payload['emisor_barrio'] = self.company_id.neighborhood_id.code
                payload['emisor_otras_senas'] = self.company_id.street
                payload['emisor_cod_pais_tel'] = self.company_id.phone_code
                payload['emisor_tel'] = self.company_id.phone
                payload['emisor_cod_pais_fax'] = ''
                payload['emisor_fax'] = ''
                payload['emisor_email'] = self.company_id.email
                payload['receptor_nombre'] = self.partner_id.name[:80]
                payload['receptor_tipo_identif'] = self.partner_id.identification_id.code
                payload['receptor_num_identif'] = self.partner_id.vat
                payload['receptor_provincia'] = self.partner_id.state_id.code
                payload['receptor_canton'] = self.partner_id.county_id.code
                payload['receptor_distrito'] = self.partner_id.district_id.code
                payload['receptor_barrio'] = self.partner_id.neighborhood_id.code
                payload['receptor_cod_pais_tel'] = self.partner_id.phone_code
                payload['receptor_tel'] = self.partner_id.phone
                payload['receptor_cod_pais_fax'] = ''
                payload['receptor_fax'] = ''
                payload['receptor_email'] = self.partner_id.email
                payload['condicion_venta'] = sale_conditions
                payload['plazo_credito'] = ''
                payload['medio_pago'] = medio_pago
                payload['cod_moneda'] = self.currency_id.name
                payload['tipo_cambio'] = 1
                payload['total_serv_gravados'] = total_servicio_gravado
                payload['total_serv_exentos'] = total_servicio_exento
                payload['total_merc_gravada'] = total_mercaderia_gravado
                payload['total_merc_exenta'] = total_mercaderia_exento
                payload['total_gravados'] = total_servicio_gravado + total_mercaderia_gravado
                payload['total_exentos'] = total_servicio_exento + total_mercaderia_exento
                payload['total_ventas'] = total_servicio_gravado + total_mercaderia_gravado + total_servicio_exento + total_mercaderia_exento
                payload['total_descuentos'] = round(base_total, 2) - round(self.amount_untaxed, 2)
                payload['total_ventas_neta'] = (total_servicio_gravado + total_mercaderia_gravado
                                                + total_servicio_exento + total_mercaderia_exento) \
                                               - (base_total - self.amount_untaxed)
                payload['total_impuestos'] = self.amount_tax
                payload['total_comprobante'] = self.amount_total
                payload['otros'] = ''
                payload['detalles'] = lines

                response = requests.request("POST", url, data=payload, headers=headers)
                response_json = json.loads(response._content)
                _logger.info('XML Sin Firmar')

                # firmar Comprobante
                payload = {}
                payload['w'] = 'signXML'
                payload['r'] = 'signFE'
                payload['p12Url'] = self.company_id.frm_apicr_signaturecode
                payload['inXml'] = response_json.get('resp').get('xml')
                payload['pinP12'] = self.company_id.frm_pin
                payload['tipodoc'] = tipo_documento

                response = requests.request("POST", url, data=payload, headers=headers)
                response_json = json.loads(response._content)
                xml_firmado = response_json.get('resp').get('xmlFirmado')
                _logger.info('Firmado XML')

                # validar XML
                '''payload = {}
                payload['xml'] = xmlFirmado
                payload['type'] = 'AUTO'
                response = requests.request("POST", 'https://apis.gometa.org/validar/', data=payload,
                                            headers=headers)
                textlength = response.text.find('</pre>') + 6
                responsejson = json.loads(response._content[textlength:])
                _logger.info('Validacion gometa.org')
                if responsejson.get('xsd_result') == 'NOT_VALID':
                    errorsjson = responsejson.get('xsd_errors')
                    errors = ''
                    _logger.info(errorsjson)
                    for error in errorsjson:
                        errors = errors + "Linea: " + error.get('linea') + " Error: " + error.get('error')
                        errors = errors + "\n"

                    raise UserError(
                        'La factura no es valida por los siguientes errores \n' + errors
                    )'''

                if self.company_id.frm_ws_ambiente == 'stag':
                    env = 'api-stag'
                else:
                    env = 'api-prod'
                # get token
                payload = {}
                payload['w'] = 'token'
                payload['r'] = 'gettoken'
                payload['grant_type'] = 'password'
                payload['client_id'] = env
                payload['username'] = self.company_id.frm_ws_identificador
                payload['password'] = self.company_id.frm_ws_password

                response = requests.request("POST", url, data=payload, headers=headers)
                response_json = json.loads(response._content)
                _logger.info('Token MH')
                token_m_h = response_json.get('resp').get('access_token')

                payload = {}
                payload['w'] = 'send'
                payload['r'] = 'json'
                payload['token'] = token_m_h
                payload['clave'] = self.number_electronic
                payload['fecha'] = date_cr
                payload['emi_tipoIdentificacion'] = self.company_id.identification_id.code
                payload['emi_numeroIdentificacion'] = self.company_id.vat
                payload['recp_tipoIdentificacion'] = self.partner_id.identification_id.code
                payload['recp_numeroIdentificacion'] = self.partner_id.vat
                payload['comprobanteXml'] = xml_firmado
                payload['client_id'] = env

                response = requests.request("POST", url, data=payload, headers=headers)
                response_json = json.loads(response._content)

                if response_json.get('resp').get('Status') == 202:
                    payload = {}
                    payload['w'] = 'consultar'
                    payload['r'] = 'consultarCom'
                    payload['client_id'] = env
                    payload['token'] = token_m_h
                    payload['clave'] = self.number_electronic
                    response = requests.request("POST", url, data=payload, headers=headers)
                    response_json = json.loads(response._content)
                    estado_m_h = response_json.get('resp').get('ind-estado')

                    _logger.error('MAB - MH response:%s', response_json)

                    if estado_m_h == 'aceptado':
                        self.state_tributacion = estado_m_h
                        self.date_issuance = date_cr
                        self.fname_xml_respuesta_tributacion = 'respuesta_' + self.number_electronic + '.xml'
                        self.xml_respuesta_tributacion = response_json.get('resp').get('respuesta-xml')
                        self.fname_xml_comprobante = 'comprobante_' + self.number_electronic + '.xml'
                        self.xml_comprobante = xml_firmado
                        if not self.partner_id.opt_out:
                            email_template = self.env.ref('account.email_template_edi_selfoice', False)
                            attachment = self.env['ir.attachment'].search(
                                [('res_model', '=', 'account.selfoice'), ('res_id', '=', self.id),
                                 ('res_field', '=', 'xml_comprobante')], limit=1)
                            attachment.name = self.fname_xml_comprobante
                            attachment.datas_fname = self.fname_xml_comprobante
                            email_template.attachment_ids = [(6, 0, [attachment.id])]  # [(4, attachment.id)]
                            email_template.with_context(type='binary', default_type='binary').send_mail(self.id,
                                                                                                        raise_exception=False,
                                                                                                        force_send=True)  # default_type='binary'
                            email_template.attachment_ids = [(3, attachment.id)]
                    elif estado_m_h == 'recibido':
                        self.state_tributacion = estado_m_h;
                        self.date_issuance = date_cr
                        self.fname_xml_comprobante = 'comprobante_' + self.number_electronic + '.xml'
                        self.xml_comprobante = xml_firmado
                    elif estado_m_h == 'procesando':
                        self.state_tributacion = estado_m_h;
                        self.date_issuance = date_cr
                        self.fname_xml_comprobante = 'comprobante_' + self.number_electronic + '.xml'
                        self.xml_comprobante = xml_firmado
                    elif estado_m_h == 'rechazado':
                        self.state_tributacion = estado_m_h;
                        self.date_issuance = date_cr
                        self.fname_xml_comprobante = 'comprobante_' + self.number_electronic + '.xml'
                        self.xml_comprobante = xml_firmado
                        self.fname_xml_respuesta_tributacion = 'respuesta_' + self.number_electronic + '.xml'
                        self.xml_respuesta_tributacion = response_json.get('resp').get('respuesta-xml')
                    elif estado_m_h == 'error':
                        self.state_tributacion = estado_m_h
                        self.date_issuance = date_cr
                        self.fname_xml_comprobante = 'comprobante_' + self.number_electronic + '.xml'
                        self.xml_comprobante = xml_firmado
                    else:
                        raise UserError('No se pudo Crear la factura electrónica: \n' + str(response_json))
                else:
                    raise UserError(
                        'No se pudo Crear la factura electrónica: \n' + str(response_json.get('resp').get('text')))
