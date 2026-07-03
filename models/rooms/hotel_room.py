from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'website.published.mixin']
    _description = 'Hotel Room'

    name = fields.Char(string="Room Number", required=True)
    image_1920 = fields.Image(string="Room Image", max_width=1920, max_height=1920)
    website_description = fields.Html(string="Website Description", translate=True)
    
    review_ids = fields.One2many('hotel.room.review', 'room_id', string="Reviews")
    rating_avg = fields.Float(string="Average Rating", compute="_compute_rating_stats", store=True)
    rating_count = fields.Integer(string="Rating Count", compute="_compute_rating_stats", store=True)
    review_count = fields.Integer(string="Review Count", compute="_compute_rating_stats", store=True)

    @api.depends('review_ids.rating', 'review_ids.is_published')
    def _compute_rating_stats(self):
        for room in self:
            published_reviews = room.review_ids.filtered(lambda r: r.is_published)
            if published_reviews:
                room.rating_avg = sum(float(r.rating) for r in published_reviews) / len(published_reviews)
                room.review_count = len(published_reviews)
                room.rating_count = room.review_count
            else:
                room.rating_avg = 0.0
                room.review_count = 0
                room.rating_count = 0

    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        compute='_compute_company_id', 
        store=True, 
        readonly=False, 
        default=lambda self: self.env.company
    )

    @api.depends()
    def _compute_company_id(self):
        for record in self:
            if not record.company_id:
                record.company_id = self.env.company
    room_type = fields.Many2one(
        'product.product',
        string="Room Type Product",
        required=False,
        domain=[('type', '=', 'service')],
        ondelete='set null'
    )
    room_type_id = fields.Many2one(
        'hotel.room.type',
        string="Physical Room Type",
        required=True,
        ondelete='cascade'
    )
    floor = fields.Char(string="Floor")

    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Maintenance'),
        ('unavailable', 'Out of Order'),
    ], string="Status", default='available', tracking=True)
    out_of_order_reason = fields.Text(string="Out of Order Reason", tracking=True)
    cleaning_status = fields.Selection(
        [
            ('clean', 'Clean'),
            ('dirty', 'Dirty'),
            ('inspected', 'Inspected'),
            ('skip', 'Skip'),
            ('sleep', 'Sleep'),
            ('discrepancy', 'Person Discrepancy'),
        ],
        string="Cleaning Status",
        default='clean',
        tracking=True,
    )

    booking_ids = fields.One2many('hotel.book.history', 'room_id', string="Bookings")
    booking_count = fields.Integer(string="Booking Count", compute="_compute_booking_count", store=True)
    current_guest_name = fields.Char(string="Current Guest", compute="_compute_current_booking_info")
    maintenance_request_ids = fields.One2many(
        'maintenance.request',
        'hotel_room_id',
        string="Maintenance Requests",
    )
    maintenance_request_count = fields.Integer(
        string="Maintenance Request Count",
        compute="_compute_maintenance_request_count",
    )
    inspection_ids = fields.One2many(
        'hotel.room.inspection',
        'room_id',
        string="Inspections",
    )
    inspection_count = fields.Integer(
        string="Inspection Count",
        compute="_compute_inspection_count",
    )
    is_future_reserved = fields.Boolean(
        string="Future Reserved",
        help="Indicates that there is a future confirmed booking for this room while it's currently occupied.",
        default=False
    )

    # === COMPUTE METHODS ===
    @api.depends('booking_ids')
    def _compute_booking_count(self):
        for room in self:
            room.booking_count = len(room.booking_ids)

    @api.depends('booking_ids.state')
    def _compute_current_booking_info(self):
        for room in self:
            current_booking = self.env['hotel.book.history'].search([
                ('room_id', '=', room.id),
                ('state', '=', 'checked_in'),
            ], limit=1, order='check_in desc')
            room.current_guest_name = current_booking.partner_id.name if current_booking.partner_id else ""

    def _compute_maintenance_request_count(self):
        grouped_data = self.env['maintenance.request'].read_group(
            [('hotel_room_id', 'in', self.ids)],
            ['hotel_room_id'],
            ['hotel_room_id']
        )
        count_map = {data['hotel_room_id'][0]: data['hotel_room_id_count'] for data in grouped_data}
        for room in self:
            room.maintenance_request_count = count_map.get(room.id, 0)

    def _compute_inspection_count(self):
        grouped_data = self.env['hotel.room.inspection'].read_group(
            [('room_id', 'in', self.ids)],
            ['room_id'],
            ['room_id']
        )
        count_map = {data['room_id'][0]: data['room_id_count'] for data in grouped_data}
        for room in self:
            room.inspection_count = count_map.get(room.id, 0)

    # === STATE TRANSITIONS ===
    def action_maintenance(self):
        for room in self:
            if room.state == 'occupied':
                raise UserError(_("Cannot set room to maintenance while occupied."))
            room.state = 'maintenance'

    def action_available(self):
        self.write({'state': 'available'})

    def action_set_to_out_of_order(self):
        self.ensure_one()
        return {
            'name': _('Set Out of Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.room.out.of.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_room_id': self.id},
        }

    # === BUTTONS & ACTIONS ===
    def action_view_reservations(self):
        self.ensure_one()
        return {
            'name': _('Bookings'),
            'view_mode': 'list,form',
            'res_model': 'hotel.book.history',
            'type': 'ir.actions.act_window',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id},
        }

    def open_booking_form(self):
        self.ensure_one()
        return {
            'name': _('Create Booking'),
            'view_mode': 'form',
            'res_model': 'hotel.book.history',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_room_id': self.id},
        }

    def open_checkin_form(self):
        self.ensure_one()
        booking = self._search_currently_reserved_booking()
        if not booking:
            raise UserError(_("No confirmed booking found for check-in."))
        return self._open_booking_form(booking, _('Check In'))

    def open_checkout_form(self):
        self.ensure_one()
        booking = self._search_currently_occupied_booking()
        if not booking:
            raise UserError(_("No checked-in booking found for check-out."))
        return self._open_booking_form(booking, _('Check Out'))

    def _search_currently_reserved_booking(self):
        return self.env['hotel.book.history'].search([
            ('room_id', '=', self.id),
            ('state', '=', 'confirmed'),
        ], limit=1, order='create_date desc')

    def _search_currently_occupied_booking(self):
        return self.env['hotel.book.history'].search([
            ('room_id', '=', self.id),
            ('state', '=', 'checked_in'),
        ], limit=1, order='check_in desc')

    def _open_booking_form(self, booking, title):
        return {
            'name': title,
            'view_mode': 'form',
            'res_model': 'hotel.book.history',
            'res_id': booking.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_print_room_summary(self):
        self.ensure_one()
        report = self.env.ref('atk_hotel.action_report_hotel_room_summary_pdf', raise_if_not_found=False)
        if not report:
            report = self.env['ir.actions.report'].sudo().search([
                ('report_name', '=', 'atk_hotel.report_hotel_room_summary_document')
            ], limit=1)
        if not report:
            raise UserError(_(
                "The room summary report is not available. Please update the Hotel module or contact your administrator."
            ))
        return report.report_action(self)

    # === AVAILABILITY CHECK ===
    def is_available_for_dates(self, check_in, check_out):
        self.ensure_one()
        overlapping = self.env['hotel.book.history'].search([
            ('room_id', '=', self.id),
            ('state', 'not in', ['checked_out', 'cancelled']),
            ('check_in', '<', check_out),
            ('check_out', '>', check_in),
        ])
        return len(overlapping) == 0

    # === MAINTENANCE & INSPECTION ACTIONS ===
    def action_open_maintenance_requests(self):
        self.ensure_one()
        return {
            'name': _('Maintenance Requests'),
            'view_mode': 'list,form,kanban,calendar,pivot,graph',
            'res_model': 'maintenance.request',
            'type': 'ir.actions.act_window',
            'domain': [('hotel_room_id', '=', self.id)],
            'context': {
                'default_hotel_room_id': self.id,
            },
        }

    def action_create_maintenance_request(self):
        self.ensure_one()
        return {
            'name': _('New Maintenance Request'),
            'view_mode': 'form',
            'res_model': 'maintenance.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {
                'default_hotel_room_id': self.id,
                'default_name': _('Maintenance for %s', self.name),
                'default_description': _('Maintenance request created from room %s', self.name),
            },
        }

    def action_open_inspections(self):
        self.ensure_one()
        return {
            'name': _('Room Inspections'),
            'view_mode': 'list,form',
            'res_model': 'hotel.room.inspection',
            'type': 'ir.actions.act_window',
            'domain': [('room_id', '=', self.id)],
            'context': {
                'default_room_id': self.id,
            },
        }

    def action_schedule_inspection(self):
        self.ensure_one()
        return {
            'name': _('Schedule Inspection'),
            'view_mode': 'form',
            'res_model': 'hotel.room.inspection',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {
                'default_room_id': self.id,
            },
        }
