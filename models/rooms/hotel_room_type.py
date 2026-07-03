from odoo import models, fields, api, _

class HotelRoomType(models.Model):
    _name = 'hotel.room.type'
    _description = 'Hotel Room Type'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'website.published.mixin']
    _order = 'sequence, name'

    rating_avg = fields.Float(string="Average Rating", compute="_compute_rating_stats", store=True)
    rating_count = fields.Integer(string="Rating Count", compute="_compute_rating_stats", store=True)
    review_count = fields.Integer(string="Review Count", compute="_compute_rating_stats", store=True)

    @api.depends('room_ids.rating_avg', 'room_ids.review_count')
    def _compute_rating_stats(self):
        for room_type in self:
            rooms = room_type.room_ids
            if rooms:
                room_type.rating_avg = sum(r.rating_avg for r in rooms) / len(rooms)
                room_type.review_count = sum(r.review_count for r in rooms)
                room_type.rating_count = room_type.review_count
            else:
                room_type.rating_avg = 0.0
                room_type.review_count = 0
                room_type.rating_count = 0

    name = fields.Char(string="Room Type Name", required=True, translate=True)
    code = fields.Char(string="Room Code", help="Short code for the room type (e.g. DLX, SUT)")
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
    website_description = fields.Html(string="Website Description", translate=True)
    sequence = fields.Integer(string="Sequence", default=10)

    # Capacity & Physical Attributes
    max_adults = fields.Integer(string="Max Adults", default=2, required=True)
    max_children = fields.Integer(string="Max Children", default=2, required=True)
    max_occupancy = fields.Integer(string="Max Guests", compute="_compute_max_occupancy", store=True)
    size_sqm = fields.Float(string="Size (sqm)", help="Approximate suite size shown on the website.")

    @api.depends('max_adults', 'max_children')
    def _compute_max_occupancy(self):
        for rt in self:
            rt.max_occupancy = rt.max_adults + rt.max_children
    bed_type = fields.Selection([
        ('single', 'Single'),
        ('double', 'Double'),
        ('queen', 'Queen'),
        ('king', 'King'),
        ('twin', 'Twin'),
        ('bunk', 'Bunk Bed'),
        ('sofa', 'Sofa Bed'),
    ], string="Bed Type")
    floor = fields.Char(string="Floor")
    view = fields.Selection([
        ('city', 'City View'),
        ('sea', 'Sea View'),
        ('garden', 'Garden View'),
        ('pool', 'Pool View'),
        ('mountain', 'Mountain View'),
    ], string="View")

    # Pricing
    default_price = fields.Float(string="Default Nightly Rate", required=True, digits='Product Price')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Integration with Sales
    product_id = fields.Many2one('product.product', string="Service Product",
        domain=[('type', '=', 'service')],
        help="The service product used in sale orders for this room type.")

    # Amenities
    amenity_ids = fields.Many2many('hotel.amenity', string="Included Amenities")

    # Images
    image_1920 = fields.Image(string="Image", max_width=1920, max_height=1920)
    image_1024 = fields.Image("Image 1024", related="image_1920", max_width=1024, max_height=1024, store=True)
    image_512 = fields.Image("Image 512", related="image_1920", max_width=512, max_height=512, store=True)
    image_256 = fields.Image("Image 256", related="image_1920", max_width=256, max_height=256, store=True)
    image_128 = fields.Image("Image 128", related="image_1920", max_width=128, max_height=128, store=True)

    # Statistics
    room_ids = fields.One2many('hotel.room', 'room_type_id', string="Rooms")
    room_count = fields.Integer(string="Number of Rooms", compute="_compute_room_count", store=True)

    @api.depends('room_ids')
    def _compute_room_count(self):
        for record in self:
            record.room_count = len(record.room_ids)

    def action_view_rooms(self):
        self.ensure_one()
        return {
            'name': _('Rooms of Type: %s') % self.name,
            'view_mode': 'list,form',
            'res_model': 'hotel.room',
            'type': 'ir.actions.act_window',
            'domain': [('room_type_id', '=', self.id)],
            'context': {'default_room_type_id': self.id},
        }
