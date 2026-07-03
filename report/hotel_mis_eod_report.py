from odoo import models
from odoo.tools import float_repr, formatLang, format_date, format_datetime


class ReportHotelMISEndOfDayV2(models.AbstractModel):
    _inherit = "report.atk_hotel.report_hotel_mis_eod_document"

    def _get_report_values(self, docids, data=None):
        wizard_ids = docids or []
        if data:
            wizard_ids = wizard_ids or data.get("docids") or data.get("ids")
        wizard_ids = wizard_ids or self.env.context.get("active_ids")

        wizards = self.env["hotel.mis.report.wizard"].browse(wizard_ids)
        if not wizards:
            return {}

        return {
            "doc_ids": wizard_ids,
            "doc_model": "hotel.mis.report.wizard",
            "docs": wizards,
            "currency": self.env.company.currency_id,
            "format_date": lambda date, **kwargs: format_date(self.env, date, **kwargs),
            "format_datetime": lambda dt, **kwargs: format_datetime(self.env, dt, **kwargs),
            "format_float": lambda value, precision=2: float_repr(value or 0.0, precision),
            "formatLang": lambda value, currency_obj=None, **kwargs: formatLang(
                self.env, value or 0.0, currency_obj=currency_obj or self.env.company.currency_id, **kwargs
            ),
        }

    def _get_report_base_filename(self, docids, data):
        wizard_ids = docids or []
        if data:
            wizard_ids = wizard_ids or data.get("docids") or data.get("ids")
        wizard_ids = wizard_ids or self.env.context.get("active_ids")
        wizard = self.env["hotel.mis.report.wizard"].browse(wizard_ids[:1])
        if wizard:
            suffix = "Fin" if wizard.report_audience == "finance" else "GM"
            date_label = (wizard.date_to or wizard.date_from).strftime("%d.%m.%Y")
            return f"Hotel EOD {suffix} {date_label}"
        return super()._get_report_base_filename(docids, data)
