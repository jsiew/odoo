import datetime
import logging

import pytz
from odoo.addons.account_payment.controllers.portal import PortalAccount
from odoo.addons.payment import utils as payment_utils
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from werkzeug.utils import redirect

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebsiteAppointmentSystem(PortalAccount):
    @http.route('/appointment', auth='public', methods=['POST', 'GET'], website=True, csrf=False)
    def index(self, **kw):
        # print("kw", kw)
        if kw.get("login_redirect"):
            param = kw.get("login_redirect").split(" ")
            for val in param:
                a = [val.split("=")]

                kw.update(dict(a))
        slot_id = kw.get('slot_id')
        user_id = kw.get('user__id')
        date = kw.get('date')

        re_sch_invoice_id = kw.get('re_sch_invoice_id')
        appointment_type_id = kw.get('appointment_type_id')
        redirect_link = ""
        if user_id:
            if request.env.user._is_public():
                redirect_link = "/web/login?redirect=/appointment?login_redirect=slot_id=%s+user__id=%s+date=%s+appointment_type_id=%s+re_sch_invoice_id=%s" % (
                    slot_id, user_id, date, appointment_type_id, re_sch_invoice_id)
        if slot_id and user_id and date:
            if re_sch_invoice_id:
                re_sch_invoice_id = int(re_sch_invoice_id)

            user_id = http.request.env['res.users'].sudo().search([('id', '=', user_id)])
            appointment_type_id = http.request.env['appointment.type'].sudo().search([('id', '=', appointment_type_id)],
                                                                                     limit=1)

            slot_of_time_id = http.request.env['slot.of.time'].sudo().search([('id', '=', slot_id)])
            dt = str(date)
            tm = str('{0:02.0f}:{1:02.0f}'.format(*divmod(slot_of_time_id.time_from * 60, 60)))
            d_t = dt + " " + tm
            datetime_object = datetime.datetime.strptime(d_t, '%Y-%m-%d %H:%M')
            session_token = http.request.session.get('session_token')
            if not session_token:
                session_token = http.request.httprequest.cookies.get('session_id')
            slot_of_time_ids = http.request.env['slot.of.time'].sudo().search(
                [('slot_book_line_ids.session_id', '=', session_token)])
            slot_of_time_ids.unblock(force_unblock=True)

            slot_of_time_id.slot_book_line_ids = [(0, 0, {
                "blocked": True,
                "session_id": session_token,
                "blocked_date": datetime.datetime.now(),
                "blocked_for_date": datetime_object.date()
            })]

            user_ids = http.request.env['res.users'].sudo().search([('app_user', '=', True)])
            designation_ids = user_ids.mapped('designation_id')
            values = {
                'designation_ids': designation_ids,
                'user_ids': user_ids,
                'slot_of_time_id': slot_of_time_id,
                'userid': user_id,
                'date': datetime_object,
                'appointment_type_id': appointment_type_id,
                're_sch_invoice_id': re_sch_invoice_id,
                'redirect_link': redirect_link,
            }
            if request.session.get("appointment_customer_id"):
                customer_id = request.session.get("appointment_customer_id")
                customer_id = http.request.env['res.partner'].sudo().search([('id', '=', int(customer_id))])
                values.update({
                    "customer_name": customer_id.name,
                    "customer_phone": customer_id.phone,
                    "customer_email": customer_id.email,
                    "customer_address_one": customer_id.street,
                    "customer_address_two": customer_id.street2,
                    "customer_address_city": customer_id.city,
                    "customer_address_state": customer_id.state_id.id,
                    "customer_address_zip": customer_id.zip,
                })
            return http.request.render('website_appointment_system.website_appointment_system', values)
        else:
            return ""

    @http.route(['/slots_time_date'], type='json', auth="user", website=True)
    def slots_time_date(self, **kw):
        date_app = kw.get('date_app')
        try:
            user_id = int(kw.get('user_id'))
            if date_app:
                user_id = http.request.env['res.users'].sudo().search([('id', '=', user_id)])
                datetime_object = datetime.datetime.strptime(date_app, '%Y-%m-%d')
                domain = []
                if datetime_object:
                    domain.append(('name', '=', (datetime_object.weekday())))
                if user_id:
                    domain.append(('partner_id', '=', user_id.partner_id.id))

                day_of_week_id = http.request.env['day.of.week'].sudo().search(domain, limit=1)
                allotted_slot_of_time_ids = []
                appointment_system_ids = http.request.env['em.appointment.system'].sudo().search(
                    [('date', '=', datetime_object), ('state', 'not in', ['cancel', 'done'])])

                for appointment_system_id in appointment_system_ids:
                    allotted_slot_of_time_ids.append(appointment_system_id.slot_of_time_id.id)
                slot_of_time_ids = http.request.env['slot.of.time'].sudo().search(
                    [('day_of_week_id', '=', day_of_week_id.id), ('id', 'not in', allotted_slot_of_time_ids)])
                slot_of_time_list = []
                for slot_of_time_id in slot_of_time_ids:

                    blocked_for_date_list = slot_of_time_id.slot_book_line_ids.mapped('blocked_for_date')
                    if datetime_object.date() not in blocked_for_date_list:
                        slot_of_time_list.append((slot_of_time_id.id, slot_of_time_id.display_name))

                return slot_of_time_list
            else:
                return []

        except (ValueError, TypeError) as e:
            _logger.exception(e)
            return []

    @http.route(['/users_as_desg'], type='json', auth="user", website=True)
    def users_as_desg(self, **kw):
        desg = False
        if kw.get('desg') != 'Designation':
            desg = int(kw.get('desg'))

        if desg and isinstance(desg, int):
            user_ids = http.request.env['res.users'].sudo().search([('designation_id', '=', desg)])
            user_list = []
            for user_id in user_ids:
                user_list.append((user_id.id, user_id.name))

            return user_list

    @http.route(['/find_types'], type='json', auth="public", website=True)
    def find_types(self, **kw):
        user_cal = False
        if kw.get('user_id') and kw.get('user_id') != 'Appointee':
            user_cal = int(kw.get('user_id'))

        if user_cal and isinstance(user_cal, int):
            user_id = http.request.env['res.users'].sudo().search([('id', '=', user_cal)], limit=1)
            type_list = []

            for type in user_id.appointment_type_ids:
                type_list.append((type.id, type.name))

            return type_list

    @http.route(['/location_as_user'], type='json', auth="user", website=True)
    def location_as_user(self, **kw):
        try:
            user_id = int(kw.get('user_id'))
            user_ids = http.request.env['res.users'].sudo().search([('id', '=', user_id)])
            user_list = []
            for user_id in user_ids:
                amount = str(user_id.amount)
                if user_id.currency_id.position == 'after':
                    amount += user_id.currency_id.symbol
                elif user_id.currency_id.position == 'before':
                    amount = user_id.currency_id.symbol + amount
                location_address = user_id.location_address.replace('\n', ', ')
                user_list.append(location_address)
                user_list.append(amount)

            return user_list
        except (ValueError, TypeError) as e:
            _logger.exception(e)
            return []

    @http.route('/confirm_appointment', auth="public", type='http', website=True, csrf=False)
    def confirm_appointment(self, **kw):
        re_sch_invoice_id = False

        slot_of_time_id = kw.get('slot_time') and int(kw.get('slot_time')) or False
        slot_of_time_id = http.request.env['slot.of.time'].sudo().search([('id', '=', slot_of_time_id)])
        session_token = http.request.session.get('session_token')
        if not session_token:
            session_token = http.request.httprequest.cookies.get('session_id')
        if not slot_of_time_id.slot_book_line_ids or slot_of_time_id.slot_book_line_ids[0].session_id != session_token:
            user_ids = http.request.env['res.users'].sudo().search([('app_user', '=', True)])
            designation_ids = user_ids.mapped('designation_id')
            appointment_type_ids = http.request.env['appointment.type'].sudo().search([])

            return http.request.render("website_appointment_system.appointment_user_calendar", {
                'session_expired': True,
                'user_ids': user_ids,
                'designation_ids': designation_ids,
                'appointment_type_ids': appointment_type_ids,
            })

        if kw.get('re_sch_invoice_id'):
            re_sch_invoice_id = int(kw.get('re_sch_invoice_id'))
        if not kw.get('user') or not kw.get('date_app') or not kw.get('slot_time' or kw.get('reason')):
            return http.request.render('website_appointment_system.website_appointment_system_feedback', {
                'appointment_id': False
            })
        if kw.get('desg'):
            desg = int(kw.get('desg'))
            desg_id = http.request.env['designation.designation'].sudo().search([('id', '=', desg)])
        else:
            desg_id = False
        user = int(kw.get('user'))
        date_app = kw.get('date_app')
        appointment_type_id = int(kw.get('appointment_type_id'))
        reason = kw.get('reason')
        user_id = http.request.env['res.users'].sudo().search([('id', '=', user)])
        if http.request.env.user._is_public():
            #   Get Customer Detail fields:
            customer_name = kw.get("customer_name")
            customer_phone = kw.get("customer_phone")
            customer_email = kw.get("customer_email")
            customer_address_one = kw.get("customer_address_one")
            customer_address_two = kw.get("customer_address_two")
            customer_address_city = kw.get("customer_address_city")
            customer_address_state = kw.get("customer_address_state")
            customer_address_zip = kw.get("customer_address_zip")
            if not request.session.get("appointment_customer_id", False):
                partner_id = request.env["res.partner"].sudo().create({
                    "company_type": "person",
                    "name": customer_name,
                    "phone": customer_phone,
                    "email": customer_email,
                    "street": customer_address_one,
                    "street2": customer_address_two,
                    "city": customer_address_city,
                    "state_id": customer_address_state,
                    "zip": customer_address_zip
                })
                # return partner_id
                request.session['appointment_customer_id'] = partner_id.id
            else:
                partner_id = request.session.get("appointment_customer_id")
                partner_id = request.env["res.partner"].sudo().search([("id", "=", int(partner_id))])
                partner_id.write({
                    "company_type": "person",
                    "name": customer_name,
                    "phone": customer_phone,
                    "email": customer_email,
                    "street": customer_address_one,
                    "street2": customer_address_two,
                    "city": customer_address_city,
                    "state_id": customer_address_state,
                    "zip": customer_address_zip
                })
        else:
            partner_id = http.request.env.user.partner_id

        datetime_object = datetime.datetime.strptime(date_app, '%Y-%m-%d')
        domain = []
        if datetime_object:
            domain.append(('name', '=', (datetime_object.weekday())))
        if user_id:
            domain.append(('partner_id', '=', user_id.partner_id.id))

        day_of_week_id = http.request.env['day.of.week'].sudo().search(domain, limit=1)

        appointment_dict = {
            'designation_id': desg_id.id if desg_id else False,
            'day_of_week_id': day_of_week_id.id,
            'slot_of_time_id': slot_of_time_id.id,
            'user_id': user_id.id,
            'appointment_type_id': appointment_type_id,
            'partner_id': partner_id.id,
            'client': kw.get('client_name') or False,
            'reason': reason,
            'date': datetime_object,
        }

        appointment_ids = http.request.env['em.appointment.system'].sudo().search(
            [('partner_id', '=', partner_id.id),
             ('state', 'not in', ['cancel', 'done'])]).filtered(
            lambda app: app.payment_state != 'paid')
        # print("appointment_ids", appointment_ids)
        if not appointment_ids:
            appointment_id = http.request.env['em.appointment.system'].with_user(user_id.id).create(appointment_dict)

            appointment_id.invoice_id = int(re_sch_invoice_id) if re_sch_invoice_id else False
            appointment_id.invoice_id.appointment_system_id = appointment_id.id

            move_id = appointment_id._create_invoice()
            if appointment_id.amount == 0:
                return request.redirect('/success_appointment?app_id=%s&user_id=%s' % (appointment_id.id, user_id.id))
            data_dict = {

                'move_id': move_id,
                'back_url': '/appointment?slot_id=%s&user__id=%s&date=%s&appointment_type_id=%s&re_sch_invoice_id=' % (
                    slot_of_time_id.id, user, date_app, appointment_type_id),
                'success_url': '/success_appointment?app_id=%s&user_id=%s' % (appointment_id.id, user_id.id),
                'redirect_url': 'my/appointment/%s' % appointment_id.id,

            }
            move_id.access_token = payment_utils.generate_access_token(
                appointment_id.partner_id.id, appointment_id.amount, appointment_id.currency_id.id
            )
            val = self._invoice_get_page_view_values(move_id, move_id.access_token, **kw)
            data_dict.update(val)
            # print("data_dict 1",data_dict)

            return http.request.render('website_appointment_system.website_appointment_system_pay_invoice',
                                       data_dict)
        else:
            appointment_id = appointment_ids[0]
            appointment_id.day_of_week_id = day_of_week_id.id
            appointment_id.slot_of_time_id = slot_of_time_id.id
            appointment_id.reason = reason

            appointment_id.date = datetime_object
            move_id = appointment_id.invoice_id
            if appointment_id.amount == 0:
                return request.redirect('/success_appointment?app_id=%s&user_id=%s' % (appointment_id.id, user_id.id))
            data_dict = {

                'move_id': move_id,
                'back_url': '/appointment?slot_id=%s&user__id=%s&date=%s&appointment_type_id=%s&re_sch_invoice_id=' % (
                    slot_of_time_id.id, user, date_app, appointment_type_id),
                'success_url': '/success_appointment?app_id=%s&user_id=%s' % (appointment_id.id, user_id.id),
                'redirect_url': 'my/appointment/%s' % appointment_id.id,

            }
            move_id.access_token = payment_utils.generate_access_token(
                appointment_id.partner_id.id, appointment_id.amount, appointment_id.currency_id.id
            )
            val = self._invoice_get_page_view_values(move_id, move_id.access_token, **kw)
            data_dict.update(val)
            # print("data_dict",data_dict)
            return http.request.render('website_appointment_system.website_appointment_system_pay_invoice',
                                       data_dict)

    @http.route('/success_appointment', auth="public", type='http', website=True, csrf=False)
    def success_appointment(self, **kw):

        appointment_id = http.request.env['em.appointment.system'].with_user(kw.get('user_id')).search(
            [('id', '=', kw.get('app_id'))])
        if appointment_id.invoice_id.sudo().payment_state == 'paid':
            appointment_id.action_confirm(website=True)
            request.session['appointment_customer_id'] = False
        return http.request.render('website_appointment_system.website_appointment_system_feedback', {
            'appointment_id': appointment_id
        })

    @http.route('/appointment_pay/<int:appointment_id>', auth="public", type='http', website=True, csrf=False)
    def appointment_pay(self, appointment_id, **kw):

        appointment_id = http.request.env['em.appointment.system'].sudo().search([('id', '=', appointment_id)])
        am = appointment_id.pay_amount()

        return redirect(am.get('url'))

    @http.route(['/appointment/new'], type='http', auth="public", website=True, csrf=False)
    def appointment_user_calendar(self):

        user_ids = http.request.env['res.users'].sudo().search([('app_user', '=', True)])
        designation_ids = user_ids.mapped('designation_id')
        appointment_type_ids = http.request.env['appointment.type'].sudo().search([])

        return http.request.render("website_appointment_system.appointment_user_calendar", {
            'session_expired': False,
            'user_ids': user_ids,
            'designation_ids': designation_ids,
            'appointment_type_ids': appointment_type_ids,
        })

    @http.route(['/appointment/new/calender'], type='http', auth="public", website=True, csrf=False)
    def appointment_test(self, **kw):
        try:
            user_id = int(kw.get('user_cal'))
            invoice_id = False
            if 'invoice_id' in kw.keys() and kw.get('invoice_id'):
                invoice_id = int(kw.get('invoice_id'))

            appointment_type_id = False
            if kw.get('appointment_type_id'):
                appointment_type_id = int(kw.get('appointment_type_id'))
            # user_ids = http.request.env['res.users'].sudo().search([('app_user', '=', True)])
            userid = http.request.env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
            appointment_type_id = http.request.env['appointment.type'].sudo().search([('id', '=', appointment_type_id)],
                                                                                     limit=1)
            appointment_ids = http.request.env['em.appointment.system'].sudo().search(
                [('partner_id', '=', http.request.env.user.partner_id.id), ('state', 'not in', ['done', 'cancel'])])
            appointment_ids = appointment_ids.filtered(lambda app: app.payment_state != 'paid')
            if appointment_ids:
                go_back = False
            else:
                go_back = True
            return http.request.render("website_appointment_system.appointment_calendar", {
                'slots': http.request.website._get_appointment_slots(cal_of=userid.duration, user_id=user_id,
                                                                     appointment_type_id=appointment_type_id),
                'userid': user_id,
                'go_back': go_back,
                'appointment_type_id': appointment_type_id,
                'invoice_id': invoice_id,
                'today_date': datetime.datetime.today(),

            })
        except (ValueError, TypeError) as e:
            _logger.exception(e)
            return ""

    @http.route(['/o_day_events'], type='json', auth="public", website=True)
    def o_day_events(self, **kw):
        try:
            user_id = int(kw.get('user_id'))
            date_app = kw.get('date')
            appointment_type_id = False
            if kw.get('appointment_type_id'):
                appointment_type_id = int(kw.get('appointment_type_id'))
            appointment_type_id = http.request.env['appointment.type'].sudo().search([('id', '=', appointment_type_id)],
                                                                                     limit=1)

            user_id = http.request.env['res.users'].sudo().search([('id', '=', user_id)])
            datetime_object = datetime.datetime.strptime(date_app, '%Y-%m-%d')
            domain = []
            if datetime_object:
                domain.append(('name', '=', (datetime_object.weekday())))
            if user_id:
                domain.append(('partner_id', '=', user_id.partner_id.id))

            day_of_week_id = http.request.env['day.of.week'].sudo().search(domain, limit=1)
            allotted_slot_of_time_ids = []
            appointment_system_ids = http.request.env['em.appointment.system'].sudo().search(
                [('date', '=', datetime_object), ('state', 'not in', ['cancel', 'done'])])
            user_tz = http.request.env.user.tz or 'UTC'
            now = datetime.datetime.now().astimezone(pytz.timezone(user_tz))

            now_float = now.hour + (int(now.minute / 60 * 100) / 100)

            for appointment_system_id in appointment_system_ids:
                ##############
                if appointment_system_id.payment_state == 'paid':
                    allotted_slot_of_time_ids.append(appointment_system_id.slot_of_time_id.id)

                ##############

            dom = [('day_of_week_id', '=', day_of_week_id.id), ('id', 'not in', allotted_slot_of_time_ids)]
            if datetime_object.date() == datetime.datetime.now().date():
                dom.append(('time_from', '>', now_float))

            slot_of_time_ids = http.request.env['slot.of.time'].sudo().search(dom)
            date_format = http.request.env['res.lang']._lang_get(http.request.env.user.lang).date_format
            date_app = datetime_object.strftime(date_format or "%Y/%m/%d")
            slot_of_time_list = [(user_id.name, date_app, appointment_type_id.name)]
            slot_of_time_ids.unblock()

            for slot_of_time_id in slot_of_time_ids:
                blocked_for_date_list = slot_of_time_id.slot_book_line_ids.mapped('blocked_for_date')
                if datetime_object.date() not in blocked_for_date_list:
                    slot_of_time_list.append((slot_of_time_id.id, slot_of_time_id.display_name))

            return slot_of_time_list

        except (ValueError, TypeError) as e:
            _logger.exception(e)
            return []


class InheritCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        Booking = request.env['em.appointment.system'].sudo()

        if 'booking_count' in counters:
            values['booking_count'] = Booking.search_count([('partner_id', '=', partner.id)])

        return values

    @http.route(['/my/appointment', '/my/appointment/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_appointment(self, page=1, **kw):
        appointment_id = http.request.env['em.appointment.system'].sudo()

        values = {}
        pager = portal_pager(
            url="/my/appointment",
            url_args={},
            total=http.request.website.get_appointment_counts(),
            page=page,
            step=self._items_per_page
        )

        appointment_ids = appointment_id.search([('partner_id', '=', http.request.env.user.partner_id.id)],
                                                order='id desc',
                                                limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'appointment_ids': appointment_ids,
            'page_name': 'Appointment',
            'pager': pager,
            'default_url': '/my/appointment',
        })
        return http.request.render("website_appointment_system.portal_my_appointment", values)

    @http.route(['/my/appointment/<int:appointment_id>'], type='http', auth="public", website=True)
    def portal_my_appointment_detail(self, appointment_id, access_token=None, report_type=None, download=False, **kw):
        try:
            appointment_sudo = self._document_check_access('em.appointment.system', appointment_id,
                                                           access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = {}
        appointment_id = appointment_sudo.search([('id', '=', appointment_id)])
        values.update(appointment_id=appointment_id, page_name='Appointment')
        return http.request.render("website_appointment_system.portal_appoint_page", values)

    @http.route(['/appointment_cancel/<int:appointment_id>'], type='http', auth="public", website=True)
    def appointment_cancel(self, appointment_id, access_token=None, report_type=None, download=False, **kw):
        try:
            appointment_sudo = self._document_check_access('em.appointment.system', appointment_id,
                                                           access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        appointment_id = appointment_sudo.search([('id', '=', appointment_id)])
        appointment_id.cancel()

        return redirect('/my/appointment/%s?access_token=%s' % (appointment_id.id, access_token))

    @http.route('/print_report/<int:appointment_id>/<int:download>', auth="public", type='http', website=True,
                csrf=False)
    def print_report(self, appointment_id, download, access_token=None, **kw):

        try:
            appointment_sudo = self._document_check_access('em.appointment.system', appointment_id,
                                                           access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        appointment_id = appointment_sudo.search([('id', '=', appointment_id)])
        report_ref = 'em_appointment_system.action_report_appointment'
        if download == '0':
            download = False
        elif download == '1':
            download = True
        rep = self._show_report(model=appointment_id, report_type='pdf', report_ref=report_ref, download=download)
        return rep
