from collections import defaultdict
from datetime import datetime, time, timedelta
import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class HotelKPIEngine(models.AbstractModel):
    _name = "hotel.kpi.engine"
    _description = "Unified KPI Engine for Hotel MIS"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _rooms(self, company_id, property_id=False):
        room_model = self.env["hotel.room"]
        domain = []
        if "company_id" in room_model._fields and company_id:
            domain.append(("company_id", "=", company_id))
        if property_id and "property_id" in room_model._fields:
            domain.append(("property_id", "=", property_id))
        return room_model.search(domain)

    def _booking_domain(self, start_dt, end_dt, company_id, property_id=False, include_cancelled=False):
        domain = [
            ("check_in", "<=", end_dt),
            ("check_out", ">", start_dt),
        ]
        if not include_cancelled:
            domain.append(("state", "in", ["confirmed", "checked_in", "checked_out"]))
        if "company_id" in self.env["hotel.book.history"]._fields and company_id:
            domain.append(("company_id", "=", company_id))
        if property_id:
            if "property_id" in self.env["hotel.book.history"]._fields:
                domain.append(("property_id", "=", property_id))
            elif "room_id" in self.env["hotel.book.history"]._fields and "property_id" in self.env["hotel.room"]._fields:
                domain.append(("room_id.property_id", "=", property_id))
        return domain

    def _sale_domain(self, start_dt, end_dt, company_id, property_id=False):
        domain = [
            ("state", "in", ["sale", "done"]),
            ("date_order", ">=", start_dt),
            ("date_order", "<=", end_dt),
        ]
        if "company_id" in self.env["sale.order"]._fields and company_id:
            domain.append(("company_id", "=", company_id))
        if property_id and "property_id" in self.env["sale.order"]._fields:
            domain.append(("property_id", "=", property_id))
        return domain

    def _get_operating_expenses(self, start_dt, end_dt, company_id):
        """Fetch operating expenses breakdown from Accounting."""
        move_line_model = self.env["account.move.line"]
        domain = [
            ("date", ">=", start_dt.date()),
            ("date", "<=", end_dt.date()),
            ("parent_state", "=", "posted"),
            ("account_id.account_type", "=", "expense"),
        ]
        if company_id:
            domain.append(("company_id", "=", company_id))
        
        lines = move_line_model.search(domain)
        
        # Categorize expenses based on account name keywords or tags
        breakdown = defaultdict(float)
        total_expenses = 0.0
        
        for line in lines:
            amount = line.balance
            total_expenses += amount
            name = (line.account_id.name or "").lower()
            
            if "payroll" in name or "salary" in name or "wages" in name:
                breakdown["payroll"] += amount
            elif "utility" in name or "electricity" in name or "water" in name:
                breakdown["utilities"] += amount
            elif "commission" in name or "ota" in name:
                breakdown["commissions"] += amount
            elif "housekeeping" in name or "cleaning" in name:
                breakdown["housekeeping"] += amount
            elif "maintenance" in name or "repair" in name:
                breakdown["maintenance"] += amount
            elif "marketing" in name or "advert" in name:
                breakdown["marketing"] += amount
            elif "admin" in name or "office" in name:
                breakdown["admin"] += amount
            else:
                breakdown["other"] += amount
                
        return {
            "total": total_expenses,
            "breakdown": [{"category": k, "amount": v} for k, v in breakdown.items()]
        }

    def _split_revenue(self, orders):
        room_revenue = extra_revenue = discount_amount = ota_commission = 0.0
        for order in orders:
            # Net revenue calculation: Revenue - commissions
            # We can find commissions from linked hotel.book.history
            for booking in order.hotel_book_history_ids:
                ota_commission += booking.commission_amount

            for line in order.order_line.filtered(lambda l: not l.display_type):
                line_total = line.price_subtotal
                if line.product_id and getattr(line.product_id.product_tmpl_id, "is_room", False):
                    room_revenue += line_total
                else:
                    extra_revenue += line_total
                if line.discount:
                    discount_amount += (line.price_unit * line.product_uom_qty) * (line.discount / 100)
        
        tax_amount = sum(orders.mapped("amount_tax"))
        total_revenue = room_revenue + extra_revenue + tax_amount - discount_amount
        net_revenue = total_revenue - ota_commission
        
        return {
            "room_revenue": room_revenue,
            "extra_revenue": extra_revenue,
            "tax_amount": tax_amount,
            "discount_amount": discount_amount,
            "total_revenue": total_revenue,
            "ota_commission": ota_commission,
            "net_revenue": net_revenue,
        }

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def compute_day_kpis(self, date, company_id, property_id=False):
        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)
        rooms = self._rooms(company_id, property_id)
        total_rooms = len(rooms)
        maintenance_rooms = len(rooms.filtered(lambda r: r.state == "maintenance"))

        booking_model = self.env["hotel.book.history"]
        bookings = booking_model.search(self._booking_domain(start_dt, end_dt, company_id, property_id))
        active_bookings = bookings.filtered(lambda b: b.state in ["confirmed", "checked_in", "checked_out"])
        occupied_rooms = len(active_bookings)
        nights_sold = occupied_rooms
        arrivals = len(active_bookings.filtered(lambda b: b.check_in and b.check_in.date() == date))
        departures = len(active_bookings.filtered(lambda b: b.check_out and b.check_out.date() == date))
        cancellations = booking_model.search_count(
            [
                ("state", "=", "cancelled"),
                ("write_date", ">=", start_dt),
                ("write_date", "<=", end_dt),
            ] + ([ ("company_id", "=", company_id) ] if "company_id" in booking_model._fields and company_id else [])
        )

        sales = self.env["sale.order"].search(self._sale_domain(start_dt, end_dt, company_id, property_id))
        revenue_breakdown = self._split_revenue(sales)
        room_revenue = revenue_breakdown["room_revenue"]

        available_rooms = max(total_rooms - occupied_rooms - maintenance_rooms, 0)
        occupancy_pct = (occupied_rooms / total_rooms * 100.0) if total_rooms else 0.0
        adr = room_revenue / nights_sold if nights_sold else 0.0
        revpar = room_revenue / total_rooms if total_rooms else 0.0

        expenses_data = self._get_operating_expenses(start_dt, end_dt, company_id)
        expenses = expenses_data["total"]
        gop = revenue_breakdown["total_revenue"] - expenses
        goppar = gop / total_rooms if total_rooms else 0.0

        return {
            "date": date,
            "total_rooms": total_rooms,
            "occupied_rooms": occupied_rooms,
            "available_rooms": available_rooms,
            "maintenance_rooms": maintenance_rooms,
            "occupancy_pct": round(occupancy_pct, 2),
            "arrivals": arrivals,
            "departures": departures,
            "cancellations": cancellations,
            "nights_sold": nights_sold,
            "adr": adr,
            "revpar": revpar,
            "revenue": revenue_breakdown["total_revenue"],
            "ota_commission": revenue_breakdown["ota_commission"],
            "net_revenue": revenue_breakdown["net_revenue"],
            "operating_expenses": expenses,
            "expense_breakdown": expenses_data["breakdown"],
            "gop": gop,
            "goppar": goppar,
            "room_revenue": room_revenue,
            "extra_revenue": revenue_breakdown["extra_revenue"],
            "tax_amount": revenue_breakdown["tax_amount"],
            "discount_amount": revenue_breakdown["discount_amount"],
        }

    def compute_range_kpis(self, date_from, date_to, company_id, property_id=False):
        """ Optimized KPI computation using bulk queries """
        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to, time.max)
        
        # 1. Fetch all business data in bulk
        rooms = self._rooms(company_id, property_id)
        total_rooms_count = len(rooms)
        maintenance_rooms_list = rooms.filtered(lambda r: r.state == "maintenance")
        maint_count = len(maintenance_rooms_list)
        
        booking_model = self.env["hotel.book.history"]
        bookings = booking_model.search(self._booking_domain(start_dt, end_dt, company_id, property_id))
        
        sales = self.env["sale.order"].search(self._sale_domain(start_dt, end_dt, company_id, property_id))
        
        # Pre-group sales by date (assuming date_order is used)
        sales_by_date = defaultdict(list)
        for s in sales:
            sales_by_date[s.date_order.date()].append(s)

        # 2. Iterate through days and process cached data
        days_count = (date_to - date_from).days + 1
        day_results = []
        
        for offset in range(days_count):
            day = date_from + timedelta(days=offset)
            d_start = datetime.combine(day, time.min)
            d_end = datetime.combine(day, time.max)
            
            # Filter bookings for this day in memory
            day_bookings = bookings.filtered(lambda b: b.check_in <= d_end and b.check_out > d_start)
            occupied_count = len(day_bookings)
            
            day_sales = sales_by_date.get(day, [])
            rev_breakdown = self._split_revenue(self.env["sale.order"].browse([s.id for s in day_sales]))
            
            room_rev = rev_breakdown["room_revenue"]
            expenses_data = self._get_operating_expenses(d_start, d_end, company_id)
            expenses = expenses_data["total"]
            gop = rev_breakdown["total_revenue"] - expenses
            goppar = gop / total_rooms_count if total_rooms_count else 0.0

            day_results.append({
                "date": day,
                "total_rooms": total_rooms_count,
                "occupied_rooms": occupied_count,
                "available_rooms": max(total_rooms_count - occupied_count - maint_count, 0),
                "maintenance_rooms": maint_count,
                "occupancy_pct": round((occupied_count / total_rooms_count * 100.0) if total_rooms_count else 0.0, 2),
                "revenue": rev_breakdown["total_revenue"],
                "room_revenue": room_rev,
                "ota_commission": rev_breakdown["ota_commission"],
                "net_revenue": rev_breakdown["net_revenue"],
                "operating_expenses": expenses,
                "expense_breakdown": expenses_data["breakdown"],
                "gop": gop,
                "goppar": goppar,
                "extra_revenue": rev_breakdown["extra_revenue"],
                "nights_sold": occupied_count,
                "adr": room_rev / occupied_count if occupied_count else 0.0,
                "revpar": room_rev / total_rooms_count if total_rooms_count else 0.0,
                # Simple counts for other fields
                "arrivals": len(day_bookings.filtered(lambda b: b.check_in.date() == day)),
                "departures": len(day_bookings.filtered(lambda b: b.check_out.date() == day)),
            })

        # 3. Create Summary
        total_revenue = sum(res["revenue"] for res in day_results)
        total_expenses = sum(res["operating_expenses"] for res in day_results)
        total_gop = total_revenue - total_expenses
        total_nights_sold = sum(res["nights_sold"] for res in day_results)
        total_available_nights = total_rooms_count * days_count
        
        summary = {
            "total_rooms": total_rooms_count,
            "rooms_available": sum(res["available_rooms"] for res in day_results),
            "rooms_occupied": sum(res["occupied_rooms"] for res in day_results),
            "rooms_ooo": sum(res["maintenance_rooms"] for res in day_results),
            "nights_sold": total_nights_sold,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "ota_commission": sum(res["ota_commission"] for res in day_results),
            "net_revenue": sum(res["net_revenue"] for res in day_results),
            "gop": total_gop,
            "goppar": total_gop / total_available_nights if total_available_nights else 0.0,
            "room_revenue": sum(res["room_revenue"] for res in day_results),
            "occupancy_pct": round((total_nights_sold / total_available_nights * 100.0) if total_available_nights else 0.0, 2),
            "adr": round(sum(res["room_revenue"] for res in day_results) / total_nights_sold if total_nights_sold else 0.0, 2),
            "revpar": round(sum(res["room_revenue"] for res in day_results) / total_available_nights if total_available_nights else 0.0, 2),
        }
        return day_results, summary

    def compute_arrivals(self, date, company_id=None, property_id=False):
        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)
        bookings = self.env["hotel.book.history"].search(
            self._booking_domain(start_dt, end_dt, company_id, property_id) + [("check_in", ">=", start_dt), ("check_in", "<=", end_dt)]
        )
        return bookings

    def compute_departures(self, date, company_id=None, property_id=False):
        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)
        bookings = self.env["hotel.book.history"].search(
            self._booking_domain(start_dt, end_dt, company_id, property_id) + [("check_out", ">=", start_dt), ("check_out", "<=", end_dt)]
        )
        return bookings

    def compute_stayovers(self, date, company_id=None, property_id=False):
        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)
        bookings = self.env["hotel.book.history"].search(self._booking_domain(start_dt, end_dt, company_id, property_id))
        return bookings.filtered(lambda b: b.check_in and b.check_out and b.check_in.date() < date < b.check_out.date())

    def compute_revenue(self, date, company_id=None, property_id=False):
        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)
        orders = self.env["sale.order"].search(self._sale_domain(start_dt, end_dt, company_id, property_id))
        return self._split_revenue(orders)

    def compute_channel_breakdown(self, date_from, date_to, company_id=None, property_id=False):
        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to, time.max)
        bookings = self.env["hotel.book.history"].search(self._booking_domain(start_dt, end_dt, company_id, property_id))
        channels = defaultdict(lambda: {"nights": 0.0, "revenue": 0.0})
        for booking in bookings:
            # channel_name = booking.booking_source_id.name if booking.booking_source_id else "Direct"
            channel_name = "Direct"
            channels[channel_name]["nights"] += booking.duration_days_decimal or 0.0
            channels[channel_name]["revenue"] += booking.total_amount or 0.0
        return [{"channel": name, **vals} for name, vals in channels.items()]

    def compute_market_breakdown(self, date_from, date_to, company_id=None, property_id=False):
        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to, time.max)
        bookings = self.env["hotel.book.history"].search(self._booking_domain(start_dt, end_dt, company_id, property_id))
        markets = defaultdict(lambda: {"nights": 0.0, "revenue": 0.0})
        for booking in bookings:
            country = booking.partner_id.country_id.name if booking.partner_id and booking.partner_id.country_id else "Unknown"
            markets[country]["nights"] += booking.duration_days_decimal or 0.0
            markets[country]["revenue"] += booking.total_amount or 0.0
        return [{"market": name, **vals} for name, vals in markets.items()]

    def compute_room_type_breakdown(self, date_from, date_to, company_id=None, property_id=False):
        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to, time.max)
        bookings = self.env["hotel.book.history"].search(self._booking_domain(start_dt, end_dt, company_id, property_id))
        room_types = defaultdict(lambda: {"nights": 0.0, "revenue": 0.0})
        for booking in bookings:
            room_type_name = self._safe_room_type_name(booking)
            room_types[room_type_name]["nights"] += booking.duration_days_decimal or 0.0
            room_types[room_type_name]["revenue"] += booking.total_amount or 0.0
        return [{"room_type": name, **vals} for name, vals in room_types.items()]

    def _safe_room_type_name(self, booking):
        """Return a room type name without triggering access errors.

        Some users may not have access to the product templates backing the room
        types (multi-company rules). Accessing ``display_name`` on the
        ``room_type_id``/``room_id`` then raises an AccessError while rendering
        the report. Using ``sudo`` bypasses the record rules purely for display
        purposes and avoids breaking the report.
        """

        for record in (booking.room_type_id, booking.room_id):
            if record:
                try:
                    return record.sudo().display_name
                except AccessError:
                    continue
        return _("Unspecified")

    def compute_payment_method_breakdown(self, date_from, date_to, company_id=None, property_id=False):
        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to, time.max)
        orders = self.env["sale.order"].search(self._sale_domain(start_dt, end_dt, company_id, property_id))
        payment_methods = defaultdict(lambda: {"nights": 0.0, "revenue": 0.0, "orders": 0})

        for order in orders:
            nights = sum(order.hotel_book_history_ids.mapped("duration_days_decimal")) or 0.0
            payments_found = False
            invoices = order.invoice_ids.filtered(lambda inv: inv.state == "posted")
            for invoice in invoices:
                widget = invoice.invoice_payments_widget
                if widget:
                    data = widget
                    if isinstance(widget, str):
                        try:
                            data = json.loads(widget)
                        except Exception:
                            data = {}
                    for line in data.get("content", []) if isinstance(data, dict) else []:
                        method_name = line.get("payment_method_name") or "Unspecified"
                        amount = line.get("amount") or 0.0
                        payment_methods[method_name]["nights"] += nights
                        payment_methods[method_name]["revenue"] += amount
                        payment_methods[method_name]["orders"] += 1
                        payments_found = True
            if not payments_found:
                payment_methods["Unspecified"]["nights"] += nights
                payment_methods["Unspecified"]["revenue"] += order.amount_total or 0.0
                payment_methods["Unspecified"]["orders"] += 1

        return [{"payment_method": name, **vals} for name, vals in payment_methods.items()]

    def compute_room_type_profitability(self, date_from, date_to, company_id=None, property_id=False):
        """Matrix of Occ %, ADR, RevPAR, and Revenue Share by Room Type."""
        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to, time.max)
        days_count = (date_to - date_from).days + 1
        
        bookings = self.env["hotel.book.history"].search(self._booking_domain(start_dt, end_dt, company_id, property_id))
        total_revenue = sum(bookings.mapped("total_amount"))
        
        # Get rooms by type
        rooms = self._rooms(company_id, property_id)
        rooms_by_type = defaultdict(list)
        for room in rooms:
            rooms_by_type[room.room_type.id].append(room)
            
        profitability = []
        for type_id, type_rooms in rooms_by_type.items():
            type_name = type_rooms[0].room_type.display_name
            type_bookings = bookings.filtered(lambda b: b.room_type_id.id == type_id)
            
            nights_sold = sum(type_bookings.mapped("duration_days_decimal"))
            revenue = sum(type_bookings.mapped("total_amount"))
            total_available_nights = len(type_rooms) * days_count
            
            profitability.append({
                "room_type": type_name,
                "occ_pct": (nights_sold / total_available_nights * 100.0) if total_available_nights else 0.0,
                "adr": revenue / nights_sold if nights_sold else 0.0,
                "revpar": revenue / total_available_nights if total_available_nights else 0.0,
                "revenue": revenue,
                "revenue_share": (revenue / total_revenue * 100.0) if total_revenue else 0.0,
            })
        return profitability

    def compute_lead_time_analytics(self, date_from, date_to, company_id=None, property_id=False):
        """Calculate lead time buckets (0-3, 4-7, 8-14, 15-30, 30+)."""
        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to, time.max)
        bookings = self.env["hotel.book.history"].search(self._booking_domain(start_dt, end_dt, company_id, property_id))
        
        buckets = {
            "0-3 Days": 0,
            "4-7 Days": 0,
            "8-14 Days": 0,
            "15-30 Days": 0,
            "30+ Days": 0
        }
        total_lead_time = 0
        count = 0

        for b in bookings:
            if b.check_in and b.create_date:
                lead_time = (b.check_in - b.create_date).days
                lead_time = max(lead_time, 0)
                total_lead_time += lead_time
                count += 1
                
                if lead_time <= 3:
                    buckets["0-3 Days"] += 1
                elif lead_time <= 7:
                    buckets["4-7 Days"] += 1
                elif lead_time <= 14:
                    buckets["8-14 Days"] += 1
                elif lead_time <= 30:
                    buckets["15-30 Days"] += 1
                else:
                    buckets["30+ Days"] += 1
        
        avg_lead_time = total_lead_time / count if count else 0.0
        return {
            "avg_lead_time": round(avg_lead_time, 1),
            "total_bookings": count,
            "buckets": buckets
        }

    def compute_pickup_analysis(self, target_date, company_id=None, property_id=False):
        """Analyze bookings created on target_date vs previous periods (Pace)."""
        start_dt = datetime.combine(target_date, time.min)
        end_dt = datetime.combine(target_date, time.max)
        
        def count_sales(s_dt, e_dt):
            return self.env["hotel.book.history"].search_count([
                ("create_date", ">=", s_dt),
                ("create_date", "<=", e_dt),
                ("state", "!=", "cancelled"),
            ] + ([("company_id", "=", company_id)] if company_id else []))

        # Today
        today_count = count_sales(start_dt, end_dt)
        
        # Same day last week
        last_week_dt = target_date - timedelta(days=7)
        last_week_count = count_sales(datetime.combine(last_week_dt, time.min), datetime.combine(last_week_dt, time.max))
        
        # Same day last month
        last_month_dt = target_date - timedelta(days=30) # Approx
        last_month_count = count_sales(datetime.combine(last_month_dt, time.min), datetime.combine(last_month_dt, time.max))
        
        # Pace calculation
        pace_week = ((today_count - last_week_count) / last_week_count * 100) if last_week_count else 0.0
        pace_month = ((today_count - last_month_count) / last_month_count * 100) if last_month_count else 0.0

        return {
            "pickup_date": target_date,
            "today_count": today_count,
            "last_week_count": last_week_count,
            "last_month_count": last_month_count,
            "pace_week": round(pace_week, 1),
            "pace_month": round(pace_month, 1),
        }

    def compute_cash_flow_metrics(self, company_id):
        """Calculate Cash on Hand, Receivables, Payables for Owner Insight."""
        # This requires access to account.move generic logic
        # Simplified for now:
        # Cash: Balance of Bank/Cash journals
        # AR: Accounts Receivable balance
        # AP: Accounts Payable balance
        
        ml_model = self.env['account.move.line']
        today = fields.Date.today()
        
        # Cash on Hand (Bank + Cash)
        liquidity_accounts = self.env['account.account'].search([
            ('account_type', '=', 'asset_cash'),
            ('company_id', '=', company_id)
        ])
        cash_balance = 0.0
        if liquidity_accounts:
            # Sum balance of these accounts
             # Optimization: use read_group
             res = ml_model.read_group(
                 [('account_id', 'in', liquidity_accounts.ids), ('parent_state', '=', 'posted')],
                 ['balance'],
                 []
             )
             cash_balance = res[0]['balance'] if res else 0.0

        # Accounts Receivable (Customer Invoices unpaid)
        ar_balance = 0.0
        ar_accounts = self.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
            ('company_id', '=', company_id)
        ])
        if ar_accounts:
             res = ml_model.read_group(
                 [('account_id', 'in', ar_accounts.ids), ('parent_state', '=', 'posted'), ('reconciled', '=', False)],
                 ['amount_residual'],
                 []
             )
             ar_balance = res[0]['amount_residual'] if res else 0.0

        # Accounts Payable (Vendor Bills unpaid)
        ap_balance = 0.0
        ap_accounts = self.env['account.account'].search([
            ('account_type', '=', 'liability_payable'),
            ('company_id', '=', company_id)
        ])
        if ap_accounts:
             res = ml_model.read_group(
                 [('account_id', 'in', ap_accounts.ids), ('parent_state', '=', 'posted'), ('reconciled', '=', False)],
                 ['amount_residual'],
                 []
             )
             ap_balance = res[0]['amount_residual'] if res else 0.0 # Typically negative credit

        return {
            "cash_on_hand": cash_balance,
            "receivables": ar_balance,
            "payables": abs(ap_balance),
            "net_position": cash_balance + ar_balance + ap_balance # ap_balance is usually negative usage
        }

    def compute_risk_score(self, date, company_id):
        """Calculate Risk Scores (0-100) for Executive Dashboard."""
        # 1. Revenue Risk: Low Occupancy?
        # 2. Operational Risk: High Dirty rooms?
        # 3. Cash Risk: Low Cash vs AP?
        
        # Revenue Risk
        kpi = self.compute_day_kpis(date, company_id)
        occ = kpi['occupancy_pct']
        rev_risk = 0
        if occ < 30: rev_risk = 80 # High Risk
        elif occ < 50: rev_risk = 50 # Medium
        elif occ < 70: rev_risk = 20 # Low
        else: rev_risk = 5 # Very Low

        # Operational Risk
        alerts = self.compute_operational_alerts(date, company_id)
        total_alerts = alerts['total_alerts']
        ops_risk = min(total_alerts * 10, 100) # 10 alerts = 100% risk

        # Cash Risk
        cf = self.compute_cash_flow_metrics(company_id)
        cash = cf['cash_on_hand']
        payables = cf['payables']
        cash_risk = 50
        if payables > 0:
            ratio = cash / payables
            if ratio < 0.5: cash_risk = 90 # Critical
            elif ratio < 1.0: cash_risk = 60 # Warning
            else: cash_risk = 10 # Healthy
        
        return {
            "revenue_risk": rev_risk,
            "operational_risk": ops_risk,
            "cash_risk": cash_risk,
            "reputation_risk": 15, # Placeholder (needs reviews integration)
            "overall_score": (rev_risk + ops_risk + cash_risk) / 3
        }

    def compute_hk_efficiency(self, date, company_id):
        """Calculate rooms cleaned per HK staff."""
        # Requires tracking who cleaned what.
        # Assuming we can group rooms by 'cleaner_id' or similar if it exists,
        # otherwise we return a placeholder structure for now.
        return []

    def compute_operational_alerts(self, date, company_id=None):
        """Compute critical operational alerts for the day."""
        start_dt = datetime.combine(date, time.min)
        
        # 1. Dirty Arrivals
        arrivals = self.compute_arrivals(date, company_id)
        dirty_arrivals = len(arrivals.filtered(lambda b: b.room_id and b.room_id.state == 'dirty'))
                
        # 2. Pending Payments (Deposits Due)
        # Booking confirmed, future check-in, but invoice not fully paid
        # Simplification: bookings without "invoiced" state
        future_bookings = self.env["hotel.book.history"].search([
             ('state', '=', 'confirmed'),
             ('check_in', '>=', start_dt),
        ] + ([('company_id', '=', company_id)] if company_id else []))
        
        # Check if amount_residual > 0 on related invoices or order not fully invoiced
        pending_deposits_count = 0
        for b in future_bookings:
            # If no invoice or unpaid invoice
            if not b.invoice_ids or any(inv.payment_state != 'paid' for inv in b.invoice_ids):
                pending_deposits_count += 1
        
        # 3. Missing IDs
        in_house = self.compute_stayovers(date, company_id)
        all_active = in_house | arrivals
        missing_ids = 0
        for b in all_active:
            p = b.partner_id
            if not (p.ref or p.vat or p.email or p.phone): # Extended check
                 missing_ids += 1
                 
        # 4. Rooms OOO
        rooms = self._rooms(company_id)
        ooo_rooms = len(rooms.filtered(lambda r: r.state == 'out_of_order'))
        
        # 5. Maintenance Tickets
        # Count open maintenance requests for rooms
        maintenance_domain = [('stage_id.done', '=', False)]
        if company_id:
            maintenance_domain.append(('company_id', '=', company_id))
        if 'hotel_room_id' in self.env['maintenance.request']._fields:
            maintenance_domain.append(('hotel_room_id', '!=', False))
            
        maintenance_tickets = self.env['maintenance.request'].search_count(maintenance_domain)

        return {
            "dirty_arrivals": dirty_arrivals,
            "pending_deposits": pending_deposits_count,
            "missing_ids": missing_ids,
            "ooo_rooms": ooo_rooms,
            "maintenance_tickets": maintenance_tickets,
            "total_alerts": dirty_arrivals + pending_deposits_count + missing_ids + ooo_rooms + maintenance_tickets
        }

    def normalize_snapshot_output(self, values):
        defaults = {
            "date": False,
            "total_rooms": 0,
            "occupied_rooms": 0,
            "available_rooms": 0,
            "maintenance_rooms": 0,
            "occupancy_pct": 0.0,
            "arrivals": 0,
            "departures": 0,
            "cancellations": 0,
            "nights_sold": 0,
            "adr": 0.0,
            "revpar": 0.0,
            "revenue": 0.0,
        }
        cleaned = defaults.copy()
        cleaned.update({k: (v or defaults.get(k)) for k, v in values.items() if k in defaults})
        for numeric in ["adr", "revpar", "occupancy_pct"]:
            cleaned[numeric] = round(cleaned.get(numeric, 0.0), 2)
        return cleaned
