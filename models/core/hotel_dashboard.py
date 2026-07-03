from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HotelDashboard(models.Model):
    _name = 'hotel.dashboard'
    _description = 'Hotel Dashboard'

    name = fields.Char(default="Hotel Dashboard")
    date_range = fields.Selection(
        [
            ('last_7_days', 'Last 7 Days'),
            ('last_30_days', 'Last 30 Days'),
            ('this_month', 'This Month'),
            ('this_year', 'This Year'),
            ('custom', 'Custom Range'),
        ],
        string="Period",
        default='last_30_days',
        help="Time range used to compute bookings and revenue statistics.",
    )
    custom_start_date = fields.Date(string="Start Date")
    custom_end_date = fields.Date(string="End Date")
    date_range_label = fields.Char(string="Period Label", compute="_compute_dashboard_metrics")

    total_rooms = fields.Integer(string="Total Rooms", compute="_compute_dashboard_metrics")
    occupied_rooms = fields.Integer(string="Occupied Rooms", compute="_compute_dashboard_metrics")
    available_rooms = fields.Integer(string="Available Rooms", compute="_compute_dashboard_metrics")
    maintenance_rooms = fields.Integer(string="Maintenance Rooms", compute="_compute_dashboard_metrics")
    occupancy_rate = fields.Float(string="Occupancy Rate (%)", compute="_compute_dashboard_metrics", digits=(16, 2))

    total_bookings = fields.Integer(string="Total Bookings", compute="_compute_dashboard_metrics")
    current_bookings = fields.Integer(string="Current Bookings", compute="_compute_dashboard_metrics")
    cancelled_bookings = fields.Integer(string="Cancellations", compute="_compute_dashboard_metrics")
    pending_checkins = fields.Integer(string="Pending Check-ins", compute="_compute_dashboard_metrics")
    pending_checkouts = fields.Integer(string="Pending Check-outs", compute="_compute_dashboard_metrics")

    revenue_amount = fields.Monetary(string="Revenue", compute="_compute_dashboard_metrics")

    rooms_needing_cleaning = fields.Integer(string="Rooms Needing Cleaning", compute="_compute_dashboard_metrics")
    overdue_checkouts = fields.Integer(string="Overdue Check-outs", compute="_compute_dashboard_metrics")
    rooms_in_maintenance = fields.Integer(string="Rooms in Maintenance", compute="_compute_dashboard_metrics")

    today_income = fields.Monetary(string="Today's Income", compute="_compute_today_statistics")
    last_week_income = fields.Monetary(string="Last Week Income", compute="_compute_today_statistics")
    today_label = fields.Char(string="Today Label", compute="_compute_today_statistics")

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    @api.model
    def _compute_overlap_nights(self, booking, start_date, end_date):
        """Return the number of nights for a booking that fall within [start_date, end_date]."""
        if not booking.check_in or not booking.check_out:
            return 0.0
        start = max(booking.check_in.date(), start_date)
        end = min((booking.check_out - timedelta(days=1)).date(), end_date)
        delta = (end - start).days + 1
        return max(delta, 0)

    def _search_paid_orders(self, date_field, start_dt, end_dt):
        """Return sale orders whose invoices are fully paid within a date range."""

        sale_model = self.env['sale.order']
        return sale_model.search([
            ('state', 'in', ['sale', 'done']),
            (date_field, '>=', start_dt),
            (date_field, '<=', end_dt),
            ('invoice_ids.state', '=', 'posted'),
            ('invoice_ids.payment_state', '=', 'paid'),
        ])

    @api.model
    def get_metrics_for_period_v2(self, start_dt, end_dt):
        """Compute KPI metrics using booking overlaps for accurate occupancy and nights sold."""
        start_date = start_dt.date()
        end_date = end_dt.date()
        room_model = self.env['hotel.room']
        booking_model = self.env['hotel.book.history']

        # Optimize: Count rooms directly in DB
        total_rooms = room_model.search_count([])
        maintenance_rooms = room_model.search_count([('state', '=', 'maintenance')])
        rooms_needing_cleaning = room_model.search_count([('cleaning_status', '=', 'dirty')])

        overlapping_bookings = booking_model.search([
            ('state', 'in', ['confirmed', 'checked_in', 'checked_out']),
            ('check_in', '<=', end_dt),
            ('check_out', '>', start_dt),
        ])
        total_bookings = booking_model.search_count([
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt),
            ('state', '!=', 'cancelled'),
        ])
        cancelled_bookings = booking_model.search_count([
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt),
            ('state', '=', 'cancelled'),
        ])

        pending_checkins = booking_model.search_count([
            ('state', '=', 'confirmed'),
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt),
        ])
        pending_checkouts = booking_model.search_count([
            ('state', '=', 'checked_in'),
            ('check_out', '>=', start_dt),
            ('check_out', '<=', end_dt),
        ])

        # Occupied rooms per day (Optimized Calculation)
        # Instead of looping days, we sum the overlap duration for each booking
        occupied_room_nights = 0
        
        # Pre-calc date objects for comparison
        period_start_date = start_dt.date()
        period_end_date = end_dt.date()
        
        # Arrivals/Departures calculation using SQL or efficient filters
        # Using existing search_count logic for arrivals/departures is faster than iterating
        arrivals = booking_model.search_count([
            ('state', '!=', 'cancelled'),
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt)
        ])
        departures = booking_model.search_count([
             ('state', 'in', ['confirmed', 'checked_in', 'checked_out']),
             ('check_out', '>=', start_dt),
             ('check_out', '<=', end_dt)
        ])
        
        cancellations = cancelled_bookings # already calculated above

        for booking in overlapping_bookings:
            # Calculate overlapping days efficiently
            # Overlap = max(0, min(booking_end, period_end) - max(booking_start, period_start))
            if not booking.check_in or not booking.check_out: continue
            
            b_start = booking.check_in.date()
            b_end = booking.check_out.date()
            
            # Logic: Occupied night is when you stay OVERNIGHT.
            # So if you check in on Day 1 and check out on Day 2, that is 1 night (Day 1).
            # We count nights where the guest sleeps properly.
            
            # Effective range for the period
            range_start = max(b_start, period_start_date)
            # The night of 'end_date' is included? 
            # If period is Month, we want nights 1st to 30th/31st. 
            # If booking checks out on 5th, they stayed nights of 1,2,3,4.
            # So we effectively count days < end_date?
            # Standard hotel logic: Night of CheckIn is 1. Night of CheckOut is 0.
            
            # Booking Interval (Closed, Open): [check_in, check_out)
            # Period Interval (Closed, Closed): [start_dt, end_dt] (Based on dashboard logic usually includes the last day)
            # But 'time.max' suggests end_dt includes the full last day.
            
            # Let's align: 
            # Effective CheckOut for counting nights is limited by period_end_date + 1 day (since period includes the night of period_end_date)
            # OR, does period_end_date mean the cutoff?
            # Usually strict date range for reports: [Start, End].
            # If I select "Today", I want occupancy for tonight.
            
            range_end = min(b_end, period_end_date + timedelta(days=1))
            
            delta = (range_end - range_start).days
            if delta > 0:
                occupied_room_nights += delta

        total_days = (end_date - start_date).days + 1
        availability_capacity = total_rooms * total_days if total_rooms else 0
        occupancy_rate = (occupied_room_nights / availability_capacity * 100.0) if availability_capacity else 0.0

        revenue_orders = self._search_paid_orders('date_order', start_dt, end_dt)
        revenue_amount = sum(val or 0.0 for val in revenue_orders.mapped('amount_total'))
        average_length_of_stay = 0
        if total_bookings:
            duration_sum = sum(val or 0.0 for val in overlapping_bookings.mapped('duration_days_decimal'))
            average_length_of_stay = duration_sum / total_bookings if total_bookings else 0

        average_daily_rate = revenue_amount / occupied_room_nights if occupied_room_nights else 0.0

        occupied_rooms_today = overlapping_bookings.filtered(
            lambda b: b.check_in <= end_dt and b.check_out > end_dt
        )

        return {
            'total_rooms': total_rooms,
            'occupied_rooms': len(occupied_rooms_today),
            'available_rooms': total_rooms - len(occupied_rooms_today) - maintenance_rooms if total_rooms else 0,
            'maintenance_rooms': maintenance_rooms,
            'rooms_in_maintenance': maintenance_rooms,
            'rooms_needing_cleaning': rooms_needing_cleaning,
            'occupancy_rate': occupancy_rate,
            'total_bookings': total_bookings,
            'cancelled_bookings': cancelled_bookings,
            'current_bookings': len(overlapping_bookings),
            'pending_checkins': pending_checkins,
            'pending_checkouts': pending_checkouts,
            'revenue_amount': revenue_amount,
            'overdue_checkouts': booking_model.search_count([
                ('state', '=', 'checked_in'),
                ('check_out', '<', start_dt),
            ]),
            'arrivals': arrivals,
            'departures': departures,
            'cancellations': cancellations,
            'average_length_of_stay': average_length_of_stay,
            'avg_daily_rate': average_daily_rate,
            'occupied_room_nights': occupied_room_nights,
            'availability_capacity': availability_capacity,
        }

    @api.model
    def get_metrics_for_period(self, start_dt, end_dt):
        """Return a dictionary with the key performance indicators for the period."""
        room_model = self.env['hotel.room']
        booking_model = self.env['hotel.book.history']

        rooms = room_model.search([])
        total_rooms = len(rooms)
        occupied_rooms = len(rooms.filtered(lambda r: r.state == 'occupied'))
        available_rooms = len(rooms.filtered(lambda r: r.state == 'available'))
        maintenance_rooms = len(rooms.filtered(lambda r: r.state == 'maintenance'))

        booking_domain_range = [
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt),
        ]
        bookings_in_period = booking_model.search(
            booking_domain_range + [('state', '!=', 'cancelled')]
        )
        total_bookings = len(bookings_in_period)
        cancelled_bookings = booking_model.search_count(
            booking_domain_range + [('state', '=', 'cancelled')]
        )

        current_domain = [
            ('state', 'in', ['confirmed', 'checked_in']),
            ('check_in', '<=', end_dt),
            ('check_out', '>=', start_dt),
        ]
        current_bookings = booking_model.search_count(current_domain)

        day_start = start_dt
        day_end = end_dt
        pending_checkins = booking_model.search_count([
            ('state', '=', 'confirmed'),
            ('check_in', '>=', day_start),
            ('check_in', '<=', day_end),
        ])
        pending_checkouts = booking_model.search_count([
            ('state', '=', 'checked_in'),
            ('check_out', '>=', day_start),
            ('check_out', '<=', day_end),
        ])

        revenue_orders = self._search_paid_orders('rental_start_date', start_dt, end_dt)
        revenue_amount = sum(val or 0.0 for val in revenue_orders.mapped('amount_total'))

        rooms_needing_cleaning = len(rooms.filtered(lambda r: r.cleaning_status == 'dirty'))
        overdue_checkouts = booking_model.search_count([
            ('state', '=', 'checked_in'),
            ('check_out', '<', day_start),
        ])

        arrivals = booking_model.search_count([
            ('state', '!=', 'cancelled'),
            ('check_in', '>=', day_start),
            ('check_in', '<=', day_end),
        ])
        departures = booking_model.search_count([
            ('state', 'in', ['confirmed', 'checked_in', 'checked_out']),
            ('check_out', '>=', day_start),
            ('check_out', '<=', day_end),
        ])
        cancellations = booking_model.search_count([
            ('state', '=', 'cancelled'),
            ('write_date', '>=', day_start),
            ('write_date', '<=', day_end),
        ])

        duration_sum = sum(val or 0.0 for val in bookings_in_period.mapped('duration_days_decimal')) if bookings_in_period else 0
        average_length_of_stay = duration_sum / total_bookings if total_bookings else 0
        average_daily_rate = revenue_amount / total_bookings if total_bookings else 0

        return {
            'total_rooms': total_rooms,
            'occupied_rooms': occupied_rooms,
            'available_rooms': available_rooms,
            'maintenance_rooms': maintenance_rooms,
            'rooms_in_maintenance': maintenance_rooms,
            'rooms_needing_cleaning': rooms_needing_cleaning,
            'occupancy_rate': (occupied_rooms / total_rooms * 100.0) if total_rooms else 0.0,
            'total_bookings': total_bookings,
            'cancelled_bookings': cancelled_bookings,
            'current_bookings': current_bookings,
            'pending_checkins': pending_checkins,
            'pending_checkouts': pending_checkouts,
            'revenue_amount': revenue_amount,
            'overdue_checkouts': overdue_checkouts,
            'arrivals': arrivals,
            'departures': departures,
            'cancellations': cancellations,
            'average_length_of_stay': average_length_of_stay,
            'avg_daily_rate': average_daily_rate,
        }

    @api.depends('date_range', 'custom_start_date', 'custom_end_date')
    def _compute_dashboard_metrics(self):
        today = fields.Date.context_today(self)

        for dashboard in self:
            start_dt, end_dt, label = dashboard._get_period_bounds(today, allow_incomplete_custom=True)
            dashboard.date_range_label = label

            if not start_dt or not end_dt:
                dashboard.total_rooms = 0
                dashboard.occupied_rooms = 0
                dashboard.available_rooms = 0
                dashboard.maintenance_rooms = 0
                dashboard.rooms_in_maintenance = 0
                dashboard.occupancy_rate = 0.0
                dashboard.total_bookings = 0
                dashboard.cancelled_bookings = 0
                dashboard.current_bookings = 0
                dashboard.pending_checkins = 0
                dashboard.pending_checkouts = 0
                dashboard.revenue_amount = 0
                dashboard.rooms_needing_cleaning = 0
                dashboard.overdue_checkouts = 0
                continue

            metrics = dashboard.get_metrics_for_period_v2(start_dt, end_dt) or dashboard.get_metrics_for_period(start_dt, end_dt)
            dashboard.total_rooms = metrics.get('total_rooms', 0)
            dashboard.occupied_rooms = metrics.get('occupied_rooms', 0)
            dashboard.available_rooms = metrics.get('available_rooms', 0)
            dashboard.maintenance_rooms = metrics.get('maintenance_rooms', 0)
            dashboard.rooms_in_maintenance = metrics.get('rooms_in_maintenance', 0)
            dashboard.occupancy_rate = metrics.get('occupancy_rate', 0)
            dashboard.total_bookings = metrics.get('total_bookings', 0)
            dashboard.cancelled_bookings = metrics.get('cancelled_bookings', 0)
            dashboard.current_bookings = metrics.get('current_bookings', 0)
            dashboard.pending_checkins = metrics.get('pending_checkins', 0)
            dashboard.pending_checkouts = metrics.get('pending_checkouts', 0)
            dashboard.revenue_amount = metrics.get('revenue_amount', 0)
            dashboard.rooms_needing_cleaning = metrics.get('rooms_needing_cleaning', 0)
            dashboard.overdue_checkouts = metrics.get('overdue_checkouts', 0)

    @api.depends_context('tz')
    def _compute_today_statistics(self):
        today = fields.Date.context_today(self)

        for dashboard in self:
            today_start = datetime.combine(today, time.min)
            today_end = datetime.combine(today, time.max)
            week_start = today - timedelta(days=today.weekday())
            previous_week_start = week_start - timedelta(days=7)
            previous_week_end = week_start - timedelta(days=1)

            today_orders = dashboard._search_paid_orders('date_order', today_start, today_end)
            dashboard.today_income = sum(val or 0.0 for val in today_orders.mapped('amount_total'))

            last_week_orders = dashboard._search_paid_orders(
                'date_order',
                datetime.combine(previous_week_start, time.min),
                datetime.combine(previous_week_end, time.max),
            )
            dashboard.last_week_income = sum(val or 0.0 for val in last_week_orders.mapped('amount_total'))

            user_tz = self.env.user.tz or 'UTC'
            now_utc = fields.Datetime.now()
            now_local = fields.Datetime.context_timestamp(dashboard, fields.Datetime.to_datetime(now_utc))
            dashboard.today_label = _('%(date)s (%(tz)s)') % {
                'date': fields.Datetime.to_string(now_local),
                'tz': user_tz,
            }

    @api.onchange('date_range')
    def _onchange_date_range(self):
        if self.date_range != 'custom':
            self.custom_start_date = False
            self.custom_end_date = False
        else:
            start_date, end_date = self._get_default_custom_dates()
            self.custom_start_date = self.custom_start_date or start_date
            self.custom_end_date = self.custom_end_date or end_date
        self._compute_dashboard_metrics()

    @api.onchange('custom_start_date', 'custom_end_date')
    def _onchange_custom_dates(self):
        if self.date_range == 'custom':
            self._compute_dashboard_metrics()

    def _get_default_custom_dates(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1), today

    def _get_period_bounds(self, today, allow_incomplete_custom=False):
        self.ensure_one()

        if self.date_range == 'custom':
            default_start, default_end = self._get_default_custom_dates()
            # Always fall back to sensible defaults so users can pick dates
            # without hitting validation errors while filling the fields.
            start_date = self.custom_start_date or default_start
            end_date = self.custom_end_date or default_end

            # Persist the resolved dates on the record to keep domains and
            # computed values in sync for subsequent actions.
            self.custom_start_date = start_date
            self.custom_end_date = end_date

            if allow_incomplete_custom and not (start_date and end_date):
                return None, None, _('Select a start and end date')
            # if not start_date or not end_date:
            #     raise UserError(_('Please select both a start date and an end date for the custom period.'))

            if start_date > end_date:
                raise UserError(_('The start date cannot be after the end date.'))

            label = _('%(start)s to %(end)s') % {
                'start': fields.Date.to_string(start_date),
                'end': fields.Date.to_string(end_date),
            }
        elif self.date_range == 'last_7_days':
            start_date = today - timedelta(days=6)
            label = _('Last 7 Days')
        elif self.date_range == 'this_month':
            start_date = today.replace(day=1)
            label = _('This Month')
        elif self.date_range == 'this_year':
            start_date = today.replace(month=1, day=1)
            label = _('This Year')
        else:
            start_date = today - timedelta(days=29)
            label = _('Last 30 Days')

        end_date = self.custom_end_date if self.date_range == 'custom' else today

        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)
        return start_dt, end_dt, label

    def _action_open_bookings(self, domain, name):
        tree_view = self.env.ref('atk_hotel.view_hotel_dashboard_reservation_tree')
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.book.history',
            'view_mode': 'list,form',
            'views': [(tree_view.id, 'list'), (False, 'form')],
            'domain': domain,
            'context': {'create': False},
        }

    def _action_open_rooms(self, domain, name):
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.room',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': domain,
            'context': {'create': False},
        }

    def _ensure_singleton_dashboard(self):
        """Ensure we execute button actions on a single dashboard record."""

        self.ensure_one()
        return self

    def action_view_total_rooms(self):
        self._ensure_singleton_dashboard()
        return self._action_open_rooms([], _('All Rooms'))

    def action_view_occupied_rooms(self):
        self._ensure_singleton_dashboard()
        return self._action_open_rooms([('state', '=', 'occupied')], _('Occupied Rooms'))

    def action_view_available_rooms(self):
        self._ensure_singleton_dashboard()
        return self._action_open_rooms([('state', '=', 'available')], _('Vacant Rooms'))

    def action_view_rooms_in_maintenance(self):
        self._ensure_singleton_dashboard()
        return self._action_open_rooms([('state', '=', 'maintenance')], _('Maintenance Rooms'))

    def action_view_rooms_needing_cleaning(self):
        self._ensure_singleton_dashboard()
        return self._action_open_rooms([('cleaning_status', '=', 'dirty')], _('Rooms Needing Cleaning'))

    def _action_open_sale_orders(self, domain, name):
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': domain,
            'context': {'create': False},
        }

    # === REPORT HELPERS ===
    def _ensure_report_action(self, xmlid, name, report_name, report_type):
        report_action = self.env.ref(xmlid, raise_if_not_found=False)
        if report_action:
            return report_action

        model = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
        report_action = self.env['ir.actions.report'].create(
            {
                'name': name,
                'model': self._name,
                'report_name': report_name,
                'report_file': report_name,
                'report_type': report_type,
                'binding_model_id': model.id if model else False,
                'binding_type': 'report',
                'print_report_name': "'%s'" % name,
            }
        )

        self.env['ir.model.data'].create(
            {
                'module': 'atk_hotel',
                'name': xmlid.split('.')[-1],
                'model': 'ir.actions.report',
                'res_id': report_action.id,
            }
        )

        return report_action

    # === REPORT ACTIONS ===
    def action_print_mis_dashboard_pdf(self):
        self.ensure_one()
        action = self._ensure_report_action(
            'atk_hotel.action_report_hotel_mis_dashboard_pdf',
            'Hotel MIS Dashboard',
            'atk_hotel.report_hotel_mis_dashboard_document',
            'qweb-pdf',
        )
        return action.report_action(self)

    def action_print_mis_dashboard_html(self):
        self.ensure_one()
        action = self._ensure_report_action(
            'atk_hotel.action_report_hotel_mis_dashboard_html',
            'Hotel MIS Dashboard (HTML)',
            'atk_hotel.report_hotel_mis_dashboard_document',
            'qweb-html',
        )
        return action.report_action(self)

    def action_print_daily_status_pdf(self):
        self.ensure_one()
        action = self._ensure_report_action(
            'atk_hotel.action_report_hotel_daily_status_pdf',
            'Hotel Daily Status',
            'atk_hotel.report_hotel_daily_status_document',
            'qweb-pdf',
        )
        return action.report_action(self)

    def action_print_daily_status_html(self):
        self.ensure_one()
        action = self._ensure_report_action(
            'atk_hotel.action_report_hotel_daily_status_html',
            'Hotel Daily Status (HTML)',
            'atk_hotel.report_hotel_daily_status_document',
            'qweb-html',
        )
        return action.report_action(self)

    def action_view_total_bookings(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        start_dt, end_dt, _label = self._get_period_bounds(today)
        domain = [
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt),
            ('state', '!=', 'cancelled'),
        ]
        return self._action_open_bookings(domain, _('Total Bookings'))

    def action_view_current_bookings(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        start_dt, end_dt, _label = self._get_period_bounds(today)
        domain = [
            ('state', 'in', ['confirmed', 'checked_in']),
            ('check_in', '<=', end_dt),
            ('check_out', '>=', start_dt),
        ]
        return self._action_open_bookings(domain, _('Current Bookings'))

    def action_view_cancelled_bookings(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        start_dt, end_dt, _label = self._get_period_bounds(today)
        domain = [
            ('state', '=', 'cancelled'),
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt),
        ]
        return self._action_open_bookings(domain, _('Cancelled Bookings'))

    def action_view_pending_checkins(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        start_dt, end_dt, _label = self._get_period_bounds(today)
        domain = [
            ('state', '=', 'confirmed'),
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt),
        ]
        return self._action_open_bookings(domain, _('Pending Check-ins'))

    def action_view_pending_checkouts(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        start_dt, end_dt, _label = self._get_period_bounds(today)
        domain = [
            ('state', '=', 'checked_in'),
            ('check_out', '>=', start_dt),
            ('check_out', '<=', end_dt),
        ]
        return self._action_open_bookings(domain, _('Pending Check-outs'))

    def action_view_overdue_checkouts(self):
        """Open checked-in bookings whose checkout date is past the selected period."""

        self.ensure_one()
        today = fields.Date.context_today(self)
        start_dt, _end_dt, _label = self._get_period_bounds(today)
        domain = [
            ('state', '=', 'checked_in'),
            ('check_out', '<', start_dt),
        ]
        return self._action_open_bookings(domain, _('Overdue Check-outs'))

    def action_view_revenue(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        start_dt, end_dt, _label = self._get_period_bounds(today)
        domain = [
            ('state', 'in', ['sale', 'done']),
            ('rental_start_date', '>=', start_dt),
            ('rental_start_date', '<=', end_dt),
            ('invoice_ids.state', '=', 'posted'),
            ('invoice_ids.payment_state', '=', 'paid'),
        ]
        return self._action_open_sale_orders(domain, _('Revenue Orders'))

    def action_view_today_income(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)
        domain = [
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', today_start),
            ('date_order', '<=', today_end),
            ('invoice_ids.state', '=', 'posted'),
            ('invoice_ids.payment_state', '=', 'paid'),
        ]
        return self._action_open_sale_orders(domain, _('Today\'s Orders'))
