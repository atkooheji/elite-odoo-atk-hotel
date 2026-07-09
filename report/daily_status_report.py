from datetime import datetime, time

from odoo import _, fields, models
from odoo.tools import format_date


class ReportHotelDailyStatus(models.AbstractModel):
    _name = 'report.atk_hotel.report_hotel_daily_status_document'
    _description = 'Hotel Daily Status Report'

    @property
    def STATUS_LABELS(self):
        return {
            'occupied': _('Occupied'),
            'reserved': _('Booking Confirmed'),
            'available': _('Vacant'),
            'dirty': _('Dirty'),
            'maintenance': _('OOO'),
            'provision': _('Provision Booking'),
            'blocked': _('OOS'),
        }

    def _get_room_status(self, room, bookings_today, future_bookings):
        """Return a status keyword representing the room state for the day."""
        room_bookings = bookings_today.get(room.id, [])

        if any(booking.state == 'checked_in' for booking in room_bookings):
            return 'occupied'
        if any(booking.state == 'confirmed' for booking in room_bookings):
            return 'reserved'
        if room.state == 'maintenance':
            return 'maintenance'
        if room.state == 'unavailable':
            return 'blocked'
        if room.cleaning_status == 'dirty':
            return 'dirty'
        if room.id in future_bookings:
            return 'provision'
        return 'available'

    def _get_report_values(self, docids, data=None):
        dashboard_records = self.env['hotel.dashboard'].browse(docids)
        report_date = fields.Date.to_date(
            data.get('report_date') if data else fields.Date.context_today(self)
        )
        start_dt = datetime.combine(report_date, time.min)
        end_dt = datetime.combine(report_date, time.max)

        room_model = self.env['hotel.room']
        booking_model = self.env['hotel.book.history']

        rooms = room_model.search([], order='room_type, name')
        room_ids = rooms.ids

        bookings_today = booking_model.search([
            ('room_id', 'in', room_ids),
            ('state', '!=', 'cancelled'),
            ('check_in', '<=', end_dt),
            ('check_out', '>=', start_dt),
        ])
        bookings_by_room = {}
        for booking in bookings_today:
            bookings_by_room.setdefault(booking.room_id.id, []).append(booking)

        future_booking_rooms = set(
            booking_model.search([
                ('room_id', 'in', room_ids),
                ('state', '=', 'confirmed'),
                ('check_in', '>', end_dt),
            ]).mapped('room_id').ids
        )

        summary_counts = {
            'occupied': 0,
            'reserved': 0,
            'available': 0,
            'dirty': 0,
            'maintenance': 0,
            'provision': 0,
            'blocked': 0,
        }

        room_type_map = {}
        for room in rooms:
            status_key = self._get_room_status(room, bookings_by_room, future_booking_rooms)
            summary_counts[status_key] += 1

            room_type_map.setdefault(room.room_type.id, {
                'room_type': room.room_type,
                'rooms': [],
            })['rooms'].append({
                'name': room.name,
                'status': status_key,
                'status_label': self.STATUS_LABELS[status_key],
                'is_vip': any(getattr(b.partner_id, 'vip', False) or getattr(b.partner_id, 'is_vip', False) for b in bookings_by_room.get(room.id, [])),
            })

        total_rooms = len(rooms)
        checkouts_today = booking_model.search_count([
            ('state', 'in', ['confirmed', 'checked_in', 'checked_out']),
            ('room_id', 'in', room_ids),
            ('check_out', '>=', start_dt),
            ('check_out', '<=', end_dt),
        ])

        room_types = sorted(
            room_type_map.values(), key=lambda item: item['room_type'].name or ''
        )
        for entry in room_types:
            entry['rooms'] = sorted(entry['rooms'], key=lambda room: room['name'])

        max_room_columns = max((len(entry['rooms']) for entry in room_types), default=1)

        # Front Desk Activity Calculations
        checkins_today = len([b for b in bookings_today if b.check_in >= start_dt and b.check_in <= end_dt])
        stay_overs = len([b for b in bookings_today if b.check_in < start_dt and b.check_out > end_dt])
        vips_count = len([b for b in bookings_today if getattr(b.partner_id, 'vip', False) or getattr(b.partner_id, 'is_vip', False)])

        # Financial Yield Calculations
        occupied_bookings = [b for b in bookings_today if b.state in ('checked_in', 'checked_out')]
        total_room_revenue = 0.0
        for b in occupied_bookings:
            day_price = 0.0
            if hasattr(b, 'daily_line_ids') and b.daily_line_ids:
                today_line = b.daily_line_ids.filtered(lambda l: l.date == report_date)
                if today_line:
                    day_price = today_line[0].price if hasattr(today_line[0], 'price') else getattr(today_line[0], 'price_unit', 0.0)
            if not day_price:
                days = b.duration_days_decimal or 1.0
                day_price = b.total_amount / days
            total_room_revenue += day_price

        adr = (total_room_revenue / len(occupied_bookings)) if occupied_bookings else 0.0
        revpar = (total_room_revenue / total_rooms) if total_rooms else 0.0

        summary = {
            'total_rooms': total_rooms,
            'occupied': summary_counts['occupied'],
            'vacant': summary_counts['available'],
            'dirty': summary_counts['dirty'],
            'maintenance': summary_counts['maintenance'],
            'provision': summary_counts['provision'],
            'reserved': summary_counts['reserved'],
            'blocked': summary_counts['blocked'],
            'checkouts_today': checkouts_today,
            'checkins_today': checkins_today,
            'stay_overs': stay_overs,
            'vips_count': vips_count,
            'adr': adr,
            'revpar': revpar,
            'total_room_revenue': total_room_revenue,
            'occupancy_rate': (summary_counts['occupied'] / total_rooms * 100.0) if total_rooms else 0.0,
        }

        return {
            'doc_ids': docids,
            'doc_model': 'hotel.dashboard',
            'docs': dashboard_records,
            'report_date': report_date,
            'room_types': room_types,
            'max_room_columns': max_room_columns,
            'summary': summary,
            'status_labels': self.STATUS_LABELS,
            'format_date': lambda date, **kwargs: format_date(self.env, date, **kwargs),
        }
