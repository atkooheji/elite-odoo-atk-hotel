from odoo import api, fields, models


class HotelBookingSource(models.Model):
    _name = 'hotel.booking.source'
    _description = 'Hotel Booking Source'
    _order = 'sequence, name'

    name = fields.Char(string='Source Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    note = fields.Text(string='Description')

    class Constraint(models.Constraint):
        _sql = "UNIQUE(name)"
        _message = "The booking source must be unique."

    @api.model
    def name_create(self, name):
        record = self.create({'name': name})
        return record.id, record.display_name
