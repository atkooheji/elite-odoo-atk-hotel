from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import datetime

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    hotel_book_history_ids = fields.One2many('hotel.book.history', 'sale_order_id', string="Hotel Book History")
    hotel_book_history_count = fields.Integer(string="Hotel Book History Count", compute="_compute_hotel_book_history_count", store=False)
    partner_loyalty_points = fields.Float(
        string="Loyalty Points Remaining",
        compute="_compute_partner_loyalty_points",
        store=True
    )
    loyalty_points_accrued = fields.Boolean(
        string="Loyalty Points Awarded",
        default=False,
        copy=False,
        help="Indicates if loyalty points have been accrued for this order from the hotel module.",
    )
    loyalty_points_amount = fields.Float(
        string="Loyalty Points Awarded Amount",
        default=0.0,
        copy=False,
        help="Stores the amount of points granted when the hotel action was triggered.",
    )


    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        # Set default check-in / check-out from sale order rental period
        invoice_vals.update({
            'check_in': self.rental_start_date,
            'check_out': self.rental_return_date,
            'duration':self.duration_days
        })
        return invoice_vals

    @api.depends('partner_id')
    def _compute_partner_loyalty_points(self):
        for order in self:
            card = self.env['loyalty.card'].search(
                [('partner_id', '=', order.partner_id.id)],
                limit=1,
                order='id desc'
            )
            order.partner_loyalty_points = card.points if card else 0.0

    @api.depends('hotel_book_history_ids')
    def _compute_hotel_book_history_count(self):
        for record in self:
            record.hotel_book_history_count = len(record.hotel_book_history_ids)
            
    def action_view_hotel_book_history(self):
        self.ensure_one()
        action = self.env.ref('atk_hotel.action_hotel_book_history_all').read()[0]
        action['domain'] = [('sale_order_id', '=', self.id)]
        return action

    def action_view_customer_loyalty(self):
        """Open the customer's loyalty card form to review points."""
        self.ensure_one()
        if not self.partner_id:
            return False

        # Find the loyalty card
        card = self.env['loyalty.card'].search([('partner_id', '=', self.partner_id.id)], limit=1)
        if not card:
            return False  # Or raise ValidationError("No loyalty card for this customer")

        return {
            'name': _('Loyalty'),
            'type': 'ir.actions.act_window',
            'res_model': 'loyalty.card',
            'view_mode': 'form',
            'res_id': card.id,  # âœ… correct ID
            'target': 'current',
            'context': {
                'default_partner_loyalty_points': card.points,  # you can pass points here if needed
            }
        }

    def action_accrue_loyalty_points(self):
        """Accrue loyalty points from the hotel workflow when requested explicitly."""
        self.ensure_one()

        if self.loyalty_points_accrued:
            raise ValidationError(_('Loyalty points have already been accrued for this order.'))

        if not self.partner_id:
            raise ValidationError(_('Please select a customer before accruing loyalty points.'))

        card = self.env['loyalty.card'].search([('partner_id', '=', self.partner_id.id)], limit=1)
        if not card:
            raise ValidationError(_('No loyalty card is available for this customer.'))

        # Use the order total as the points to grant so it is only applied when this action is triggered.
        points_to_add = self.amount_total
        if points_to_add <= 0:
            raise ValidationError(_('No loyalty points can be accrued because the order total is zero.'))

        card.with_context(allow_loyalty_accrual=True).add_points(
            points=points_to_add,
            description=_('Hotel loyalty accrual from order %s') % self.name,
        )

        self.write({
            'loyalty_points_accrued': True,
            'loyalty_points_amount': points_to_add,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Loyalty Points Accrued'),
                'message': _('Added %(points).2f points to %(customer)s\'s loyalty card.') % {
                    'points': points_to_add,
                    'customer': self.partner_id.name,
                },
                'sticky': False,
                'type': 'success',
            }
        }

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total')
    def _compute_amounts(self):
        res = super(SaleOrder, self)._compute_amounts()
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })
            
        return res

    # @api.depends_context('lang')
    # @api.depends('order_line.tax_ids', 'order_line.price_unit', 'amount_total', 'amount_untaxed', 'currency_id')
    # def _compute_tax_totals(self):
    #     res = super(SaleOrder, self)._compute_tax_totals()
    #     for order in self:
    #         order_lines = order.order_line.filtered(lambda x: not x.display_type)
            
    #         tax_model = self.env['account.tax']

    #         tax_base_line_dicts = []

    #         for order_line in order_lines:
    #             tax_base_line_dict = order_line._convert_to_tax_base_line_dict()
    #             tax_base_line_dict['quantity'] *= order_line.duration
    #             tax_base_line_dicts.append(tax_base_line_dict)

    #         currency_to_use = order.currency_id or order.company_id.currency_id
    #         tax_totals = tax_model._prepare_tax_totals(tax_base_line_dicts, currency_to_use)
    #         order.tax_totals = tax_totals

    #     return res
