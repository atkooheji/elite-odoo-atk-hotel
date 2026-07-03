from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HotelBookingWizard(models.TransientModel):
    _name = 'hotel.booking.wizard'
    _description = 'Hotel Booking Wizard'

    guest_id = fields.Many2one('res.partner', string="Guest", required=True,domain=[('is_hotel_customer', '=', True)])
    room_id = fields.Many2one('hotel.room', string="Room", required=True)
    check_in = fields.Datetime(string="Check-in", required=True)
    check_out = fields.Datetime(string="Check-out", required=True)

    @api.onchange('check_in', 'check_out')
    def _onchange_dates(self):
        if self.check_out and self.check_in and self.check_out <= self.check_in:
            raise UserError(_("Check-out must be after check-in."))

    def action_open_guest_form(self):
        self.ensure_one()
        return {
            'name': _('Create Guest'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'view_id': self.env.ref('atk_hotel.view_hotel_partner_form').id,
            'target': 'new',
            'flags': {'initial_mode': 'edit'},
            'context': {
                'default_is_hotel_customer': True,
                'default_company_type': 'person',
                'default_type': 'contact',
                'from_hotel_booking_wizard_id': self.id,
                'active_model': self._name,
                'active_id': self.id,
            },
        }

    def action_create_booking(self):
        self.ensure_one()

        # Validate room availability
        if self.room_id and not self.room_id.is_available_for_dates(self.check_in, self.check_out):
            raise UserError(_("Room %s is not available for selected dates.") % self.room_id.name)

        # Create booking
        booking = self.env['hotel.book.history'].create({
            'partner_id': self.guest_id.id,
            'room_id': self.room_id.id,
            'check_in': self.check_in,
            'check_out': self.check_out,
            'state': 'draft',  # Will be confirmed manually or auto via button
        })

        # Optional: Auto-confirm
        # booking.action_confirm()

        return {
            'name': _('Booking Created'),
            'view_mode': 'form',
            'res_model': 'hotel.book.history',
            'res_id': booking.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
