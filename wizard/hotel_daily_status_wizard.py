from odoo import api, fields, models
from odoo.exceptions import UserError


class HotelDailyStatusWizard(models.TransientModel):
    _name = 'hotel.daily.status.wizard'
    _description = 'Hotel Daily Status Wizard'

    report_date = fields.Date(string='Report Date', default=fields.Date.context_today, required=True)

    def _prepare_report_data(self):
        self.ensure_one()
        return {'report_date': self.report_date}

    def _get_dashboard_record(self):
        """Return the singleton dashboard record or raise a user friendly error."""

        dashboard = self.env.ref(
            'atk_hotel.hotel_dashboard_record', raise_if_not_found=False
        )
        if not dashboard:
            raise UserError(
                'The Hotel Dashboard record is missing. Please update the module to recreate it.'
            )
        return dashboard

    @api.model
    def _ensure_report_action(self, xmlid, name, report_type):
        """Return the report action, recreating it if it was deleted."""

        action = self.env.ref(f"atk_hotel.{xmlid}", raise_if_not_found=False)
        if action:
            return action

        template = self.env.ref(
            "atk_hotel.report_hotel_daily_status_document", raise_if_not_found=False
        )
        if not template:
            raise UserError(
                "The Hotel Daily Status report template is missing. Please reinstall the module."
            )

        binding_model = self.env.ref(
            "atk_hotel.model_hotel_dashboard", raise_if_not_found=False
        )

        action = self.env["ir.actions.report"].create(
            {
                "name": name,
                "model": "hotel.dashboard",
                "report_name": "atk_hotel.report_hotel_daily_status_document",
                "report_file": "atk_hotel.report_hotel_daily_status_document",
                "report_type": report_type,
                "binding_model_id": binding_model.id if binding_model else False,
                "binding_type": "report",
                "print_report_name": "'Hotel Daily Status - %s' % (object.date_range_label or 'Today')",
            }
        )

        self.env["ir.model.data"].create(
            {
                "module": "atk_hotel",
                "name": xmlid,
                "model": "ir.actions.report",
                "res_id": action.id,
            }
        )

        return action

    def action_print_pdf(self):
        self.ensure_one()
        action = self._ensure_report_action(
            "action_report_hotel_daily_status_pdf",
            "Hotel Daily Status",
            "qweb-pdf",
        )
        return action.report_action(
            self._get_dashboard_record(),
            data=self._prepare_report_data(),
        )

    def action_print_html(self):
        self.ensure_one()
        action = self._ensure_report_action(
            "action_report_hotel_daily_status_html",
            "Hotel Daily Status (HTML)",
            "qweb-html",
        )
        return action.report_action(
            self._get_dashboard_record(),
            data=self._prepare_report_data(),
        )
