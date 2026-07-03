from odoo import fields, models, _
from odoo.exceptions import UserError


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    hotel_room_id = fields.Many2one(
        'hotel.room',
        string='Hotel Room',
        tracking=True,
    )
    inspection_id = fields.Many2one(
        'hotel.room.inspection',
        string='Room Inspection',
        tracking=True,
    )

    def action_open_related_room(self):
        self.ensure_one()
        if not self.hotel_room_id:
            raise UserError(_('No room is linked to this maintenance request.'))
        return {
            'name': _('Room'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.room',
            'res_id': self.hotel_room_id.id,
            'view_mode': 'form',
        }
