from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class HotelMISReportWizard(models.TransientModel):
    _name = "hotel.mis.report.wizard"
    _description = "Hotel MIS Report Wizard"

    period_preset = fields.Selection(
        selection=[
            ("today", "Today"),
            ("yesterday", "Yesterday"),
            ("this_week", "This Week"),
            ("last_week", "Last Week"),
            ("last_7_days", "Last 7 Days"),
            ("last_30_days", "Last 30 Days"),
            ("this_month", "This Month"),
            ("last_month", "Last Month"),
            ("custom", "Custom Range"),
        ],
        string="Period",
        required=True,
        default="today",
    )
    date_from = fields.Date(string="Start Date", required=True, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string="End Date", required=True, default=lambda self: fields.Date.context_today(self))
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    property_id = fields.Many2one("property.property", string="Property")
    report_audience = fields.Selection(
        selection=[("gm", "GM / Operations"), ("finance", "Finance / Accounting")],
        string="Report Audience",
        required=True,
        default="gm",
    )
    grouping_mode = fields.Selection(
        selection=[("day", "Group by Day"), ("reservation", "Detailed Reservations")],
        string="Group By",
        required=True,
        default="reservation",
    )
    include_reservation_appendix = fields.Boolean(string="Include detailed reservation list (appendix)", default=True)
    include_revenue_appendix = fields.Boolean(string="Include detailed revenue orders (appendix)", default=True)

    @api.onchange("period_preset")
    def _onchange_period_preset(self):
        today = fields.Date.context_today(self)
        if self.period_preset == "today":
            self.date_from = self.date_to = today
        elif self.period_preset == "yesterday":
            yesterday = today - timedelta(days=1)
            self.date_from = self.date_to = yesterday
        elif self.period_preset == "this_week":
            start = today - timedelta(days=today.weekday())
            self.date_from = start
            self.date_to = today
        elif self.period_preset == "last_week":
            start = today - timedelta(days=today.weekday() + 7)
            end = start + timedelta(days=6)
            self.date_from = start
            self.date_to = end
        elif self.period_preset == "last_7_days":
            self.date_from = today - timedelta(days=6)
            self.date_to = today
        elif self.period_preset == "last_30_days":
            self.date_from = today - timedelta(days=29)
            self.date_to = today
        elif self.period_preset == "this_month":
            start = today.replace(day=1)
            self.date_from = start
            self.date_to = today
        elif self.period_preset == "last_month":
            start = (today.replace(day=1) - relativedelta(months=1))
            end = start + relativedelta(day=31)
            self.date_from = start
            self.date_to = end
        else:
            # Custom range: leave dates untouched so the user can set them manually
            return

    # ------------------------------------------------------------------
    # Bounds & domains
    # ------------------------------------------------------------------
    def _get_period_bounds(self):
        self.ensure_one()
        start_date = self.date_from or fields.Date.context_today(self)
        end_date = self.date_to or start_date
        if end_date < start_date:
            end_date = start_date
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)
        return start_date, end_date, start_dt, end_dt

    def _engine(self):
        return self.env["hotel.kpi.engine"]

    # ------------------------------------------------------------------
    # KPI helpers
    # ------------------------------------------------------------------
    def get_daily_snapshot(self):
        start_date, end_date, _start_dt, _end_dt = self._get_period_bounds()
        engine = self._engine()
        snapshot_model = self.env["hotel.mis.snapshot"]
        snapshot_model.generate_range(start_date, end_date, self.company_id.id, self.property_id.id if self.property_id else False)
        snapshots = snapshot_model.get_range(start_date, end_date, self.company_id.id, self.property_id.id if self.property_id else False)
        lines = []
        for rec in snapshots:
            lines.append(
                engine.normalize_snapshot_output(
                    {
                        "date": rec.snapshot_date,
                        "total_rooms": rec.total_rooms,
                        "occupied_rooms": rec.occupied_rooms,
                        "available_rooms": rec.available_rooms,
                        "maintenance_rooms": rec.maintenance_rooms,
                        "occupancy_pct": rec.occupancy_pct,
                        "arrivals": rec.arrivals,
                        "departures": rec.departures,
                        "cancellations": rec.cancellations,
                        "nights_sold": rec.nights_sold,
                        "adr": rec.avg_daily_rate,
                        "revpar": rec.revpar,
                        "revenue": rec.revenue_amount,
                    }
                )
            )
        return lines

    def get_period_kpis(self):
        start_date, end_date, _start_dt, _end_dt = self._get_period_bounds()
        day_lines, summary = self._engine().compute_range_kpis(
            start_date, end_date, self.company_id.id, self.property_id.id if self.property_id else False
        )
        return summary, day_lines

    def get_today_movements(self):
        _start_date, end_date, _start_dt, _end_dt = self._get_period_bounds()
        engine = self._engine()
        arrivals = engine.compute_arrivals(end_date, self.company_id.id, self.property_id.id if self.property_id else False)
        departures = engine.compute_departures(end_date, self.company_id.id, self.property_id.id if self.property_id else False)
        stayovers = engine.compute_stayovers(end_date, self.company_id.id, self.property_id.id if self.property_id else False)
        return {
            "arrivals": arrivals,
            "departures": departures,
            "stayovers": stayovers,
            "header": {
                "arrivals": len(arrivals),
                "departures": len(departures),
                "stayovers": len(stayovers),
            },
        }

    def get_revenue_breakdown(self):
        start_date, end_date, _start_dt, _end_dt = self._get_period_bounds()
        _, summary = self._engine().compute_range_kpis(
            start_date, end_date, self.company_id.id, self.property_id.id if self.property_id else False
        )
        total_revenue = summary.get("total_revenue", 0.0)
        room_revenue = summary.get("room_revenue", 0.0)
        extra_revenue = summary.get("extra_revenue", 0.0)
        tax_amount = summary.get("tax_amount", 0.0)
        discount_amount = summary.get("discount_amount", 0.0)
        return {
            "room_revenue": room_revenue,
            "extra_revenue": extra_revenue,
            "tax_amount": tax_amount,
            "discount_amount": discount_amount,
            "total_revenue": total_revenue,
            "sellable_nights": summary.get("sellable_nights", 0.0),
            "unsold_nights": summary.get("unsold_nights", 0.0),
        }

    def get_channel_breakdown(self):
        start_date, end_date, _start_dt, _end_dt = self._get_period_bounds()
        return self._engine().compute_channel_breakdown(
            start_date, end_date, self.company_id.id, self.property_id.id if self.property_id else False
        )

    def get_market_breakdown(self):
        start_date, end_date, _start_dt, _end_dt = self._get_period_bounds()
        return self._engine().compute_market_breakdown(
            start_date, end_date, self.company_id.id, self.property_id.id if self.property_id else False
        )

    def get_room_type_breakdown(self):
        start_date, end_date, _start_dt, _end_dt = self._get_period_bounds()
        return self._engine().compute_room_type_breakdown(
            start_date, end_date, self.company_id.id, self.property_id.id if self.property_id else False
        )

    def get_payment_method_breakdown(self):
        start_date, end_date, _start_dt, _end_dt = self._get_period_bounds()
        return self._engine().compute_payment_method_breakdown(
            start_date, end_date, self.company_id.id, self.property_id.id if self.property_id else False
        )

    # ------------------------------------------------------------------
    # Legacy compatibility wrappers
    # ------------------------------------------------------------------
    def get_eod_payload(self):
        self.ensure_one()
        start_date, end_date, start_dt, end_dt = self._get_period_bounds()
        summary, daily_lines = self.get_period_kpis()
        revenue_data = self.get_revenue_breakdown()
        today_movements = self.get_today_movements()
        booking_domain = self._engine()._booking_domain(
            start_dt, end_dt, self.company_id.id, self.property_id.id if self.property_id else False
        )
        bookings = self.env["hotel.book.history"].search(booking_domain)
        sales = self.env["sale.order"].search(
            self._engine()._sale_domain(start_dt, end_dt, self.company_id.id, self.property_id.id if self.property_id else False)
        )

        appendix_grouped = []
        if self.grouping_mode == "day":
            totals_by_date = {}
            for booking in bookings:
                if not booking.check_in or not booking.check_out:
                    continue
                overlap_start = max(booking.check_in.date(), start_date)
                overlap_end = min(booking.check_out.date(), end_date)
                if overlap_end < overlap_start:
                    continue
                nights_in_range = (overlap_end - overlap_start).days
                if nights_in_range <= 0:
                    continue
                per_night_amount = (booking.total_amount or 0.0) / booking.duration_days_decimal if booking.duration_days_decimal else 0.0
                for offset in range(nights_in_range):
                    day = overlap_start + timedelta(days=offset)
                    day_totals = totals_by_date.setdefault(day, {"reservations_count": 0, "nights": 0.0, "amount": 0.0})
                    day_totals["reservations_count"] += 1
                    day_totals["nights"] += 1
                    day_totals["amount"] += per_night_amount
            appendix_grouped = [
                {"date": day, **values} for day, values in sorted(totals_by_date.items(), key=lambda item: item[0])
            ]

        payload = {
            "start_date": start_date,
            "end_date": end_date,
            "snapshots": self.get_daily_snapshot(),
            "summary": summary,
            "arrivals_today": today_movements.get("arrivals", self.env["hotel.book.history"]),
            "departures_today": today_movements.get("departures", self.env["hotel.book.history"]),
            "stayovers_today": today_movements.get("stayovers", self.env["hotel.book.history"]),
            "channel_breakdown": self.get_channel_breakdown(),
            "market_breakdown": self.get_market_breakdown(),
            "room_type_breakdown": self.get_room_type_breakdown(),
            "payment_method_breakdown": self.get_payment_method_breakdown(),
            "revenue_data": revenue_data,
            "bookings": bookings,
            "sales": sales,
            "daily_lines": daily_lines,
            "grouping_mode": self.grouping_mode,
            "period_preset": self.period_preset,
            "period_label": self._get_period_preset_label(),
            "appendix_grouped": appendix_grouped,
        }
        return payload

    def _prepare_report_data(self):
        self.ensure_one()
        return {
            "date_from": self.date_from,
            "date_to": self.date_to,
            "company_id": self.company_id.id,
            "property_id": self.property_id.id if self.property_id else False,
            "report_audience": self.report_audience,
            "period_preset": self.period_preset,
            "grouping_mode": self.grouping_mode,
            "include_reservation_appendix": self.include_reservation_appendix,
            "include_revenue_appendix": self.include_revenue_appendix,
        }

    def _get_period_preset_label(self):
        self.ensure_one()
        presets = dict(self._fields["period_preset"].selection)
        return presets.get(self.period_preset)

    def _ensure_report_action(self, xmlid, name, report_type):
        report_action = self.env.ref(xmlid, raise_if_not_found=False)
        if report_action:
            return report_action

        model = self.env["ir.model"].search([("model", "=", self._name)], limit=1)
        report_action = self.env["ir.actions.report"].create(
            {
                "name": name,
                "model": self._name,
                "report_name": "atk_hotel.report_hotel_mis_eod_document",
                "report_file": "atk_hotel.report_hotel_mis_eod_document",
                "report_type": report_type,
                "binding_model_id": model.id if model else False,
                "binding_type": "report",
                "print_report_name": "object._get_report_filename('%s')" % report_type,
            }
        )

        self.env["ir.model.data"].create(
            {
                "module": "atk_hotel",
                "name": xmlid.split(".")[-1],
                "model": "ir.actions.report",
                "res_id": report_action.id,
            }
        )

        return report_action

    def _get_report_filename(self, report_type):
        self.ensure_one()
        suffix = "GM" if self.report_audience == "gm" else "Fin"
        date_label = (self.date_to or fields.Date.context_today(self)).strftime("%d.%m.%Y")
        base = f"Hotel EOD {suffix} {date_label}"
        if report_type == "qweb-pdf":
            return base + ".pdf"
        if report_type == "qweb-html":
            return base
        return base

    # ------------------------------------------------------------------
    # Report actions
    # ------------------------------------------------------------------
    def action_print_pdf(self):
        self.ensure_one()
        action = self._ensure_report_action(
            "atk_hotel.action_report_hotel_mis_eod_pdf",
            "Hotel End of Day",
            "qweb-pdf",
        )
        return action.report_action(self, data=self._prepare_report_data())

    def action_print_html(self):
        self.ensure_one()
        action = self._ensure_report_action(
            "atk_hotel.action_report_hotel_mis_eod_html",
            "Hotel End of Day (HTML)",
            "qweb-html",
        )
        return action.report_action(self, data=self._prepare_report_data())

    def action_print_gm_eod_pdf(self):
        self.ensure_one()
        self.report_audience = "gm"
        return self.action_print_pdf()

    def action_print_finance_eod_pdf(self):
        self.ensure_one()
        self.report_audience = "finance"
        return self.action_print_pdf()

    def action_print_gm_eod_html(self):
        self.ensure_one()
        self.report_audience = "gm"
        return self.action_print_html()

    def action_print_finance_eod_html(self):
        self.ensure_one()
        self.report_audience = "finance"
        return self.action_print_html()

    def action_view_snapshot(self):
        self.ensure_one()
        return {
            "name": _("Daily Snapshot"),
            "type": "ir.actions.act_window",
            "res_model": "hotel.mis.snapshot",
            "view_mode": "list,graph,pivot",
            "domain": [
                ("snapshot_date", ">=", self.date_from),
                ("snapshot_date", "<=", self.date_to),
                ("company_id", "=", self.company_id.id),
            ],
            "target": "current",
            "context": {"default_company_id": self.company_id.id},
        }
