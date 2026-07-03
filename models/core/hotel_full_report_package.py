import base64
import logging

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import pdf

_logger = logging.getLogger(__name__)


class HotelFullReportPackageWizard(models.TransientModel):
    _name = "ism.hotel.full.report.package.wizard"
    _description = "Hotel Full Report Package Wizard"

    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    booking_id = fields.Many2one("hotel.book.history", string="Booking")
    room_id = fields.Many2one("hotel.room", string="Room")
    cleaning_request_ids = fields.Many2many("cleaning.request", string="Cleaning Requests")
    hotel_dashboard_id = fields.Many2one("hotel.dashboard", string="Hotel Dashboard")
    mis_eod_id = fields.Many2one("hotel.mis.report.wizard", string="MIS EOD")

    include_grc = fields.Boolean(string="Guest Registration Card", default=True)
    include_booking_summary = fields.Boolean(string="Booking Summary", default=True)
    include_room_summary = fields.Boolean(string="Room Summary", default=True)
    include_cleaning = fields.Boolean(string="Cleaning Request Summary", default=True)
    include_mis_dashboard = fields.Boolean(string="MIS Dashboard", default=True)
    include_daily_status = fields.Boolean(string="Daily Status", default=True)
    include_eod = fields.Boolean(string="MIS End-of-Day", default=True)

    def _render_report(self, xml_id, res_ids):
        """Safely render a QWeb PDF report for the given xml_id and record(s)."""
        if not res_ids:
            return None

        if isinstance(res_ids, int):
            res_ids = [res_ids]
        elif isinstance(res_ids, models.Model):
            res_ids = res_ids.ids

        try:
            report_action = self.env.ref(xml_id)
        except ValueError:
            _logger.warning("Report xml_id %s not found for full package", xml_id)
            return None

        if not report_action:
            return None

        try:
            pdf_content, _ = report_action._render_qweb_pdf(res_ids)
        except Exception:
            _logger.exception("Failed to render report %s for ids %s", xml_id, res_ids)
            return None

        return pdf_content

    def action_print_full_package(self):
        """Generate and download the full hotel report package as a single merged PDF."""
        self.ensure_one()
        pdf_parts = []

        if self.include_grc and self.booking_id:
            pdf_content = self._render_report("atk_hotel.action_report_grc", self.booking_id.id)
            if pdf_content:
                pdf_parts.append(pdf_content)

        if self.include_booking_summary and self.booking_id:
            pdf_content = self._render_report(
                "atk_hotel.action_report_hotel_booking_summary_pdf", self.booking_id.id
            )
            if pdf_content:
                pdf_parts.append(pdf_content)

        room = self.room_id or self.booking_id.room_id
        if self.include_room_summary and room:
            pdf_content = self._render_report("atk_hotel.action_report_hotel_room_summary_pdf", room.id)
            if pdf_content:
                pdf_parts.append(pdf_content)

        if self.include_cleaning and self.cleaning_request_ids:
            pdf_content = self._render_report(
                "atk_hotel.action_report_cleaning_request_summary_pdf", self.cleaning_request_ids.ids
            )
            if pdf_content:
                pdf_parts.append(pdf_content)

        if self.include_mis_dashboard and self.hotel_dashboard_id:
            pdf_content = self._render_report(
                "atk_hotel.action_report_hotel_mis_dashboard_pdf", self.hotel_dashboard_id.id
            )
            if pdf_content:
                pdf_parts.append(pdf_content)

        if self.include_daily_status and self.hotel_dashboard_id:
            pdf_content = self._render_report(
                "atk_hotel.action_report_hotel_daily_status_pdf", self.hotel_dashboard_id.id
            )
            if pdf_content:
                pdf_parts.append(pdf_content)

        if self.include_eod and self.mis_eod_id:
            pdf_content = self._render_report("atk_hotel.action_report_hotel_mis_eod_pdf", self.mis_eod_id.id)
            if pdf_content:
                pdf_parts.append(pdf_content)

        if not pdf_parts:
            raise UserError(
                _("No reports could be generated for the selected options. Please check your selections and data.")
            )

        merged_pdf = pdf.merge_pdf(pdf_parts)
        filename = f"hotel_full_report_package_{self.date or fields.Date.context_today(self)}.pdf"

        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "mimetype": "application/pdf",
                "datas": base64.b64encode(merged_pdf).decode(),
                "res_model": self._name,
                "res_id": self.id,
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=1",
            "target": "self",
        }
