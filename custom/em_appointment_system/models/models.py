import math

import pytz

from odoo import models, fields, api, _
from datetime import datetime
from datetime import timedelta

from odoo.exceptions import ValidationError, UserError
from odoo.http import request
from babel.dates import format_datetime
from dateutil.relativedelta import relativedelta
import calendar as cal
from odoo.tools.misc import get_lang

import logging

_logger = logging.getLogger(__name__)


class EmAppointments(models.Model):
    _name = 'em.appointment.user'
    _rec_name = 'user_id'
    _description = "Appointment User Dashboard"

    user_id = fields.Many2one('res.users')

    def appointment_system_form_view(self):
        self.ensure_one()
        action_xmlid = 'em_appointment_system.em_appointment_system_user'
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.user_id.name
        context = {
            'default_user_id': self.user_id.id,
        }
        context = {**context}
        action['domain'] = [('user_id', '=', self.env.user.id)]
        action['context'] = context
        action['help'] = """<p class="o_view_nocontent_smiling_face">
                          There are no appointments!
                      </p>"""
        return action

    def appointment_system_form_view_today(self):
        self.ensure_one()
        action_xmlid = 'em_appointment_system.em_appointment_system_user'
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.user_id.name
        context = {
            'default_user_id': self.user_id.id,
        }
        context = {**context}
        action['context'] = context
        action['domain'] = [('user_id', '=', self.env.user.id), ('date', '=', datetime.today().date()), ]
        action['help'] = """<p class="o_view_nocontent_smiling_face">
                    There are no appointments for today!
                </p>"""
        return action

    def appointment_system_form_view_next(self):
        self.ensure_one()
        action_xmlid = 'em_appointment_system.em_appointment_system_user'
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.user_id.name
        context = {
            'default_user_id': self.user_id.id,
        }
        context = {**context}
        action['context'] = context
        action['domain'] = [('user_id', '=', self.env.user.id), ('date', '>=', datetime.today().date()), ]
        action['help'] = """<p class="o_view_nocontent_smiling_face">
                           You do not have any upcoming appointments for next days!
                       </p>"""
        return action

    def appointment_system_list_view_draft(self):
        self.ensure_one()
        action_xmlid = 'em_appointment_system.em_appointment_system_user'
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.user_id.name
        context = {
            'default_user_id': self.user_id.id,
        }

        context = {**context}
        context.update({'search_default_user_id': self.user_id.id})
        action['context'] = context
        action['domain'] = [('state', '=', 'draft')]
        action['help'] = """<p class="o_view_nocontent_smiling_face">
                                  You do not have any  appointment in draft state!
                              </p>"""
        return action

    def appointment_system_list_view_confirm(self):
        self.ensure_one()
        action_xmlid = 'em_appointment_system.em_appointment_system_user'
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.user_id.name
        context = {
            'default_user_id': self.user_id.id,
        }
        context = {**context}
        context.update({'search_default_user_id': self.user_id.id})
        action['context'] = context
        action['domain'] = [('state', '=', 'confirm')]
        action['help'] = """<p class="o_view_nocontent_smiling_face">
                                     You do not have any confirmed appointment!
                                 </p>"""
        return action

    def appointment_system_list_view_expire(self):
        self.ensure_one()
        action_xmlid = 'em_appointment_system.em_appointment_system_user'
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.user_id.name
        context = {
            'default_user_id': self.user_id.id,
        }

        context = {**context}
        context.update({'search_default_user_id': self.user_id.id})
        action['context'] = context
        action['domain'] = [('state', '=', 'expire')]
        action['help'] = """<p class="o_view_nocontent_smiling_face">
                                          You do not have any expired appointment!
                                      </p>"""
        return action

    def appointment_system_list_view_close(self):
        self.ensure_one()
        action_xmlid = 'em_appointment_system.em_appointment_system_user'
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.user_id.name
        context = {
            'default_user_id': self.user_id.id,
        }

        context = {**context}
        context.update({'search_default_user_id': self.user_id.id})
        action['context'] = context
        action['domain'] = [('state', '=', 'done')]
        action['help'] = """<p class="o_view_nocontent_smiling_face">
                                          You do not have any completed appointment!
                                      </p>"""
        return action


class AppointmentType(models.Model):
    _name = 'appointment.type'
    _description = "Appointment Type"

    name = fields.Char(required=True)
    address_need = fields.Boolean()
    partner_id = fields.Many2one('res.partner')


class EmAppointmentSystem(models.Model):
    _name = 'em.appointment.system'
    _inherit = ['portal.mixin', 'mail.thread']
    _order = "id desc"
    _description = "Appointment"

    def _compute_access_url(self):
        super(EmAppointmentSystem, self)._compute_access_url()
        for appointment in self:
            appointment.access_url = '/my/appointment/%s' % (appointment.id)

    @api.model
    def default_get(self, default_fields):

        values = super(EmAppointmentSystem, self).default_get(default_fields)
        if self.env.user.partner_id.app_user:
            values['designation_id'] = \
                self.env.user.partner_id.designation_id and self.env.user.partner_id.designation_id.id
            values['user_id'] = self.env.user and self.env.user.id
            values['self_created'] = True
        return values

    name = fields.Char(string='Ref.#', default='New', required=True, readonly=1)
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirm'), ('expire', 'Expired'), ('done', 'Done'), ('cancel', 'Cancel')],
        default='draft', string="Status")
    self_created = fields.Boolean()
    designation_id = fields.Many2one('designation.designation', ondelete="restrict", string = "Resident Type")
    day_of_week_id = fields.Many2one('day.of.week', string="Week Day", ondelete="restrict")
    slot_of_time_id = fields.Many2one('slot.of.time', ondelete="restrict")
    user_id = fields.Many2one('res.users', required=True, domain=[('partner_id.app_user', '=', True)],
                              string="Resident")
    partner_id = fields.Many2one('res.partner', string='Booked By', required=True)
    appointment_type_id = fields.Many2one('appointment.type', required=True, ondelete="restrict", string="Visit Type")
    client = fields.Char(string='Client Name')
    reason = fields.Text(required=False, string="Remarks")
    date = fields.Date(required=True)
    date_time = fields.Datetime(compute='_compute_date_time', string="Visit Date", store=True)
    canceled_by_user = fields.Boolean()
    location_address = fields.Text(compute="_compute_location_address")
    currency_id = fields.Many2one('res.currency', compute="_compute_location_address")
    amount = fields.Monetary(compute="_compute_location_address", string="Fee")
    display_name = fields.Char('Display Name', compute="_compute_display_name")
    url = fields.Char(compute='get_url')
    invoice_id = fields.Many2one("account.move")
    invoice_count = fields.Integer(string='Invoice Count', compute='_get_invoiced', readonly=True)
    invoice_ids = fields.Many2many("account.move", string='Invoices', compute="_get_invoiced", readonly=True,
                                   copy=False, search="_search_invoice_ids")
    payment_state = fields.Selection(selection=[
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy')],
        string="Payment Status", store=True,
        compute='_compute_payment_state')
    show_address = fields.Boolean()
    enable_additional_item = fields.Boolean()
    additional_item_line_ids = fields.One2many("appointment.additional.item", 'appointment_id')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    order_count = fields.Integer(string='Sale Order Count', compute='_get_invoiced', readonly=True)

    def unlink(self):
        for appointment in self:
            if appointment.state not in ('draft', 'cancel', 'done'):
                raise UserError(
                    _('You can not delete a sent appointment or a confirmed appointment. You must first cancel it.'))
        return super(EmAppointmentSystem, self).unlink()

    def format_date(self):
        date_format = self.env['res.lang']._lang_get(self.env.user.lang).date_format
        date_start = self.date.strftime(date_format or "%Y/%m/%d_%H:%M:%S")
        return date_start

    def appoint_cancel(self):
        appointment_system_ids = self.env["em.appointment.system"].browse(self._context.get("active_ids"))
        for appointment_system_id in appointment_system_ids:
            template_id = self.env.ref('em_appointment_system.canceled_email_template_appointment_system_order').id
            template = self.env['mail.template'].browse(template_id)
            partners = [appointment_system_id.partner_id.id]

            email_values = {'recipient_ids': partners}
            template.browse(template_id).send_mail(appointment_system_id.id, force_send=True, email_values=email_values)
            appointment_system_id.canceled_by_user = True
            appointment_system_id.cancel()

    @api.depends('date', 'slot_of_time_id', "user_id")
    def _compute_date_time(self):
        for rec in self:
            dt = str(rec.date)
            tm = str('{0:02.0f}:{1:02.0f}'.format(*divmod(rec.slot_of_time_id.time_from * 60, 60)))
            d_t = dt + " " + tm
            datetime_object = datetime.strptime(d_t, '%Y-%m-%d %H:%M')
            tz = self.user_id.tz
            if tz:
                datetime_object = pytz.timezone(tz).localize(datetime_object).astimezone(pytz.UTC).replace(tzinfo=None)
            rec.date_time = datetime_object

    def appointment_local_time(self):
        if self.date_time:
            tz = self.user_id.tz
            date_format = self.env['res.lang']._lang_get(self.env.user.lang).date_format
            time_format = self.env['res.lang']._lang_get(self.env.user.lang).time_format

            if tz:
                user_time_zone = pytz.timezone(tz)
                date_time = pytz.utc.localize(self.date_time).astimezone(user_time_zone).replace(tzinfo=None)
                return date_time.strftime(date_format + " " + time_format or "%Y/%m/%d %H:%M:%S")
            return self.date_time.strftime(date_format + " " + time_format or "%Y/%m/%d %H:%M:%S")

    @api.depends('invoice_id.payment_state')
    def _compute_payment_state(self):
        for rec in self:
            if rec.invoice_id:
                rec.payment_state = rec.invoice_id.payment_state
            else:
                rec.payment_state = False

    def cancel(self):
        self.state = 'cancel'
        self.slot_of_time_id = False
        self.day_of_week_id = False
        for invoice in self.invoice_ids:
            if invoice.state == 'posted' and invoice.payment_state == 'not_paid':
                invoice.button_draft()
                invoice.button_cancel()

    def expire(self):
        for rec in self:
            rec.state = 'expire'
            for invoice in rec.invoice_ids:
                if invoice.state == 'posted' and invoice.payment_state == 'not_paid':
                    invoice.button_draft()
                    invoice.button_cancel()

    def close(self):
        self.state = 'done'

    def pay_amount(self):
        if self.invoice_id:
            return self.invoice_id.preview_invoice()

    def _get_report_base_filename(self):
        return self.name

    def appointment_reminder_ir_cron(self):
        ircsudo = self.env['ir.config_parameter'].sudo()
        allow_reminder_to_partner = ircsudo.get_param('em_appointment_system.allow_reminder_to_partner')
        old_appointments = self.env['em.appointment.system'].sudo().search(
            [('date_time', '<=', datetime.today()), ('state', 'not in', ['done', 'expire', 'cancel'])])
        old_appointments.expire()
        if allow_reminder_to_partner:
            template_id = self.env.ref('em_appointment_system.customer_email_template_appointment_system_order').id
            template = self.env['mail.template'].browse(template_id)
            appointment_ids = self.env['em.appointment.system'].sudo().search([('date', '=', datetime.today().date())])
            template.subject += ' reminder'
            for appointment_id in appointment_ids:
                partners = []
                partners.append(appointment_id.partner_id.id)
                if partners:
                    email_values = {'recipient_ids': partners}
                    template.browse(template_id).send_mail(appointment_id.id, force_send=True,
                                                           email_values=email_values)

    def manual_mail(self):
        template_id = self.env.ref('em_appointment_system.customer_email_template_appointment_system_order').id
        template = self.env['mail.template'].sudo().browse(template_id)
        template.subject = self.name + ' Reply to ' + ' (' + self.partner_id.name + ')'
        template.email_from = self.env.user.sudo().partner_id.email
        template.email_to = self.partner_id.email
        ctx = {
            'default_model': 'em.appointment.system',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template.id),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': 'comment',
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def _create_invoice(self):
        product_id = self.env.ref('em_appointment_system.product_product_appoint_fee')
        move_id = False
        if not self.invoice_id:
            move_id = self.env['account.move'].sudo().create({
                'move_type': 'out_invoice',
                'date': datetime.now(),
                'partner_id': self.partner_id.id,
                'currency_id': self.currency_id.id,
                'appointment_system_id': self.id,
                'invoice_date': datetime.now().date(),
                'invoice_date_due': datetime.now().date(),
                'invoice_user_id': self.user_id.id,
                'invoice_line_ids': [
                    (0, 0, {'product_id': product_id.id, 'quantity': 1, 'price_unit': self.amount})],
            })
            move_id.action_post()
            self.invoice_id = move_id.id
        return move_id

    def action_confirm(self, website=False):
        if website == False: self.state = 'confirm'
        self.name = self.env['ir.sequence'].sudo().next_by_code('eas.sequence')
        if not website:
            self._create_invoice()

        ircsudo = self.env['ir.config_parameter'].sudo()
        allow_mail_to_user = ircsudo.get_param('em_appointment_system.allow_mail_to_user')
        allow_mail_to_partner = ircsudo.get_param('em_appointment_system.allow_mail_to_partner')
        if not self.env['em.appointment.user'].sudo().search([('user_id', '=', self.user_id.id)]):
            app_user_id = self.env['em.appointment.user'].sudo().create({
                'user_id': self.user_id.id
            })

        if allow_mail_to_partner:
            template_id = self.env.ref('em_appointment_system.customer_email_template_appointment_system_order').id
            template = self.env['mail.template'].sudo().browse(template_id)
            partner = [self.partner_id.id]
            email_values = {'recipient_ids': partner}
            template.browse(template_id).send_mail(self.id, force_send=True, email_values=email_values)
        if allow_mail_to_user:
            template_id = self.env.ref('em_appointment_system.appointee_email_template_appointment_system_order').id
            template = self.env['mail.template'].sudo().browse(template_id)
            partner = [self.user_id.sudo().partner_id.id]
            email_values = {'recipient_ids': partner}
            template.browse(template_id).send_mail(self.id, force_send=True, email_values=email_values)

    def get_url(self):
        url = request.httprequest.host_url
        db = self.env.cr.dbname
        if self.id:
            self.url = url + 'web#id=' + str(
                self.id) + '&db=' + db + '&model=em.appointment.system&view_type=form'
        else:
            self.url = False

    @api.onchange('partner_id')
    def _get_invoiced(self):
        for rec in self:
            invoices = self.env['account.move'].sudo().search([('appointment_system_id', '=', rec.id)])
            orders = self.env['sale.order'].sudo().search([('appointment_id', '=', rec.id)])
            if invoices:
                rec.invoice_count = len(invoices)
                rec.order_count = len(orders)
                rec.invoice_ids = invoices
            else:
                rec.invoice_count = 0
                rec.order_count = 0

    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env["ir.actions.actions"].sudo()._for_xml_id("account.action_move_out_invoice_type")
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_invoice_payment_term_id': self.env['account.move'].sudo().default_get(
                    ['invoice_payment_term_id']).get('invoice_payment_term_id'),
            })
        action['context'] = context
        return action

    def action_view_sale_order(self):

        return {
            'type': 'ir.actions.act_window',
            'name': "Appointment Additional Items Orders",
            'view_mode': 'list,form',
            'res_model': 'sale.order',
            'target': 'current',
            'domain': [("appointment_id", "=", self.id)]
        }

    @api.onchange('user_id')
    def onchange_user_id(self):
        type_list = []
        if self.user_id:
            type_list = self.user_id.appointment_type_ids.ids
        return {"domain": {
            'appointment_type_id': [('id', 'in', type_list)]}}

    @api.onchange("appointment_type_id")
    def show_hide_location(self):
        if self.appointment_type_id and self.appointment_type_id.address_need:
            self.show_address = True
        else:
            self.show_address = False

    @api.depends('user_id')
    def _compute_location_address(self):
        for rec in self:
            rec.location_address = rec.user_id.partner_id.location_address
            rec.amount = rec.user_id.partner_id.amount
            rec.currency_id = rec.user_id.partner_id.currency_id.id

    @api.depends('date', 'partner_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = str(rec.partner_id.name) + " (" + str(rec.date) + ')'

    @api.onchange('designation_id')
    def _onchange_designation_id(self):
        if self.designation_id:
            return {"domain": {
                'user_id': [('designation_id', '=', self.designation_id.id), ('partner_id.app_user', '=', True)]}}
        else:
            return {"domain": {'user_id': [('partner_id.app_user', '=', True)]}}

    @api.onchange('date')
    def _onchange_date(self):
        self.slot_of_time_id = False
        if self.date:
            domain = []
            if self.date:
                domain.append(('name', '=', str(self.date.weekday())))
            if self.user_id:
                domain.append(('partner_id', '=', self.user_id.partner_id.id))
            self.day_of_week_id = self.env['day.of.week'].sudo().search(domain, limit=1)
            user_tz = self.env.user.tz or 'UTC'
            now = datetime.now().astimezone(pytz.timezone(user_tz))

            now_float = now.hour + (int(now.minute / 60 * 100) / 100)
            appointment_system_ids = self.env['em.appointment.system'].sudo().search([('date', '=', self.date)], )

            slot_of_time_ids = []
            for appointment_system_id in appointment_system_ids:
                slot_of_time_ids.append(appointment_system_id.slot_of_time_id.id)

            if now.date() > self.date:
                return {"domain": {'slot_of_time_id': [('day_of_week_id', '=', False)], }}
            elif now.date() == self.date:
                return {"domain": {
                    'slot_of_time_id': [('day_of_week_id', '=', self.day_of_week_id.id), ('time_from', '>', now_float),
                                        ('id', 'not in', slot_of_time_ids)]}}
            else:
                return {"domain": {'slot_of_time_id': [('day_of_week_id', '=', self.day_of_week_id.id),
                                                       ('id', 'not in', slot_of_time_ids)]}}
        else:
            self.day_of_week_id = False
            return {"domain": {'slot_of_time_id': [('day_of_week_id', '=', False)], }}

    @api.onchange('date')
    def show_slot_hints(self):
        if self.date and self.user_id:
            slots = self.get_slots(self.date, self.user_id.id)

            def check_slot():
                date = self.date
                hint_slots = []
                while date >= datetime.today().date():
                    slots = self.get_slots(date, self.user_id.id).mapped("display_name")
                    if slots:
                        hint_slots.append({"date": date, "slots": slots})
                    date = date - timedelta(days=1)
                date = self.date
                if date <= datetime.today().date():
                    date = datetime.today().date() + timedelta(days=1)

                max_advance_appointment_date = datetime.today() + timedelta(days=self.user_id.partner_id.duration)
                while date <= max_advance_appointment_date.date():
                    slots = self.get_slots(date, self.user_id.id).mapped("display_name")
                    if slots:
                        hint_slots.append({"date": date, "slots": slots})
                    date = date + timedelta(days=1)
                hint_slots.sort(key=lambda s: s['date'])

                message_str = "\n\nThere are some slots available for other days: \n"
                date_format = self.env['res.lang']._lang_get(self.env.user.lang).date_format

                for slot in hint_slots:
                    date = slot['date'].strftime(date_format or "%Y/%m/%d")
                    message_str += date + " :  " + ', '.join(slot['slots']) + "\n"
                raise ValidationError(
                    "No Slots for the selected date!!! %s" % message_str if hint_slots else "No Free Slots available "
                                                                                            "for appointment!!!")

            if not slots:
                check_slot()
            else:
                domain = self._onchange_date()
                filtered_slots = slots.filtered_domain(domain["domain"]["slot_of_time_id"])
                if not filtered_slots:
                    check_slot()

    def get_slots(self, day, user_id):
        domain = []
        user_id = self.env['res.users'].sudo().search([('id', '=', user_id)])
        if day:
            domain.append(('name', '=', (day.weekday())))
        if user_id:
            domain.append(('partner_id', '=', user_id.partner_id.id))

        day_of_week_id = self.env['day.of.week'].sudo().search(domain, limit=1)
        allotted_slot_of_time_ids = []
        appointment_system_ids = self.env['em.appointment.system'].sudo().search(
            [('date', '=', day)], )
        user_tz = self.env.user.tz or 'UTC'
        now = datetime.now().astimezone(pytz.timezone(user_tz))
        now_float = now.hour + (int(now.minute / 60 * 100) / 100)
        for appointment_system_id in appointment_system_ids:
            allotted_slot_of_time_ids.append(appointment_system_id.slot_of_time_id.id)
        dom = [('day_of_week_id', '=', day_of_week_id.id), ('id', 'not in', allotted_slot_of_time_ids)]
        if day == datetime.now().date():
            dom.append(('time_from', '>', now_float))
        slot_of_time_ids = self.env['slot.of.time'].sudo().search(dom)
        return slot_of_time_ids

    def order_items(self):
        if self.additional_item_line_ids:
            order_line = []
            for item_line in self.additional_item_line_ids:
                order_line.append([0, 0, {
                    'product_id': item_line.product_id.id,
                    "name": item_line.name,
                    "sequence": item_line.sequence,
                    "price_unit": item_line.price_unit,
                    "tax_id": item_line.tax_id,
                    "discount": item_line.discount,
                    "product_uom_qty": item_line.product_uom_qty,
                    "product_uom": item_line.product_uom.id,
                    "product_uom_category_id": item_line.product_uom_category_id.id,

                }])
            order_id = self.env["sale.order"].create({
                "partner_id": self.partner_id.id,
                "order_line": order_line,
                "appointment_id": self.id
            })


class AppointmentAdditionalItem(models.Model):
    _name = "appointment.additional.item"
    _description = "Appointment Additional Items"

    appointment_id = fields.Many2one('em.appointment.system', string='Appointment Reference', required=True,
                                     ondelete='cascade', index=True, copy=False)
    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    tax_id = fields.Many2many('account.tax', string='Taxes',
                              domain=['|', ('active', '=', False), ('active', '=', True)])
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    product_id = fields.Many2one(
        'product.product', string='Product',
        domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        change_default=True, ondelete='restrict', check_company=True)
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    currency_id = fields.Many2one(related='appointment_id.currency_id', depends=['appointment_id.currency_id'],
                                  store=True,
                                  string='Currency', readonly=True)
    company_id = fields.Many2one(related='appointment_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the Appointment line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.appointment_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.appointment_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

    @api.onchange("product_id")
    def onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.get_product_multiline_description_sale()
            self.price_unit = self.product_id.lst_price
            self.tax_id = self.product_id.taxes_id
            self.product_uom = self.product_id.uom_id.id
        else:
            self.name = ""
            self.price_unit = 0
            self.tax_id = False

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        if self.appointment_id.partner_id:
            product = self.product_id.with_context(
                lang=self.appointment_id.partner_id.lang,
                partner=self.appointment_id.partner_id,
                quantity=self.product_uom_qty,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(product.lst_price,
                                                                                      product.taxes_id, self.tax_id,
                                                                                      self.company_id)


class Designation(models.Model):
    _name = 'designation.designation'
    _description = "Appointee Designation"

    name = fields.Char(required=True)


class DayOfWeek(models.Model):
    _name = 'day.of.week'
    _rec_name = 'display_name'
    _description = "Week Day"

    display_name = fields.Char('Display Name', compute="_compute_display_name")
    name = fields.Selection(
        [('6', 'Sunday'), ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'),
         ('4', 'Friday'), ('5', 'Saturday')], required=True)

    slot_of_time_ids = fields.One2many('slot.of.time', 'day_of_week_id')
    partner_id = fields.Many2one('res.partner', ondelete='cascade')

    @api.depends('name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = dict(self._fields['name'].selection).get(rec.name)


class SlotOfTime(models.Model):
    _name = 'slot.of.time'
    _rec_name = 'display_name'
    _description = "Appointment Time Slot"

    display_name = fields.Char('Display Name', compute="_compute_display_name")
    time_from = fields.Float(required=True)
    time_to = fields.Float(required=True)
    day_of_week_id = fields.Many2one('day.of.week', ondelete='cascade')

    slot_book_line_ids = fields.One2many("slot.book.line", "slot_id")

    @api.depends('time_from', 'time_to')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = str('{0:02.0f}:{1:02.0f}'.format(*divmod(rec.time_from * 60, 60))) + ' - ' + str(
                '{0:02.0f}:{1:02.0f}'.format(*divmod(rec.time_to * 60, 60)))

    def unblock(self, force_unblock=False):
        ircsudo = self.env['ir.config_parameter'].sudo()
        slot_reserve_time = int(ircsudo.get_param('em_appointment_system.slot_reserve_time'))
        for rec in self:
            sbl_ids = rec.slot_book_line_ids.filtered(lambda sbl: datetime.now() >= (
                    sbl.blocked_date + timedelta(minutes=slot_reserve_time)) or force_unblock)
            rec.slot_book_line_ids = [(3, l_id.id, 0) for l_id in sbl_ids]


class SlotBookLine(models.Model):
    _name = "slot.book.line"

    blocked = fields.Boolean()
    session_id = fields.Char()
    blocked_date = fields.Datetime()
    blocked_for_date = fields.Date()
    slot_id = fields.Many2one("slot.of.time")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    app_user = fields.Boolean(string='Appointee')
    designation_id = fields.Many2one('designation.designation')
    location_address = fields.Text()
    appointment_type_ids = fields.Many2many('appointment.type')
    duration = fields.Integer(default=15, string='Advance Appointment (Days)')
    amount = fields.Monetary()
    currency_id = fields.Many2one('res.currency')
    day_of_week_ids = fields.One2many('day.of.week', 'partner_id')


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    appointment_system_id = fields.Many2one('em.appointment.system')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_mail_to_user = fields.Boolean()
    allow_mail_to_partner = fields.Boolean()
    allow_reminder_to_partner = fields.Boolean()
    slot_reserve_time = fields.Integer()

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()

        self.env['ir.config_parameter'].set_param('em_appointment_system.allow_mail_to_user',
                                                  self.allow_mail_to_user)
        self.env['ir.config_parameter'].set_param('em_appointment_system.allow_mail_to_partner',
                                                  self.allow_mail_to_partner)
        self.env['ir.config_parameter'].set_param('em_appointment_system.allow_reminder_to_partner',
                                                  self.allow_reminder_to_partner)
        self.env['ir.config_parameter'].set_param('em_appointment_system.slot_reserve_time',
                                                  self.slot_reserve_time)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ircsudo = self.env['ir.config_parameter'].sudo()
        allow_mail_to_user = ircsudo.get_param('em_appointment_system.allow_mail_to_user')
        allow_mail_to_partner = ircsudo.get_param('em_appointment_system.allow_mail_to_partner')
        allow_reminder_to_partner = ircsudo.get_param('em_appointment_system.allow_reminder_to_partner')
        slot_reserve_time = ircsudo.get_param('em_appointment_system.slot_reserve_time')
        cron_id = self.env.ref('em_appointment_system.ir_cron_em_appointment_system')
        if allow_reminder_to_partner:
            cron_id.active = True
        else:
            cron_id.active = False

        res.update(
            allow_mail_to_user=allow_mail_to_user,
            allow_mail_to_partner=allow_mail_to_partner,
            allow_reminder_to_partner=allow_reminder_to_partner,
            slot_reserve_time=slot_reserve_time,
        )
        return res


class InheritWebsite(models.Model):
    _inherit = 'website'

    def get_appointment_counts(self):
        appointment_ids = self.env['em.appointment.system'].sudo().search(
            [('partner_id', '=', self.env.user.partner_id.id)])
        return len(appointment_ids)

    def _get_appointment_slots(self, cal_of, user_id=None, appointment_type_id=None, timezone='UTC', employee=None):

        self.ensure_one()
        today = datetime.now()
        last_day = today + timedelta(days=cal_of)
        start = today
        month_dates_calendar = cal.Calendar(0).monthdatescalendar
        months = []
        while (start.year, start.month) <= (last_day.year, last_day.month):
            dates = month_dates_calendar(start.year, start.month)
            for week_index, week in enumerate(dates):
                for day_index, day in enumerate(week):
                    mute_cls = weekend_cls = today_cls = None
                    today_slots = []
                    if day.weekday() in (cal.SUNDAY, cal.SATURDAY):
                        weekend_cls = 'o_weekend'
                    if day == today.date() and day.month == today.month:
                        today_cls = 'o_today'
                    if day.month != start.month:
                        mute_cls = 'text-muted o_mute_day'
                    else:
                        slots = self.get_slots(day, user_id)
                        for slot in slots:
                            dt = str(day)
                            tm_to = str('{0:02.0f}:{1:02.0f}'.format(*divmod(slot.time_to * 60, 60)))
                            tm = str('{0:02.0f}:{1:02.0f}'.format(*divmod(slot.time_from * 60, 60)))
                            d_t = dt + " " + tm
                            datetime_object = datetime.strptime(d_t, '%Y-%m-%d %H:%M')
                            if day < last_day.date():
                                today_slots.append({
                                    'employee_id': user_id,
                                    'datetime': datetime_object.strftime('%Y-%m-%d %H:%M:%S'),
                                    'hours': tm + ' - ' + tm_to,
                                    'appointment_type_id': appointment_type_id,
                                })
                    dates[week_index][day_index] = {
                        'day': day,
                        'slots': today_slots,
                        'mute_cls': mute_cls,
                        'weekend_cls': weekend_cls,
                        'today_cls': today_cls
                    }
            months.append({
                'month': format_datetime(start, 'MMMM Y', locale=get_lang(self.env).code),
                'weeks': dates,
                'today_date': datetime.now(),
                'start': start,
            })

            start = start + relativedelta(months=1)
        return months

    def get_slots(self, day, user_id):
        domain = []
        user_id = self.env['res.users'].sudo().search([('id', '=', user_id)])
        if day:
            domain.append(('name', '=', (day.weekday())))
        if user_id:
            domain.append(('partner_id', '=', user_id.partner_id.id))

        day_of_week_id = self.env['day.of.week'].sudo().search(domain, limit=1)
        allotted_slot_of_time_ids = []
        appointment_system_ids = self.env['em.appointment.system'].sudo().search(
            [('date', '=', day)], )
        user_tz = self.env.user.tz or 'UTC'
        now = datetime.now().astimezone(pytz.timezone(user_tz))
        now_float = now.hour + (int(now.minute / 60 * 100) / 100)
        for appointment_system_id in appointment_system_ids:
            allotted_slot_of_time_ids.append(appointment_system_id.slot_of_time_id.id)
        dom = [('day_of_week_id', '=', day_of_week_id.id), ('id', 'not in', allotted_slot_of_time_ids)]
        if day == datetime.now().date():
            dom.append(('time_from', '>', now_float))
        slot_of_time_ids = self.env['slot.of.time'].sudo().search(dom)
        return slot_of_time_ids


class InheritAction(models.Model):
    _inherit = 'ir.actions.act_window'

    def read(self, fields=None, load='_classic_read'):
        result = super(InheritAction, self).read(fields, load)
        for rec in result:
            domain = rec.get('domain')
            if domain:
                active_id = ""
                domain = eval(domain)
                index = [index for index, tpl in enumerate(domain) if len(tpl) == 3 and tpl[2] == 'Account_Move']
                if index:
                    domain[index[0]] = ('invoice_user_id', '=', self.env.user.id)
                    rec['domain'] = str(domain)
        return result


class SaleOrder(models.Model):
    _inherit = "sale.order"

    appointment_id = fields.Many2one('em.appointment.system', string='Appointment Reference',
                                     ondelete='cascade', index=True, copy=False)
