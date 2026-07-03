from datetime import timedelta

from odoo import _, api, fields, models


class HotelMISAuditWizard(models.TransientModel):
    _name = "hotel.mis.audit.wizard"
    _description = "Hotel MIS Audit Wizard"

    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    check_dashboard_vs_snapshot = fields.Boolean(default=True)
    check_snapshot_vs_eod = fields.Boolean(default=True)

    def _prepare_snapshot(self, day):
        snapshot_model = self.env["hotel.mis.snapshot"]
        snapshot_model.generate_range(day, day, self.company_id.id)
        return snapshot_model.search(
            [("snapshot_date", "=", day), ("company_id", "=", self.company_id.id)], limit=1
        )

    def _dashboard_metrics(self, day):
        engine = self.env["hotel.kpi.engine"]
        _, summary = engine.compute_range_kpis(day, day, self.company_id.id)
        return summary

    def _eod_metrics(self, day):
        wizard = self.env["hotel.mis.report.wizard"].create(
            {"date_from": day, "date_to": day, "company_id": self.company_id.id}
        )
        summary, _lines = wizard.get_period_kpis()
        return summary

    def _create_result(self, day, metric, dashboard_value, snapshot_value, eod_value):
        difference = (snapshot_value or 0) - (dashboard_value or 0)
        self.env["hotel.mis.audit.result"].create(
            {
                "date": day,
                "metric": metric,
                "dashboard_value": dashboard_value,
                "snapshot_value": snapshot_value,
                "eod_value": eod_value,
                "difference": difference,
            }
        )

    def action_run_audit(self):
        self.ensure_one()
        self.env["hotel.mis.audit.result"].search([]).unlink()
        date_from = self.date_from
        date_to = self.date_to
        day_count = (date_to - date_from).days + 1
        for offset in range(day_count):
            day = date_from + timedelta(days=offset)
            dashboard_metrics = self._dashboard_metrics(day)
            snapshot = self._prepare_snapshot(day)
            eod_metrics = self._eod_metrics(day)
            metric_map = {
                "Occupancy %": (
                    dashboard_metrics.get("occupancy_pct", 0.0),
                    snapshot.occupancy_pct if snapshot else 0.0,
                    eod_metrics.get("occupancy_pct", 0.0),
                ),
                "Rooms Occupied": (
                    dashboard_metrics.get("rooms_occupied", 0.0),
                    snapshot.occupied_rooms if snapshot else 0.0,
                    eod_metrics.get("rooms_occupied", 0.0),
                ),
                "Nights Sold": (
                    dashboard_metrics.get("nights_sold", 0.0),
                    snapshot.nights_sold if snapshot else 0.0,
                    eod_metrics.get("nights_sold", 0.0),
                ),
                "Revenue": (
                    dashboard_metrics.get("total_revenue", 0.0),
                    snapshot.revenue_amount if snapshot else 0.0,
                    eod_metrics.get("total_revenue", 0.0),
                ),
            }
            for metric, values in metric_map.items():
                dashboard_value, snapshot_value, eod_value = values
                if (
                    (self.check_dashboard_vs_snapshot and dashboard_value != snapshot_value)
                    or (self.check_snapshot_vs_eod and snapshot_value != eod_value)
                ):
                    self._create_result(day, metric, dashboard_value, snapshot_value, eod_value)
        return {
            "type": "ir.actions.act_window",
            "name": _("MIS Audit Results"),
            "res_model": "hotel.mis.audit.result",
            "view_mode": "list",
            "target": "current",
        }


class HotelMISAuditResult(models.TransientModel):
    _name = "hotel.mis.audit.result"
    _description = "Hotel MIS Audit Result"

    date = fields.Date()
    metric = fields.Char()
    dashboard_value = fields.Float()
    snapshot_value = fields.Float()
    eod_value = fields.Float()
    difference = fields.Float()
