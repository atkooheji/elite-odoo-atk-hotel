from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
import base64

from odoo import _, api, fields, models


class HotelReportKitWizard(models.TransientModel):
    _name = "hotel.report.kit.wizard"
    _description = "Al Faris Intelligence Kit Report Wizard"

    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)

    report_type = fields.Selection(
        selection=[
            ("daily", "Daily Operations Report"),
            ("weekly", "Weekly Performance Report"),
            ("monthly", "Monthly Owner Report"),
            ("quarterly", "Quarterly Strategic Report"),
            ("mis", "Legacy: MIS Dashboard"),
            ("eod", "Legacy: End of Day"),
            ("grc", "Legacy: Guest Registration Card"),
            ("booking_summary", "Legacy: Reservation Summary"),
            ("room_summary", "Legacy: Room Summary"),
        ],
        string="Report Type",
        required=True,
        default="daily",
    )
    period_preset = fields.Selection(
        selection=[
            ("today", "Today"),
            ("yesterday", "Yesterday"),
            ("week", "This Week"),
            ("last_week", "Last Week"),
            ("month", "This Month"),
            ("last_month", "Last Month"),
            ("quarter", "This Quarter"),
            ("last_quarter", "Last Quarter"),
            ("year", "This Year"),
            ("last_year", "Last Year"),
            ("custom", "Custom Range"),
        ],
        string="Period",
        default="today",
    )
    date_from = fields.Date(string="Start Date", default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string="End Date", default=lambda self: fields.Date.context_today(self))
    
    booking_id = fields.Many2one("hotel.book.history", string="Reservation")
    room_id = fields.Many2one("hotel.room", string="Room")
    
    output_format = fields.Selection(
        selection=[("pdf", "PDF (Branded)"), ("xlsx", "Excel (Raw Data)")],
        string="Output Format",
        required=True,
        default="pdf",
    )

    @api.onchange("report_type")
    def _onchange_report_type(self):
        if not self.report_type:
            return
        if self.report_type == "daily":
            self.period_preset = "today"
        elif self.report_type == "weekly":
            self.period_preset = "last_week"
        elif self.report_type == "monthly":
            self.period_preset = "last_month"
        elif self.report_type == "quarterly":
            self.period_preset = "last_quarter"
        
        # Trigger date update
        self._onchange_period_preset()

    @api.onchange("period_preset")
    def _onchange_period_preset(self):
        today = fields.Date.context_today(self)
        if self.period_preset == "today":
            self.date_from = self.date_to = today
        elif self.period_preset == "yesterday":
            yesterday = today - timedelta(days=1)
            self.date_from = self.date_to = yesterday
        elif self.period_preset == "week":
            # 7 days including today
            self.date_from = today - timedelta(days=6)
            self.date_to = today
        elif self.period_preset == "this_week":
            # Traditional Odoo week (Monday to Today)
            start = today - timedelta(days=today.weekday())
            self.date_from = start
            self.date_to = today
        elif self.period_preset == "last_week":
            # Previous 7 days
            self.date_from = today - timedelta(days=13)
            self.date_to = today - timedelta(days=7)
        elif self.period_preset == "month":
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
        elif self.period_preset == "quarter":
            month = (today.month - 1) // 3 * 3 + 1
            self.date_from = today.replace(month=month, day=1)
            self.date_to = today
        elif self.period_preset == "last_quarter":
            month = (today.month - 1) // 3 * 3 + 1
            first_day_this_q = today.replace(month=month, day=1)
            last_day_last_q = first_day_this_q - timedelta(days=1)
            m_prev = (last_day_last_q.month - 1) // 3 * 3 + 1
            self.date_from = last_day_last_q.replace(month=m_prev, day=1)
            self.date_to = last_day_last_q
        elif self.period_preset == "year":
            self.date_from = today.replace(month=1, day=1)
            self.date_to = today
        elif self.period_preset == "last_year":
            last_y = today.year - 1
            self.date_from = today.replace(year=last_y, month=1, day=1)
            self.date_to = today.replace(year=last_y, month=12, day=31)

    def _get_day_kpi_data(self):
        """Fetch KPI data for a single day (Daily Report)."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine.compute_day_kpis(self.date_from, self.company_id.id)

    def _get_period_data(self):
        """Fetch summarized data for a period (Weekly/Monthly/Quarterly)."""
        kpi_engine = self.env["hotel.kpi.engine"]
        res_list, summary = kpi_engine.compute_range_kpis(self.date_from, self.date_to, self.company_id.id)
        return {"summary": summary, "daily_data": res_list}

    def _get_operational_alerts(self):
        """Fetch operational alerts for the Daily Report."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine.compute_operational_alerts(self.date_from, self.company_id.id)

    def _get_channel_performance(self):
        """Fetch channel breakdown for Weekly Report."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine.compute_channel_breakdown(self.date_from, self.date_to, self.company_id.id)

    def _get_room_type_performance(self):
        """Fetch room type profitability for Weekly/Monthly Reports."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine.compute_room_type_profitability(self.date_from, self.date_to, self.company_id.id)

    def _get_expense_breakdown(self):
        """Fetch expense breakdown for Monthly Report."""
        kpi_engine = self.env["hotel.kpi.engine"]
        return kpi_engine._get_operating_expenses(
            datetime.combine(self.date_from, time.min),
            datetime.combine(self.date_to, time.max),
            self.company_id.id
        )

    def action_generate_report(self):
        self.ensure_one()
        
        # New Tiered reports (Daily, Weekly, Monthly, Quarterly)
        if self.report_type == "daily":
             return self.env.ref("atk_hotel.action_report_hotel_daily").report_action(self)
        if self.report_type == "weekly":
             return self.env.ref("atk_hotel.action_report_hotel_weekly").report_action(self)
        if self.report_type == "monthly":
             return self.env.ref("atk_hotel.action_report_hotel_monthly").report_action(self)
        if self.report_type == "quarterly":
             return self.env.ref("atk_hotel.action_report_hotel_quarterly").report_action(self)

        if self.report_type == "grc":
            if not self.booking_id:
                return
            return self.env.ref("atk_hotel.action_report_grc").report_action(self.booking_id)

        if self.report_type == "booking_summary":
            if not self.booking_id:
                return
            return self.env.ref("atk_hotel.action_report_hotel_booking_summary_pdf").report_action(self.booking_id)

        if self.report_type == "room_summary":
            if not self.room_id:
                return
            return self.env.ref("atk_hotel.action_report_hotel_room_summary_pdf").report_action(self.room_id)

        if self.report_type == "mis":
            return self.env.ref("atk_hotel.action_report_hotel_mis_dashboard_pdf").report_action(self, data={
                'date_from': self.date_from,
                'date_to': self.date_to,
                'period_preset': self.period_preset,
            })

        if self.report_type == "eod":
            return self.env.ref("atk_hotel.action_report_hotel_mis_eod_pdf").report_action(self, data={
                'date_from': self.date_from,
                'date_to': self.date_to,
                'period_preset': self.period_preset,
            })

        return True

    @api.model
    def cron_send_daily_intelligence_kit(self):
        """Automated daily dispatch of the Daily Operations Report."""
        today = fields.Date.context_today(self)
        yesterday = today - timedelta(days=1)
        
        recipients = self.env['res.partner'].search([
            ('receives_daily_intel_report', '=', True),
            ('email', '!=', False)
        ])
        if not recipients:
            return True
            
        companies = recipients.mapped('company_id') or self.env.companies
        for company in companies:
            wiz = self.create({
                'report_type': 'daily',
                'period_preset': 'yesterday',
                'date_from': yesterday,
                'date_to': yesterday,
                'company_id': company.id,
                'output_format': 'pdf'
            })
            
            # Use the new Daily Report action
            report = self.env.ref("atk_hotel.action_report_hotel_daily")
            pdf_content, _ = report._render_qweb_pdf([wiz.id])
            attachment = self.env['ir.attachment'].create({
                'name': f"Daily_Operations_{yesterday}.pdf",
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'res.partner',
                'mimetype': 'application/pdf'
            })
            
            # Send Emails
            template = self.env.ref("atk_hotel.mail_template_daily_intelligence_kit")
            company_recipients = recipients.filtered(lambda r: not r.company_id or r.company_id == company)
            for partner in company_recipients:
                template.send_mail(
                    partner.id, 
                    email_values={'attachment_ids': [(6, 0, [attachment.id])]},
                    force_send=True
                )
        return True
