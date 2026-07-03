# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Vishnu K P (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError



class CleaningRequest(models.Model):
    """Class for creating and assigning Cleaning Request"""
    _name = "cleaning.request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "sequence"
    _description = "Cleaning Request"

    sequence = fields.Char(string="Sequence", readonly=True, default='New',
                           copy=False, tracking=True,
                           help="Sequence for identifying the request")
    state = fields.Selection([('draft', 'Draft'),
                              ('assign', 'Assigned'),
                              ('ongoing', 'Cleaning'),
                              ('support', 'Waiting For Support'),
                              ('done', 'Completed')],
                             string="State",
                             default='draft', help="State of cleaning request")
    cleaning_type = fields.Selection(selection=[('room', 'Room'),
                                                ('hotel', 'Hotel'),
                                                ('vehicle', 'Vehicle')],
                                     required=True, tracking=True,
                                     string="Cleaning Type",
                                     help="Choose what is to be cleaned")
    room_id = fields.Many2one('hotel.room', string="Room",
                              help="Choose the room")
    hotel = fields.Char(string="Hotel", help="Cleaning request space in hotel")
    vehicle_id = fields.Many2one('fleet.vehicle.model',
                                 string="Vehicle",
                                 help="Cleaning request from vehicle")
    support_team_ids = fields.Many2many('hr.employee',
                                        string="Support Team",
                                        help="Support team employees")
    support_reason = fields.Char(string='Support', help="Support Reason")
    description = fields.Char(string="Description",
                              help="Description about the cleaning")
    team_id = fields.Many2one('cleaning.team', string="Team",
                              required=True,
                              tracking=True,
                              help="Choose the team")
    head_id = fields.Many2one('hr.employee', string="Head",
                              related='team_id.team_head_id',
                              help="Head of cleaning team")
    assigned_id = fields.Many2one(
        'hr.employee',
        string="Assigned To",
        help="The employee to whom the request is assigned",
    )
    cleaning_start = fields.Datetime(
        string="Cleaning Start",
        tracking=True,
        help="Date and time when the cleaning was started.",
    )
    cleaning_start_employee_id = fields.Many2one(
        'hr.employee',
        string="Cleaning Started By",
        help="Employee who started the cleaning.",
    )
    cleaning_end = fields.Datetime(
        string="Cleaning End",
        tracking=True,
        help="Date and time when the cleaning was completed.",
    )
    cleaning_end_employee_id = fields.Many2one(
        'hr.employee',
        string="Cleaning Completed By",
        help="Employee who completed the cleaning.",
    )
    inspection_status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string="Inspection Status",
        default='pending',
        tracking=True,
        help="Current inspection status for the cleaning.",
    )
    inspected_by_id = fields.Many2one(
        'hr.employee',
        string="Inspected By",
        help="Employee who inspected the cleaning.",
    )
    team_member_ids = fields.Many2many(
        'hr.employee',
        compute='_compute_team_member_ids',
        store=False,
        help='For filtering Employees'
    )

    @api.depends('team_id')
    def _compute_team_member_ids(self):
        for record in self:
            if record.team_id:
                record.team_member_ids = record.team_id.member_ids
            else:
                record.team_member_ids = False

    @api.model_create_multi
    def create(self, vals_list):
        """Sequence Generation"""
        for vals in vals_list:
            if vals.get('sequence', 'New') == 'New':
                vals['sequence'] = self.env['ir.sequence'].next_by_code('cleaning.request')

        records = super().create(vals_list)

        # Update cleaning status for room-type cleaning
        for record in records:
            if record.cleaning_type == 'room' and record.room_id:
                record.room_id.cleaning_status = 'dirty'

        return records

    def action_assign_cleaning(self):
        """Button action for updating the state to assign"""
        self.update({'state': 'assign'})

    def action_start_cleaning(self):
        """Button action for updating the state to ongoing"""
        employee = self.env.user.employee_id
        for request in self:
            vals = {'state': 'ongoing'}
            if not request.cleaning_start:
                vals.update({
                    'cleaning_start': fields.Datetime.now(),
                    'cleaning_start_employee_id': employee.id if employee else False,
                })
            request.write(vals)

    def action_done_cleaning(self):
        """Button action for  updating the state to done"""
        employee = self.env.user.employee_id
        for request in self:
            vals = {
                'state': 'done',
                'inspection_status': request.inspection_status or 'pending',
            }
            if not request.cleaning_end:
                vals.update({
                    'cleaning_end': fields.Datetime.now(),
                    'cleaning_end_employee_id': employee.id if employee else False,
                })
            request.write(vals)
        for request in self.filtered(
            lambda r: r.cleaning_type == 'room' and r.room_id
        ):
            request.room_id.cleaning_status = 'clean'

    def action_assign_support(self):
        """Button action for updating the state to support"""
        if self.support_reason:
            self.write({'state': 'support'})
        else:
            raise ValidationError(_('Please enter the reason'))

    def action_assign_assign_support(self):
        """Button action for updating the state to ongoing"""
        if self.support_team_ids:
            self.write({'state': 'ongoing'})
        else:
            raise ValidationError(_('Please choose a support'))

    def action_maintain_request(self):
        """Button action for creating the maintenance request"""
        self.env['maintenance.request'].sudo().create({
            'date': fields.Date.today(),
            'state': 'draft',
            'type': self.cleaning_type,
            'vehicle_maintenance_id': self.vehicle_id.id
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': "Maintenance Request Sent Successfully",
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_print_cleaning_summary(self):
        self.ensure_one()
        report = self.env.ref('atk_hotel.action_report_cleaning_request_summary_pdf', raise_if_not_found=False)
        if not report:
            report = self.env['ir.actions.report'].sudo().search([
                ('report_name', '=', 'atk_hotel.report_cleaning_request_summary_document')
            ], limit=1)
        if not report:
            raise UserError(_(
                "The cleaning request report is not available. Please update the Hotel module or contact your administrator."
            ))
        return report.report_action(self)
