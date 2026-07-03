from datetime import timedelta

from psycopg2 import sql

from odoo import api, fields, models


class HotelMISSnapshot(models.Model):
    _name = "hotel.mis.snapshot"
    _description = "Hotel MIS Daily Snapshot"
    _order = "snapshot_date desc"

    snapshot_date = fields.Date(string="Date", required=True, index=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    property_id = fields.Many2one("property.property", string="Property")

    total_rooms = fields.Integer(string="Total Rooms")
    occupied_rooms = fields.Integer(string="Occupied Rooms")
    available_rooms = fields.Integer(string="Available Rooms")
    maintenance_rooms = fields.Integer(string="Rooms in Maintenance")
    occupancy_pct = fields.Float(string="Occupancy %", digits=(16, 2))
    occupancy_rate = fields.Float(string="Occupancy Rate", digits=(16, 2))
    arrivals = fields.Integer(string="Arrivals")
    departures = fields.Integer(string="Departures")
    cancellations = fields.Integer(string="Cancellations")
    revenue_amount = fields.Monetary(string="Revenue")
    avg_daily_rate = fields.Monetary(string="Average Daily Rate")
    revpar = fields.Monetary(string="RevPAR")
    avg_stay_length = fields.Float(string="Average Stay (Days)")
    bookings_count = fields.Integer(string="Bookings")
    nights_sold = fields.Integer(string="Nights Sold")
    currency_id = fields.Many2one("res.currency", compute="_compute_currency")

    class Constraint(models.Constraint):
        _sql = "UNIQUE(snapshot_date, company_id, property_id)"
        _message = "Snapshot already exists for this day."

    def _auto_init(self):
        self.env.cr.execute(
            "SELECT 1 FROM pg_class WHERE relname = %s AND relkind = 'v'",
            (self._table,),
        )
        if self.env.cr.fetchone():
            drop_query = sql.SQL("DROP VIEW IF EXISTS {} CASCADE").format(sql.Identifier(self._table))
            self.env.cr.execute(drop_query)
        return super()._auto_init()

    @api.depends("company_id")
    def _compute_currency(self):
        for snapshot in self:
            snapshot.currency_id = snapshot.company_id.currency_id or self.env.company.currency_id

    # ------------------------------------------------------------------
    # Generation helpers
    # ------------------------------------------------------------------
    @api.model
    def generate_range(self, date_from, date_to, company_id, property_id=False):
        engine = self.env["hotel.kpi.engine"]
        days = (date_to - date_from).days + 1
        for offset in range(days):
            day = date_from + timedelta(days=offset)
            kpis = engine.compute_day_kpis(day, company_id, property_id)
            existing = self.search(
                [
                    ("snapshot_date", "=", day),
                    ("company_id", "=", company_id),
                    ("property_id", "=", property_id if property_id else False),
                ],
                limit=1,
            )
            values = {
                "snapshot_date": day,
                "company_id": company_id,
                "property_id": property_id or False,
                "total_rooms": kpis.get("total_rooms", 0),
                "occupied_rooms": kpis.get("occupied_rooms", 0),
                "available_rooms": kpis.get("available_rooms", 0),
                "maintenance_rooms": kpis.get("maintenance_rooms", 0),
                "occupancy_pct": kpis.get("occupancy_pct", 0.0),
                "occupancy_rate": kpis.get("occupancy_pct", 0.0),
                "arrivals": kpis.get("arrivals", 0),
                "departures": kpis.get("departures", 0),
                "cancellations": kpis.get("cancellations", 0),
                "revenue_amount": kpis.get("revenue", 0.0),
                "avg_daily_rate": kpis.get("adr", 0.0),
                "revpar": kpis.get("revpar", 0.0),
                "avg_stay_length": kpis.get("nights_sold", 0),
                "bookings_count": kpis.get("nights_sold", 0),
                "nights_sold": kpis.get("nights_sold", 0),
            }
            if existing:
                existing.write(values)
            else:
                self.create(values)

    @api.model
    def get_range(self, date_from, date_to, company_id, property_id=False):
        self.generate_range(date_from, date_to, company_id, property_id)
        domain = [
            ("snapshot_date", ">=", date_from),
            ("snapshot_date", "<=", date_to),
            ("company_id", "=", company_id),
        ]
        if property_id:
            domain.append(("property_id", "=", property_id))
        else:
            domain.append(("property_id", "=", False))
        return self.search(domain, order=self._order)
