from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HotelRoomInspection(models.Model):
    _name = 'hotel.room.inspection'
    _description = 'Hotel Room Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        copy=False,
        required=True,
        default='New',
        tracking=True,
    )
    room_id = fields.Many2one(
        'hotel.room',
        string='Room',
        required=True,
        tracking=True,
    )
    inspection_date = fields.Date(
        string='Inspection Date',
        default=fields.Date.context_today,
        tracking=True,
    )
    inspector_id = fields.Many2one(
        'hr.employee',
        string='Inspector',
        tracking=True,
    )
    state = fields.Selection(
        [
            ('scheduled', 'Scheduled'),
            ('in_progress', 'In Progress'),
            ('passed', 'Passed'),
            ('failed', 'Failed'),
            ('maintenance_requested', 'Maintenance Requested'),
        ],
        string='Status',
        default='scheduled',
        tracking=True,
    )
    notes = fields.Text(string='Notes')
    follow_up_actions = fields.Text(string='Follow-up Actions')
    maintenance_request_id = fields.Many2one(
        'maintenance.request',
        string='Maintenance Request',
        readonly=True,
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = sequence.next_by_code('hotel.room.inspection') or _('New')
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_mark_passed(self):
        self.write({'state': 'passed'})

    def action_mark_failed(self):
        self.write({'state': 'failed'})

    def action_request_maintenance(self):
        for inspection in self:
            if inspection.maintenance_request_id:
                raise UserError(_('A maintenance request has already been created for this inspection.'))
            maintenance_request = self.env['maintenance.request'].create({
                'name': _('Room Inspection - %s', inspection.room_id.name),
                'description': inspection.notes or _('Issue found during inspection.'),
                'hotel_room_id': inspection.room_id.id,
                'inspection_id': inspection.id,
            })
            inspection.maintenance_request_id = maintenance_request.id
            inspection.state = 'maintenance_requested'
        return True
