

from datetime import datetime, timedelta

import phonenumbers

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from . import api_facturae

_TIPOS_CONFIRMACION = (
    # Provides listing of types of comprobante confirmations
    ('CCE_sequence_id', 'account.invoice.supplier.accept.',
     'Supplier invoice acceptance sequence'),
    ('CPCE_sequence_id', 'account.invoice.supplier.partial.',
     'Supplier invoice partial acceptance sequence'),
    ('RCE_sequence_id', 'account.invoice.supplier.reject.',
     'Supplier invoice rejection sequence'),
    ('FEC_sequence_id', 'account.invoice.supplier.reject.',
     'Supplier electronic purchase invoice sequence'),
)


class CompanyElectronic(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'mail.thread', ]

    commercial_name = fields.Char()
    legal_name = fields.Char(string="Nombre Legal")
    activity_id = fields.Many2one("economic.activity",
                                  string="Default economic activity",
                                  context={'active_test': False})
    signature = fields.Binary(string="Cryptographic Key", )
    date_expiration_sign = fields.Datetime(string="Due date", default='1985-08-28 00:00:00')
    range_days = fields.Integer(string='Days range', default=5)
    send_user_ids = fields.Many2many('res.users', 'res_company_res_sendusers_rel', string='Users')
    to_emails = fields.Char(string='Email')

    identification_id = fields.Many2one("identification.type", string="Id Type")
    frm_ws_identificador = fields.Char(string="Electronic invoice user")
    frm_ws_password = fields.Char(string="Electronic invoice password")

    frm_ws_ambiente = fields.Selection(selection=[('disabled', 'Deshabilitado'),
                                                  ('api-stag', 'Pruebas'),
                                                  ('api-prod', 'Producción')],
                                       string="Environment",
                                       required=True,
                                       default='disabled',
                                       help='Es el ambiente en al cual se le está actualizando el certificado. '
                                       'Para el ambiente de calidad (stag), para el ambiente de producción (prod). '
                                       'Requerido.')

    frm_pin = fields.Char(string="Pin", help='Es el pin correspondiente al certificado. Requerido')

    sucursal_MR = fields.Integer(string="Sucursal para secuencias de MRs", default="1")

    terminal_MR = fields.Integer(string="Terminal para secuencias de MRs", default="1")

    CCE_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia Aceptación',
        help='Secuencia de confirmacion de aceptación de comprobante electrónico. Dejar en blanco '
        'y el sistema automaticamente se lo creará.',
        readonly=False, copy=False,
    )

    CPCE_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia Parcial',
        help='Secuencia de confirmación de aceptación parcial de comprobante electrónico. Dejar '
        'en blanco y el sistema automáticamente se lo creará.',
        readonly=False, copy=False,
    )
    RCE_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia Rechazo',
        help='Secuencia de confirmación de rechazo de comprobante electrónico. Dejar '
        'en blanco y el sistema automáticamente se lo creará.',
        readonly=False, copy=False,
    )
    FEC_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Secuencia de Facturas Electrónicas de Compra',
        readonly=False, copy=False,
    )

    invoice_qr_type = fields.Selection([('by_url', 'Invoice Url'), ('by_info', 'Invoice Text Information')],
                                       default='by_url',
                                       required=True)
    invoice_field_ids = fields.One2many('invoice.qr.fields',
                                        'company_id',
                                        string="Invoice Field's")

    # Se agrega campos para consultar información de exoneraciones
    ultima_respuesta_exo = fields.Text(string="Last API EXONET Response",
                                       help="Last API EXONET Response, this allows debugging errors if they exist")
    url_base_exo = fields.Char(string="URL Base EXONET", help="URL Base ENDPOINT EXONET",
                               default="https://api.hacienda.go.cr/fe/ex?")

    @api.constrains('invoice_qr_type', 'invoice_field_ids')
    def check_invoice_field_ids(self):
        if self.invoice_qr_type == 'by_info' and not self.invoice_field_ids:
            raise UserError(_("Please Add Invoice Field's"))

    @api.onchange('phone')
    def _onchange_phone(self):
        if self.phone:
            phone = phonenumbers.parse(self.phone, self.country_id.code)
            valid = phonenumbers.is_valid_number(phone)
            if not valid:
                alert = {
                    'title': 'Atención',
                    'message': 'Número de teléfono inválido'
                }
                return {'value': {'phone': ''}, 'warning': alert}

    @api.model
    def create(self, vals):
        """ Try to automatically add the Comprobante Confirmation sequence to the company.
            It will attempt to create and assign before storing. The sequence that is
            created will be coded with the following syntax:
                account.invoice.supplier.<tipo>.<company_name>
            where tipo is: accept, partial or reject, and company_name is either the first word
            of the name or commercial name.
        """
        new_comp_id = super().create(vals)
        # new_comp = self.browse(new_comp_id)
        new_comp_id.try_create_configuration_sequences()
        return new_comp_id

    def write(self, vals):
        if vals.get('date_expiration_sign') or vals.get('range_days'):
            cron = self.env.ref('cr_electronic_invoice.ir_cron_send_expiration_notice', False)

            if not self.range_days:
                return super().write(vals)

            date_expiration_sign = vals.get('date_expiration_sign') and \
                vals['date_expiration_sign'] or self.date_expiration_sign
            # date_expiration_sign = vals.get('date_expiration_sign') and \
            #     datetime.strptime(vals['date_expiration_sign'], '%Y-%m-%d %H:%M:%S') or self.date_expiration_sign
            if date_expiration_sign:
                if isinstance(date_expiration_sign, str):
                    date_expiration_sign = datetime.strptime(date_expiration_sign, '%Y-%m-%d %H:%M:%S')

            range_days = vals.get('range_days') or self.range_days
            next_call = date_expiration_sign - timedelta(days=range_days)
            new_values = {
                'nextcall': next_call
            }

            cron.write(new_values)

        return super().write(vals)

    def get_days_left(self):
        today = datetime.today()
        date_due = self.date_expiration_sign
        range_days = date_due - today

        return range_days.days

    def get_message_to_send(self):
        days_left = self.get_days_left()

        message = ''
        if days_left >= 0:
            message = f'Su llave criptográfica está a punto de expirar, le quedan {days_left} día(s)'
        else:
            message = f'No podrá validar porque su llave criptográfica expiró hace {abs(days_left)} día(s)'

        return message

    def _cron_send_email_notifications(self):
        today = datetime.now()
        date_due = self.env.user.company_id.date_expiration_sign
        range_day = self.env.user.company_id.range_days

        range_date = date_due - timedelta(days=range_day)
        if today >= range_date:
            template = self.env.ref('cr_electronic_invoice.email_template_edi_expiration_notice', False)

            template_values = {
                'email_to': '${object.email|safe}',
                'email_cc': False,
                'auto_delete': True,
                'partner_to': False,
                'scheduled_date': False,
            }

            template.write(template_values)

            for user in self.env.user.company_id.send_user_ids:
                if user.email:
                    template.with_context(lang=user.lang).send_mail(user.id, force_send=True, raise_exception=True)

    def try_create_configuration_sequences(self):
        """ Try to automatically add the Comprobante Confirmation sequence to the company.
            It will first check if sequence already exists before attempt to create. The s
            equence is coded with the following syntax:
                account.invoice.supplier.<tipo>.<company_name>
            where tipo is: accept, partial or reject, and company_name is either the first word
            of the name or commercial name.
        """
        company_subname = self.commercial_name
        if not company_subname:
            company_subname = getattr(self, 'name')
        company_subname = company_subname.split(' ')[0].lower()
        ir_sequence = self.env['ir.sequence']
        to_write = {}
        for field, seq_code, seq_name in _TIPOS_CONFIRMACION:
            if not getattr(self, field, None):
                seq_code += company_subname
                seq = self.env.ref(seq_code, raise_if_not_found=False) or ir_sequence.create({
                    'name': seq_name,
                    'code': seq_code,
                    'implementation': 'standard',
                    'padding': 10,
                    'use_date_range': False,
                    'company_id': getattr(self, 'id'),
                })
                to_write[field] = seq.id

        if to_write:
            self.write(to_write)

    def test_get_token(self):
        self.get_expiration_date()
        token_m_h = api_facturae.get_token_hacienda(
            self.env.user, self.frm_ws_ambiente)
        if token_m_h:
            self.message_post(
                subject=_('Info'),
                body=_("Token Correcto"))
        else:
            self.message_post(
                subject=_('Error'),
                body=_("Datos Incorrectos"))

    def get_expiration_date(self):
        if self.signature and self.frm_pin:
            self.date_expiration_sign = api_facturae.p12_expiration_date(self.signature, self.frm_pin)
        else:
            self.message_post(
                subject=_('Error'),
                body=_("Signature requerido"))

    def action_get_economic_activities(self):
        if self.vat:
            json_response = api_facturae.get_economic_activities(self)

            self.env.cr.execute('update economic_activity set active=False')

            self.message_post(subject=_('Actividades Económicas'),
                              body=_('Aviso!.\n Cargando actividades económicas desde Hacienda'))

            if json_response["status"] == 200:
                activities = json_response["activities"]
                activities_codes = list([])
                for activity in activities:
                    if activity["estado"] == "A":
                        activities_codes.append(activity["codigo"])

                economic_activities = self.env['economic.activity'].with_context(active_test=False).search([
                    ('code', 'in', activities_codes)])

                for activity in economic_activities:
                    activity.active = True

                self.legal_name = json_response["name"]
            else:
                alert = {
                    'title': json_response["status"],
                    'message': json_response["text"]
                }
                return {'value': {'vat': ''}, 'warning': alert}
        else:
            alert = {
                'title': 'Atención',
                'message': _('Company VAT is invalid')
            }
            return {'value': {'vat': ''}, 'warning': alert}
