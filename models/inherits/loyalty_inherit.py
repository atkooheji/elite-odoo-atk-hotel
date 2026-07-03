from odoo import models, fields, api, _
from datetime import datetime

class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'

    # We use the existing 'points' field from the loyalty module
    # hotel_total_points is our custom tracking field
    hotel_total_points = fields.Float(
        string="Total Points Earned",
        compute="_compute_hotel_points",
        store=True
    )
    hotel_current_balance = fields.Float(
        string="Current Balance",
        compute="_compute_hotel_points",
        store=True
    )
    hotel_history_ids = fields.One2many('hotel.loyalty.history', 'card_id', string="Points History")

    @api.model_create_multi
    def create(self, vals_list):
        """Allow loyalty card creation, but track if it came from our module logic."""
        return super().create(vals_list)

    @api.depends('hotel_history_ids.points')
    def _compute_hotel_points(self):
        for card in self:
            # Total earned points = only positive values from history
            card.hotel_total_points = sum(h.points for h in card.hotel_history_ids if h.points > 0)
            # Current balance should ideally match card.points, but we track it from history for consistency
            card.hotel_current_balance = card.hotel_history_ids[:1].new_balance if card.hotel_history_ids else 0.0

    def add_points(self, points, description="Points added"):
        """Append a loyalty history line and update the main points field."""
        # Check context only if we want to skip points for some reason, 
        # but defaulting to allowing it if called explicitly.
        for card in self:
            old_balance = card.points # Use base field
            new_balance = old_balance + points
            self.env['hotel.loyalty.history'].create({
                'card_id': card.id,
                'partner_id': card.partner_id.id,
                'points': points,
                'balance': old_balance,
                'new_balance': new_balance,
                'description': description,
                'date': datetime.now(),
            })
            card.points = new_balance


class HotelLoyaltyHistory(models.Model):
    _name = 'hotel.loyalty.history'
    _description = 'Loyalty Points History'
    _order = "date desc"

    card_id = fields.Many2one('loyalty.card', string="Loyalty Card", ondelete="cascade")
    partner_id = fields.Many2one('res.partner', string="Customer", domain=[('is_hotel_customer', '=', True)])
    date = fields.Datetime(string="Date", default=fields.Datetime.now)
    description = fields.Char(string="Activity")
    points = fields.Float(string="Points Change (+/-)")
    balance = fields.Float(string="Previous Balance")
    new_balance = fields.Float(string="New Balance")
