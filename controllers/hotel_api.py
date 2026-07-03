# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time

from odoo import fields, http, _
from odoo.http import request
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class HotelApiBridge(http.Controller):
    """Public JSON API for external hotel booking websites.

    If system parameter ``hotel.api.token`` is set, callers must send it as
    ``api_token`` in the JSON payload or as ``X-Hotel-Api-Token`` header.
    """

    def _ok(self, **payload):
        payload.setdefault('success', True)
        return payload

    def _error(self, message, code='bad_request', **extra):
        result = {'success': False, 'error': message, 'code': code}
        result.update(extra)
        return result

    def _check_api_token(self, kwargs):
        expected = request.env['ir.config_parameter'].sudo().get_param('hotel.api.token')
        if not expected:
            return True
        supplied = kwargs.get('api_token') or request.httprequest.headers.get('X-Hotel-Api-Token')
        return supplied == expected

    def _api_company(self):
        params = request.env['ir.config_parameter'].sudo()
        company_name = params.get_param('hotel.api.company_name') or 'Al Faris Suite 2 W.L.L'
        company = request.env['res.company'].sudo().search([('name', '=', company_name)], limit=1)
        if not company:
            company = request.env['res.company'].sudo().search([('name', 'ilike', 'Al Faris Suite 2')], limit=1)
        return company or request.env.company

    def _parse_stay(self, checkin, checkout):
        try:
            checkin_date = fields.Date.from_string(checkin)
            checkout_date = fields.Date.from_string(checkout)
        except Exception:
            raise ValueError(_('Dates must use YYYY-MM-DD format.'))
        if not checkin_date or not checkout_date:
            raise ValueError(_('Check-in and check-out dates are required.'))
        if checkout_date <= checkin_date:
            raise ValueError(_('Check-out must be after check-in.'))

        params = request.env['ir.config_parameter'].sudo()
        checkin_hour = float(params.get_param('hotel.policy.checkin_time', 15.0))
        checkout_hour = float(params.get_param('hotel.policy.checkout_time', 12.0))

        def as_time(hour_float):
            hour = int(hour_float)
            minute = int(round((hour_float - hour) * 60))
            return time(hour, minute)

        return (
            datetime.combine(checkin_date, as_time(checkin_hour)),
            datetime.combine(checkout_date, as_time(checkout_hour)),
        )

    def _serialize_booking(self, booking):
        booking = booking.sudo()
        token = booking._get_access_token()
        sale_order = booking.sale_order_id.sudo() if booking.sale_order_id else False
        payment_url = False
        if sale_order:
            payment_url = sale_order.get_portal_url()

        return {
            'id': booking.id,
            'reference': booking.name,
            'state': booking.state,
            'access_token': token,
            'guest': {
                'id': booking.partner_id.id,
                'name': booking.partner_id.name,
                'email': booking.partner_id.email,
                'phone': booking.partner_id.phone or booking.partner_id.mobile,
            } if booking.partner_id else False,
            'room': {
                'id': booking.room_id.id,
                'name': booking.room_id.name,
                'room_type_id': booking.room_id.room_type_id.id,
                'room_type': booking.room_id.room_type_id.name,
            } if booking.room_id else False,
            'check_in': fields.Datetime.to_string(booking.check_in) if booking.check_in else False,
            'check_out': fields.Datetime.to_string(booking.check_out) if booking.check_out else False,
            'nights': booking.duration_days_decimal,
            'total_amount': booking.total_amount,
            'currency': booking.currency_id.name,
            'payment_status': booking.payment_status,
            'sale_order_id': sale_order.id if sale_order else False,
            'payment_url': payment_url,
        }

    def _find_or_create_partner(self, guest):
        if not isinstance(guest, dict):
            raise ValueError(_('Guest details are required.'))
        name = (guest.get('name') or '').strip()
        email = (guest.get('email') or '').strip().lower()
        phone = (guest.get('phone') or guest.get('mobile') or '').strip()
        if not name:
            raise ValueError(_('Guest name is required.'))
        if not email and not phone:
            raise ValueError(_('Guest email or phone is required.'))

        Partner = request.env['res.partner'].sudo()
        partner = email and Partner.search([('email', '=ilike', email)], limit=1)
        if not partner and phone:
            partner = Partner.search(['|', ('phone', '=', phone), ('mobile', '=', phone)], limit=1)

        values = {
            'name': name,
            'email': email or False,
            'phone': phone or False,
            'is_hotel_customer': True,
        }
        if partner:
            partner.write({key: value for key, value in values.items() if value})
            return partner
        return Partner.create(values)

    def _available_rooms(self, room_type, checkin_dt, checkout_dt):
        return room_type.room_ids.filtered(
            lambda room: room.state not in ('maintenance', 'unavailable')
            and room.is_available_for_dates(checkin_dt, checkout_dt)
        )

    def _serialize_available_room(self, room, room_type, checkin_dt, checkout_dt):
        image_model = 'hotel.room' if room.image_1920 else 'hotel.room.type'
        image_id = room.id if room.image_1920 else room_type.id
        description = room.website_description or room_type.website_description or ''
        nights = max((checkout_dt.date() - checkin_dt.date()).days, 1)
        price_nightly = room_type.default_price or 0.0
        return {
            'room_id': room.id,
            'room_name': room.name,
            'room_type_id': room_type.id,
            'room_type': room_type.name,
            'code': room_type.code,
            'description': html2plaintext(description).strip(),
            'image_url': f'/web/image/{image_model}/{image_id}/image_1920',
            'floor': room.floor or room_type.floor or '',
            'view': dict(room_type._fields['view'].selection).get(room_type.view, '') if room_type.view else '',
            'bed_type': dict(room_type._fields['bed_type'].selection).get(room_type.bed_type, '') if room_type.bed_type else '',
            'size_sqm': room_type.size_sqm or 0.0,
            'max_guests': room_type.max_occupancy,
            'price_nightly': price_nightly,
            'nights': nights,
            'price_total': price_nightly * nights,
            'currency': room_type.currency_id.name or request.env.company.currency_id.name,
            'amenities': [amenity.name for amenity in room_type.amenity_ids],
        }

    @http.route('/api/hotel/availability', type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')
    def api_availability(self, checkin=None, checkout=None, guests=1, room_type_id=None, **kwargs):
        if not self._check_api_token(kwargs):
            return self._error(_('Unauthorized.'), code='unauthorized')
        try:
            checkin_dt, checkout_dt = self._parse_stay(checkin, checkout)
            guests = int(guests or 1)
        except Exception as exc:
            return self._error(str(exc))

        domain = [('max_occupancy', '>=', guests)]
        if room_type_id:
            domain.append(('id', '=', int(room_type_id)))
        company = self._api_company()
        domain.append(('company_id', 'in', [company.id, False]))
        room_types = request.env['hotel.room.type'].sudo().with_company(company).search(domain)

        nights = max((checkout_dt.date() - checkin_dt.date()).days, 1)
        results = []
        for room_type in room_types:
            available_rooms = self._available_rooms(room_type, checkin_dt, checkout_dt)
            if not available_rooms:
                continue
            price_nightly = room_type.default_price or 0.0
            rooms = [
                self._serialize_available_room(room, room_type, checkin_dt, checkout_dt)
                for room in available_rooms
            ]
            results.append({
                'room_type_id': room_type.id,
                'name': room_type.name,
                'code': room_type.code,
                'description': html2plaintext(room_type.website_description or '').strip(),
                'image_url': f'/web/image/hotel.room.type/{room_type.id}/image_1920',
                'max_guests': room_type.max_occupancy,
                'size_sqm': room_type.size_sqm or 0.0,
                'available_count': len(available_rooms),
                'price_nightly': price_nightly,
                'nights': nights,
                'price_total': price_nightly * nights,
                'currency': room_type.currency_id.name or request.env.company.currency_id.name,
                'amenities': [amenity.name for amenity in room_type.amenity_ids],
                'rooms': rooms,
            })

        return self._ok(
            company={'id': company.id, 'name': company.name},
            checkin=checkin,
            checkout=checkout,
            guests=guests,
            room_types=results,
        )

    @http.route('/api/hotel/booking/draft', type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')
    def api_booking_draft(self, room_type_id=None, checkin=None, checkout=None, adults=1, children=0, booking_source_id=None, **kwargs):
        if not self._check_api_token(kwargs):
            return self._error(_('Unauthorized.'), code='unauthorized')
        try:
            checkin_dt, checkout_dt = self._parse_stay(checkin, checkout)
            company = self._api_company()
            room_type = request.env['hotel.room.type'].sudo().with_company(company).browse(int(room_type_id))
            if not room_type.exists():
                return self._error(_('Room type not found.'), code='not_found')
            if room_type.company_id and room_type.company_id != company:
                return self._error(_('Room type is not available for this hotel.'), code='not_found')
        except Exception as exc:
            return self._error(str(exc))

        available_rooms = self._available_rooms(room_type, checkin_dt, checkout_dt)
        if not available_rooms:
            return self._error(_('No rooms available for the selected dates.'), code='sold_out')

        booking_vals = {
            'room_id': available_rooms[0].id,
            'check_in': checkin_dt,
            'check_out': checkout_dt,
            'total_adults': int(adults or 1),
            'total_children': int(children or 0),
            'company_id': company.id,
            'state': 'draft',
        }
        if booking_source_id:
            booking_vals['booking_source_id'] = int(booking_source_id)

        booking = request.env['hotel.book.history'].sudo().create(booking_vals)
        return self._ok(booking=self._serialize_booking(booking))

    @http.route('/api/hotel/booking/guest', type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')
    def api_booking_guest(self, booking_id=None, access_token=None, guest=None, **kwargs):
        if not self._check_api_token(kwargs):
            return self._error(_('Unauthorized.'), code='unauthorized')
        booking = self._get_booking(booking_id, access_token)
        if not booking:
            return self._error(_('Booking not found or token is invalid.'), code='not_found')
        if booking.state not in ('draft', 'tentative'):
            return self._error(_('Guest details can only be changed before confirmation.'), code='invalid_state')
        try:
            partner = self._find_or_create_partner(guest)
            booking.write({'partner_id': partner.id})
        except Exception as exc:
            return self._error(str(exc))
        return self._ok(booking=self._serialize_booking(booking))

    @http.route('/api/hotel/booking/confirm', type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')
    def api_booking_confirm(self, booking_id=None, access_token=None, **kwargs):
        if not self._check_api_token(kwargs):
            return self._error(_('Unauthorized.'), code='unauthorized')
        booking = self._get_booking(booking_id, access_token)
        if not booking:
            return self._error(_('Booking not found or token is invalid.'), code='not_found')
        if not booking.partner_id:
            return self._error(_('Guest details are required before confirmation.'), code='guest_required')
        if booking.state == 'draft':
            try:
                booking.action_confirm()
            except Exception as exc:
                return self._error(str(exc), code='confirmation_failed')
        return self._ok(booking=self._serialize_booking(booking))

    @http.route('/api/hotel/payment/init', type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')
    def api_payment_init(self, booking_id=None, access_token=None, confirm=True, **kwargs):
        if not self._check_api_token(kwargs):
            return self._error(_('Unauthorized.'), code='unauthorized')
        booking = self._get_booking(booking_id, access_token)
        if not booking:
            return self._error(_('Booking not found or token is invalid.'), code='not_found')
        if not booking.partner_id:
            return self._error(_('Guest details are required before payment.'), code='guest_required')

        try:
            if confirm and booking.state == 'draft':
                booking.action_confirm()
            sale_order = booking.sale_order_id
            if not sale_order:
                sale_order = booking._create_sale_order(booking)
                booking.sale_order_id = sale_order.id
            if sale_order.state in ('draft', 'sent'):
                sale_order.action_confirm()
            payment_url = sale_order.get_portal_url()
        except Exception as exc:
            _logger.exception("Hotel API payment init failed for booking %s", booking.id)
            return self._error(str(exc), code='payment_init_failed')

        return self._ok(booking=self._serialize_booking(booking), payment_url=payment_url)

    @http.route('/api/hotel/booking/status', type='jsonrpc', auth='public', methods=['POST'], csrf=False, cors='*')
    def api_booking_status(self, booking_id=None, access_token=None, reference=None, **kwargs):
        if not self._check_api_token(kwargs):
            return self._error(_('Unauthorized.'), code='unauthorized')
        booking = self._get_booking(booking_id, access_token, reference=reference)
        if not booking:
            return self._error(_('Booking not found or token is invalid.'), code='not_found')
        return self._ok(booking=self._serialize_booking(booking))

    # Backward-compatible aliases for the existing website bridge.
    @http.route('/hotel/api/availability', type='jsonrpc', auth='public', website=True, csrf=False, cors='*')
    def check_availability(self, checkin=None, checkout=None, guests=1, suite_type=None, **kwargs):
        if suite_type and suite_type != 'All Suites':
            room_type = request.env['hotel.room.type'].sudo().search([('name', 'ilike', suite_type)], limit=1)
            if room_type:
                kwargs['room_type_id'] = room_type.id
        return self.api_availability(checkin=checkin, checkout=checkout, guests=guests, **kwargs)

    @http.route('/hotel/api/book', type='jsonrpc', auth='public', website=True, csrf=False, cors='*')
    def create_booking(self, rt_id=None, checkin=None, checkout=None, guests=1, partner_data=None, **kwargs):
        draft = self.api_booking_draft(
            room_type_id=rt_id,
            checkin=checkin,
            checkout=checkout,
            adults=guests,
            **kwargs,
        )
        if not draft.get('success'):
            return draft
        booking = draft['booking']
        guest = self.api_booking_guest(
            booking_id=booking['id'],
            access_token=booking['access_token'],
            guest=partner_data,
            **kwargs,
        )
        if not guest.get('success'):
            return guest
        return self.api_booking_confirm(
            booking_id=booking['id'],
            access_token=booking['access_token'],
            **kwargs,
        )

    def _get_booking(self, booking_id=None, access_token=None, reference=None):
        if not access_token:
            return False
        domain = []
        if booking_id:
            domain.append(('id', '=', int(booking_id)))
        elif reference:
            domain.append(('name', '=', reference))
        else:
            return False
        domain.append(('access_token', '=', access_token))
        booking = request.env['hotel.book.history'].sudo().search(domain, limit=1)
        return booking if booking.exists() else False
