from odoo import models, fields, api

class HotelRoomOutOfOrderWizard(models.TransientModel):
    _name = 'hotel.room.out.of.order.wizard'
    _description = 'Set Room Out of Order'

    reason = fields.Text(string="Reason", required=True)
    room_id = fields.Many2one('hotel.room', string="Room", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.room_id.write({
            'state': 'unavailable',
            'out_of_order_reason': self.reason
        })
        return {'type': 'ir.actions.act_window_close'}
