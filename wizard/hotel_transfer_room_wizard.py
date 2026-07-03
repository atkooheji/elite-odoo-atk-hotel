from odoo import models, fields, _
from odoo.exceptions import UserError


class HotelTransferRoomWizard(models.TransientModel):
    _name = 'hotel.transfer.room.wizard'
    _description = 'Transfer Booking Room'

    booking_id = fields.Many2one(
        'hotel.book.history',
        string='Booking',
        required=True,
        default=lambda self: self.env.context.get('active_id'),
    )
    current_room_id = fields.Many2one(
        'hotel.room',
        string='Current Room',
        related='booking_id.room_id',
        readonly=True,
    )
    new_room_id = fields.Many2one(
        'hotel.room',
        string='New Room',
        required=True,
        domain=[('state', 'in', ['available', 'reserved'])],
    )

    def action_transfer_room(self):
        self.ensure_one()
        booking = self.booking_id
        if not booking:
            raise UserError(_('No booking found to transfer.'))
        if booking.state not in ['confirmed', 'checked_in']:
            raise UserError(_('Only confirmed or checked-in bookings can be transferred.'))
        if not booking.room_id:
            raise UserError(_('The booking does not have an assigned room.'))
        if self.new_room_id == booking.room_id:
            raise UserError(_('Please select a different room to transfer to.'))

        if not self.new_room_id.is_available_for_dates(booking.check_in, booking.check_out):
            raise UserError(
                _('Room %(room)s is not available between %(check_in)s and %(check_out)s.',
                  room=self.new_room_id.name,
                  check_in=booking.check_in,
                  check_out=booking.check_out)
            )

        old_room = booking.room_id
        booking.write({'room_id': self.new_room_id.id})

        self._update_room_states_after_transfer(old_room, self.new_room_id, booking)

        booking.message_post(
            body=_('Booking transferred from room %(old)s to room %(new)s.',
                   old=old_room.name,
                   new=self.new_room_id.name)
        )

        return {'type': 'ir.actions.act_window_close'}

    def _update_room_states_after_transfer(self, old_room, new_room, booking):
        if booking.state == 'checked_in':
            new_room.state = 'occupied'
        else:
            new_room.state = 'reserved'

        if not old_room:
            return

        active_checked_in = self.env['hotel.book.history'].search([
            ('room_id', '=', old_room.id),
            ('id', '!=', booking.id),
            ('state', '=', 'checked_in'),
        ], limit=1)
        if active_checked_in:
            old_room.state = 'occupied'
            old_room.is_future_reserved = False
            return

        future_confirmed = self.env['hotel.book.history'].search([
            ('room_id', '=', old_room.id),
            ('id', '!=', booking.id),
            ('state', '=', 'confirmed'),
            ('check_in', '>=', fields.Datetime.now()),
        ], order='check_in asc', limit=1)

        if future_confirmed:
            old_room.state = 'reserved'
            old_room.is_future_reserved = True
        else:
            old_room.state = 'available'
            old_room.is_future_reserved = False
