from odoo import models, api, fields, _
from datetime import datetime, time, timedelta
import logging

_logger = logging.getLogger(__name__)

class HotelDashboardService(models.TransientModel):
    _name = 'hotel.dashboard.service'
    _description = 'Hotel Dashboard Data Service'

    @api.model
    def _get_date_range(self, period, date_from=False, date_to=False):
        today = fields.Date.context_today(self)
        if period == 'custom' and date_from:
            return fields.Date.from_string(date_from), fields.Date.from_string(date_to) if date_to else today
        
        if period == 'today':
            return today, today
        elif period == 'yesterday':
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif period == 'week':
            # This Week (last 7 days including today)
            return today - timedelta(days=6), today
        elif period == 'last_week':
            # Last full week (Monday-Sunday) or simply previous 7 days
            return today - timedelta(days=13), today - timedelta(days=7)
        elif period == 'month':
            return today - timedelta(days=29), today
        elif period == 'last_month':
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            first_day_last_month = last_day_last_month.replace(day=1)
            return first_day_last_month, last_day_last_month
        elif period == 'quarter':
            month = (today.month - 1) // 3 * 3 + 1
            first_day_q = today.replace(month=month, day=1)
            return first_day_q, today
        elif period == 'last_quarter':
            month = (today.month - 1) // 3 * 3 + 1
            first_day_this_q = today.replace(month=month, day=1)
            last_day_last_q = first_day_this_q - timedelta(days=1)
            m_prev = (last_day_last_q.month - 1) // 3 * 3 + 1
            first_day_last_q = last_day_last_q.replace(month=m_prev, day=1)
            return first_day_last_q, last_day_last_q
        elif period == 'year':
            return today.replace(month=1, day=1), today
        elif period == 'last_year':
            last_y = today.year - 1
            return today.replace(year=last_y, month=1, day=1), today.replace(year=last_y, month=12, day=31)
        
        return today, today

    @api.model
    def get_dashboard_data(self, period='today', filters=None, date_from=False, date_to=False):
        """Main entry point for OWL dashboard data."""
        date_start, date_end = self._get_date_range(period, date_from, date_to)
        start_dt = datetime.combine(date_start, time.min)
        end_dt = datetime.combine(date_end, time.max)

        data = {}

        def safe_call(key, method, default_type=dict, *args, **kwargs):
            try:
                data[key] = method(*args, **kwargs)
            except Exception as e:
                _logger.error("Hotel Dashboard: Error in %s: %s", key, e, exc_info=True)
                data[key] = default_type()

        safe_call('inventory', self._get_inventory_metrics, dict, start_dt, end_dt)
        safe_call('front_desk', self._get_front_desk_metrics, dict, start_dt, end_dt)
        safe_call('guest_status', self._get_guest_status_metrics, dict, start_dt, end_dt)
        safe_call('housekeeping', self._get_housekeeping_metrics)
        safe_call('reservations', self._get_reservation_status_metrics, dict, start_dt, end_dt)
        safe_call('room_occupancy', self._get_room_occupancy_table, list, start_dt, end_dt)
        safe_call('revenue', self._get_revenue_metrics, dict, start_dt, end_dt)
        
        # New Expanded Metrics
        safe_call('alerts', self._get_operational_alerts, dict, start_dt, end_dt)
        safe_call('kpis', self._get_kpi_metrics, dict, start_dt, end_dt)
        safe_call('expenses', self._get_expense_metrics, dict, start_dt, end_dt)
        safe_call('shift', self._get_shift_revenue, dict, start_dt, end_dt)
        
        # Dashboard 2.0 Metrics
        safe_call('pickup', self._get_pickup_data, dict, start_dt, end_dt)
        safe_call('lead_time', self._get_lead_time_buckets, dict, start_dt, end_dt)
        safe_call('risk', self._get_risk_scores, dict, start_dt, end_dt)
        safe_call('cash_flow', self._get_cash_flow_metrics, dict, start_dt, end_dt)
        safe_call('hk_efficiency', self._get_hk_efficiency, list, start_dt, end_dt)
        
        # Forecast
        forecast_result = self._get_forecast_data(start_dt, end_dt)
        data['forecast'] = forecast_result.get('days', [])
        data['avg_forecast_occupancy'] = forecast_result.get('avg_occupancy', 0.0)
        
        safe_call('channels', self._get_channel_performance, list, start_dt, end_dt)
        safe_call('qms', self._get_qms_metrics, dict, start_dt, end_dt)

        data['currency'] = self.env.company.currency_id.symbol or 'BD'
        data['period_label'] = period.replace('_', ' ').capitalize()
        data['period_bounds'] = {
            'start': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'end': end_dt.strftime('%Y-%m-%d %H:%M:%S'),
        }
        return data

    @api.model
    def get_ai_insights(self, period='today'):
        """Fetches AI analysis for the dashboard."""
        try:
            data = self.get_dashboard_data(period=period)
            # Minimize data sent to LLM to avoid token limits and focus on key metrics
            summary_data = {
                'occupancy': data.get('inventory', {}).get('occupancy_rate'),
                'revenue': data.get('revenue', {}).get('revenue'),
                'period': period,
                'alerts': len(data.get('alerts', [])),
                'top_channel': (data.get('channels') or [{}])[0].get('code') if data.get('channels') else 'Direct'
            }
            return self.env['hotel.ai.engine'].analyze_dashboard(summary_data)
        except Exception as e:
            _logger.error(f"AI Insights Failed: {e}")
            return "<p>AI is currently sleeping (Connection Error).</p>"

    @api.model
    def get_pricing_suggestion(self):
        """Fetches AI pricing suggestion."""
        try:
            # Get occupancy forecast for context
            start_dt = fields.Datetime.now()
            end_dt = start_dt + timedelta(days=7)
            forecast = self._get_forecast_data(start_dt, end_dt)
            return self.env['hotel.ai.engine'].get_pricing_suggestion(forecast)
        except Exception as e:
            _logger.error(f"AI Pricing Failed: {e}")
            return {"suggestion": "Unable to generate.", "action": "Check logs.", "impact": "Unknown."}

    @api.model
    def chat_with_agent(self, message, history=None):
        """Conversational interface."""
        try:
            # Context is key. We give it 'today's snapshot'.
            context = self.get_dashboard_data(period='today')
            # Sanitize history
            if history is None: history = []
            
            return self.env['hotel.ai.engine'].query_bot(message, context_data=context)
        except Exception as e:
            return f"Error: {str(e)}"

    def _get_inventory_metrics(self, start_dt, end_dt):
        room_model = self.env['hotel.room']
        booking_model = self.env['hotel.book.history']

        total_rooms = room_model.search_count([])
        maintenance_rooms = room_model.search_count([('state', '=', 'maintenance')])
        
        # In-house rooms are the bookings currently checked in, regardless of
        # whether the selected dashboard period ends before their checkout time.
        occupied_rooms_today = booking_model.search_count([
            ('state', '=', 'checked_in'),
        ])

        occupancy_rate = (occupied_rooms_today / total_rooms * 100.0) if total_rooms else 0.0

        return {
            'total_rooms': total_rooms,
            'occupied_rooms': occupied_rooms_today,
            'vacant_rooms': total_rooms - occupied_rooms_today - maintenance_rooms,
            'maintenance_rooms': maintenance_rooms,
            'occupancy_rate': round(occupancy_rate, 2)
        }

    def _get_front_desk_metrics(self, start_dt, end_dt):
        booking_model = self.env['hotel.book.history']
        
        active_domain = [('state', '=', 'checked_in')]

        # Arrivals
        arrivals_total = booking_model.search_count([
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt),
            ('state', '!=', 'cancelled')
        ])
        checked_in_today = booking_model.search_count([
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt),
            ('state', 'in', ['checked_in', 'checked_out'])
        ])

        # Departures
        departures_total = booking_model.search_count([
            ('check_out', '>=', start_dt),
            ('check_out', '<=', end_dt),
            ('state', 'in', ['checked_in', 'checked_out'])
        ])
        checked_out_today = booking_model.search_count([
            ('check_out', '>=', start_dt),
            ('check_out', '<=', end_dt),
            ('state', '=', 'checked_out')
        ])

        in_house_total = booking_model.search_count(active_domain)
        arrived_today = booking_model.search_count(active_domain + [
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt),
        ])
        stay_over = booking_model.search_count(active_domain + [
            '|',
            ('check_in', '<', start_dt),
            ('check_in', '=', False),
        ])

        return {
            'arrivals': {'total': arrivals_total, 'checked_in': checked_in_today},
            'departures': {'total': departures_total, 'checked_out': checked_out_today},
            'in_house': {'total': in_house_total, 'arrived_today': arrived_today, 'stay_over': max(0, stay_over)}
        }

    def _get_guest_status_metrics(self, start_dt, end_dt):
        booking_model = self.env['hotel.book.history']
        
        # Current in-house bookings
        bookings = booking_model.search([
            ('state', '=', 'checked_in')
        ])
        
        partners = bookings.mapped('partner_id')
        
        return {
            'foreigner': len(partners.filtered(lambda p: p.is_foreigner)),
            'vip': len(partners.filtered(lambda p: p.is_vip)),
            'complimentary': len(bookings.filtered(lambda b: b.is_complimentary)),
            'doctor': len(partners.filtered(lambda p: p.is_doctor)),
            'single_lady': len(partners.filtered(lambda p: p.is_single_lady)),
            'house_use': len(bookings.filtered(lambda b: b.is_house_use))
        }

    def _get_housekeeping_metrics(self):
        room_model = self.env['hotel.room']
        
        return {
            'clean': room_model.search_count([('cleaning_status', '=', 'clean')]),
            'dirty': room_model.search_count([('cleaning_status', '=', 'dirty')]),
            'inspected': room_model.search_count([('cleaning_status', '=', 'inspected')]),
            'skip': room_model.search_count([('cleaning_status', '=', 'skip')]),
            'sleep': room_model.search_count([('cleaning_status', '=', 'sleep')]),
            'discrepancy': room_model.search_count([('cleaning_status', '=', 'discrepancy')])
        }

    def _get_reservation_status_metrics(self, start_dt, end_dt):
        booking_model = self.env['hotel.book.history']
        
        confirmed = booking_model.search_count([
            ('state', '=', 'confirmed'),
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt)
        ])
        tentative = booking_model.search_count([
            ('state', '=', 'tentative'),
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt)
        ])
        waitlist = booking_model.search_count([
            ('state', '=', 'waitlist'),
            ('check_in', '>=', start_dt),
            ('check_in', '<=', end_dt)
        ])

        return {
            'labels': ['Confirmed', 'Waitlist', 'Tentative'],
            'data': [confirmed, waitlist, tentative],
            'total': confirmed + waitlist + tentative
        }

    def _get_room_occupancy_table(self, start_dt, end_dt):
        room_type_model = self.env['product.template']
        room_model = self.env['hotel.room']
        booking_model = self.env['hotel.book.history']

        room_types = room_type_model.search([('is_room', '=', True)])
        
        results = []
        for rt in room_types:
            rooms_of_type = room_model.search([('room_type', '=', rt.id)])
            room_ids = rooms_of_type.ids
            
            if not room_ids: continue

            sold = booking_model.search_count([
                ('room_id', 'in', room_ids),
                ('state', '=', 'checked_in')
            ])
            maintenance_count = room_model.search_count([('id', 'in', room_ids), ('state', '=', 'maintenance')])
            ooo_count = room_model.search_count([('id', 'in', room_ids), ('state', '=', 'unavailable')])
            dirty_count = room_model.search_count([('id', 'in', room_ids), ('cleaning_status', '=', 'dirty')])

            house_use = booking_model.search_count([
                ('room_id', 'in', room_ids),
                ('state', '=', 'checked_in'),
                ('is_house_use', '=', True)
            ])
            complimentary = booking_model.search_count([
                ('room_id', 'in', room_ids),
                ('state', '=', 'checked_in'),
                ('is_complimentary', '=', True)
            ])
            
            # Calculate revenue for this room type
            bookings = booking_model.search([
                ('room_id', 'in', room_ids),
                ('state', '=', 'checked_in')
            ])
            total_revenue = sum(bookings.mapped('total_amount'))
            
            # Calculate ADR and RevPAR
            adr = (total_revenue / sold) if sold > 0 else 0.0
            revpar = (total_revenue / len(room_ids)) if len(room_ids) > 0 else 0.0
            
            total = len(room_ids)
            occ_rate = (sold / total * 100.0) if total else 0.0
            
            # available = total - sold - maintenance - ooo - dirty
            available = total - sold - maintenance_count - ooo_count - dirty_count

            results.append({
                'room_type': rt.name,
                'room_type_id': rt.id,
                'sold': sold,
                'maintenance': maintenance_count,
                'out_of_order': ooo_count,
                'dirty': dirty_count,
                'house_use': house_use,
                'complimentary': complimentary,
                'occupancy': round(occ_rate, 2),
                'available': available,
                'total': total,
                'adr': round(adr, 2),
                'revpar': round(revpar, 2)
            })

        return results

    def _get_revenue_metrics(self, start_dt, end_dt):
        kpi_engine = self.env["hotel.kpi.engine"]
        res, summary = kpi_engine.compute_range_kpis(start_dt.date(), end_dt.date(), self.env.company.id)
        
        return {
            'revenue': summary.get('total_revenue', 0.0),
            'today_income': summary.get('room_revenue', 0.0),
            'last_week_income': summary.get('extra_revenue', 0.0),
            'ota_commission': summary.get('ota_commission', 0.0),
            'net_revenue': summary.get('net_revenue', 0.0),
        }

    def _get_operational_alerts(self, start_dt, end_dt):
        """Calculates critical operational risks via KPI Engine."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine.compute_operational_alerts(start_dt.date())

    def _get_kpi_metrics(self, start_dt, end_dt):
        """Calculates ADR, RevPAR, LOS using KPI Engine."""
        kpi_engine = self.env["hotel.kpi.engine"]
        res, summary = kpi_engine.compute_range_kpis(start_dt.date(), end_dt.date(), self.env.company.id)
        
        # Lead time
        lead_analytics = kpi_engine.compute_lead_time_analytics(start_dt.date(), end_dt.date(), self.env.company.id)
        
        return {
            'adr': summary.get('adr', 0.0), # Use summary directly
            'revpar': summary.get('revpar', 0.0),
            'cancel_rate': 0.0, 
            'avg_los': round(summary.get('nights_sold', 0.0) / len(res) if res else 0.0, 1),
            'gop': round(summary.get('gop', 0.0), 2),
            'goppar': round(summary.get('goppar', 0.0), 2),
            'avg_lead_time': lead_analytics.get('avg_lead_time', 0.0),
        }

    def _get_shift_revenue(self, start_dt, end_dt):
        """Calculates today's cash vs card split."""
        # Kept local as it's very specific to POS/Payment journals which KPI engine might not fully cover yet
        payments = self.env['account.payment'].search([
            ('date', '>=', start_dt.date()),
            ('date', '<=', end_dt.date()),
            ('state', '=', 'posted'),
            ('payment_type', '=', 'inbound')
        ])
        
        cash = sum(p.amount for p in payments if 'cash' in (p.journal_id.name or '').lower())
        card = sum(p.amount for p in payments if 'bank' in (p.journal_id.name or '').lower() or 'card' in (p.journal_id.name or '').lower())
        
        return {
            'total': cash + card,
            'cash': cash,
            'card': card,
            'pending_deposits': 0.0
        }

    def _get_forecast_data(self, start_dt, end_dt):
        """Generates a 30-day sellable inventory forecast and average."""
        room_model = self.env['hotel.room']
        booking_model = self.env['hotel.book.history']
        total_rooms = room_model.search_count([])
        
        forecast_days = []
        total_occ = 0.0
        for i in range(30):
            forecast_date = (end_dt + timedelta(days=i)).date()
            f_start = datetime.combine(forecast_date, time.min)
            f_end = datetime.combine(forecast_date, time.max)
            
            occupied = booking_model.search_count([
                ('state', 'in', ['confirmed', 'checked_in']),
                ('check_in', '<=', f_end),
                ('check_out', '>', f_start)
            ])
            
            occ_rate = (occupied / total_rooms * 100) if total_rooms else 0
            total_occ += occ_rate
            forecast_days.append({
                'date': forecast_date.strftime('%a %d'),
                'date_raw': fields.Date.to_string(forecast_date),
                'occupancy': round(occ_rate, 1),
                'rooms_left': total_rooms - occupied,
                'high_demand': occ_rate > 85,
                'sold_out': (total_rooms - occupied) <= 0 if total_rooms else False,
            })
            
        return {
            'days': forecast_days,
            'avg_occupancy': round(total_occ / 7, 1) if forecast_days else 0.0
        }

    def _get_channel_performance(self, start_dt, end_dt):
        """Performance by booking source via KPI Engine."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine.compute_channel_breakdown(start_dt.date(), end_dt.date(), self.env.company.id)
        
    def _get_expense_metrics(self, start_dt, end_dt):
        """Fetch expense breakdown via KPI Engine."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine._get_operating_expenses(start_dt, end_dt, self.env.company.id)
        
    def _get_pickup_data(self, start_dt, end_dt):
        """Fetch booking pacing analysis."""
        kpi_engine = self.env["hotel.kpi.engine"]
        # Use end_dt as target date for "today" context if period is today, else use end of range
        target = end_dt.date()
        return kpi_engine.compute_pickup_analysis(target, self.env.company.id)

    def _get_lead_time_buckets(self, start_dt, end_dt):
        """Fetch lead time histogram data."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine.compute_lead_time_analytics(start_dt.date(), end_dt.date(), self.env.company.id)
        
    def _get_risk_scores(self, start_dt, end_dt):
        """Fetch executive risk scores."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine.compute_risk_score(end_dt.date(), self.env.company.id)
        
    def _get_cash_flow_metrics(self, start_dt, end_dt):
        """Fetch cash position."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine.compute_cash_flow_metrics(self.env.company.id)

    def _get_hk_efficiency(self, start_dt, end_dt):
        """Fetch housekeeping staff performance."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine.compute_hk_efficiency(end_dt.date(), self.env.company.id)

    def _get_qms_metrics(self, start_dt, end_dt):
        """Calculates Quality & Process compliance metrics."""
        booking_model = self.env['hotel.book.history']
        
        # 1. Pending Approvals (Active backlog)
        pending_approvals = booking_model.search_count([('state', '=', 'to_approve')])
        
        # 2. Check-in Delay (Minutes)
        delay_avg = booking_model.read_group(
            [('arrival_date', '!=', False), ('checkin_delay', '>', 0)],
            ['checkin_delay:avg'],
            []
        )
        avg_delay = delay_avg[0]['checkin_delay'] if delay_avg and delay_avg[0]['checkin_delay'] else 0.0
        
        # 3. Process Non-conformities (Dirty rooms on arrival)
        dirty_arrivals = booking_model.search_count([
            ('check_in', '>=', start_dt.date()),
            ('check_in', '<=', end_dt.date()),
            ('state', 'in', ['confirmed', 'checked_in']),
            ('room_id.cleaning_status', '=', 'dirty')
        ])

        # 4. Compliance Score (Mock logic: Penalty for delay and dirty rooms)
        compliance = 100.0
        if avg_delay > 15: compliance -= 10
        if dirty_arrivals > 0: compliance -= (dirty_arrivals * 2)

        return {
            'pending_approvals': pending_approvals,
            'avg_checkin_delay': round(avg_delay, 1),
            'dirty_arrivals': dirty_arrivals,
            'sla_compliance': max(0, compliance)
        }
