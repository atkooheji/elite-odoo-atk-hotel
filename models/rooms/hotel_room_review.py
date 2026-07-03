from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HotelRoomReview(models.Model):
    _name = 'hotel.room.review'
    _description = 'Hotel Room Review'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string="Guest", required=True)
    room_id = fields.Many2one('hotel.room', string="Room", required=True)
    booking_id = fields.Many2one('hotel.book.history', string="Booking", required=True)
    rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent'),
    ], string="Rating", required=True, default='5')
    comment = fields.Text(string="Comment")
    is_published = fields.Boolean(string="Published", default=False)
    
    @api.constrains('rating')
    def _check_rating(self):
        for record in self:
            if not record.rating:
                raise ValidationError(_("Rating is required."))
