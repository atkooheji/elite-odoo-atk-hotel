from odoo import fields, models
from odoo.tools import float_repr, formatLang, format_date, format_datetime


class ReportHotelMISDashboard(models.AbstractModel):
    _name = 'report.atk_hotel.report_hotel_mis_dashboard_document'
    _description = 'Hotel MIS Dashboard Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['hotel.dashboard'].browse(docids)
        company_currency = self.env.company.currency_id
        today = fields.Date.context_today(self)
        report_data = []

        for dashboard in docs:
            start_dt, end_dt, label = dashboard._get_period_bounds(today)
            metrics = self.env['hotel.dashboard'].get_metrics_for_period(start_dt, end_dt)
            report_data.append({
                'dashboard': dashboard,
                'metrics': metrics,
                'period_label': label,
                'start_dt': start_dt,
                'end_dt': end_dt,
            })

        return {
            'doc_ids': docids,
            'doc_model': 'hotel.dashboard',
            'docs': docs,
            'report_data': report_data,
            'currency': company_currency,
            'format_float': lambda value, precision=2: float_repr(value or 0.0, precision),
        }


class ReportHotelMISEndOfDay(models.AbstractModel):
    _name = 'report.atk_hotel.report_hotel_mis_eod_document'
    _description = 'Hotel MIS End of Day Report'

    def _get_report_values(self, docids, data=None):
        wizard_ids = docids or []
        if data:
            wizard_ids = wizard_ids or data.get('docids') or data.get('ids')
        wizard_ids = wizard_ids or self.env.context.get('active_ids')

        wizards = self.env['hotel.mis.report.wizard'].browse(wizard_ids)
        if not wizards:
            return {}

        return {
            'doc_ids': wizard_ids,
            'doc_model': 'hotel.mis.report.wizard',
            'docs': wizards,
            'currency': self.env.company.currency_id,
            'format_date': lambda date, **kwargs: format_date(self.env, date, **kwargs),
            'format_datetime': lambda dt, **kwargs: format_datetime(self.env, dt, **kwargs),
            'format_float': lambda value, precision=2: float_repr(value or 0.0, precision),
            'formatLang': lambda value, currency_obj=None, **kwargs: formatLang(
                self.env, value or 0.0, currency_obj=currency_obj or self.env.company.currency_id, **kwargs
            ),
        }
