from odoo import models, fields, api


class HotelBookHistoryProductLine(models.Model):
    _name = 'hotel.book.history.product.line'
    _description = 'Hotel Booking Additional Product'

    booking_id = fields.Many2one(
        'hotel.book.history',
        string='Booking',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('sale_ok', '=', True)],
    )
    name = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Monetary(string='Unit Price', currency_field='currency_id')
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', currency_field='currency_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency', store=True)

    @api.depends('booking_id.currency_id')
    def _compute_currency(self):
        company_currency = self.env.company.currency_id
        for line in self:
            line.currency_id = line.booking_id.currency_id or company_currency

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.get_product_multiline_description_sale()
                if not line.price_unit:
                    line.price_unit = line.product_id.lst_price

    @api.model_create_multi
    def create(self, vals_list):
        product_model = self.env['product.product']
        for vals in vals_list:
            product = vals.get('product_id') and product_model.browse(vals['product_id']) or False
            if product:
                vals.setdefault('name', product.get_product_multiline_description_sale())
                if 'price_unit' not in vals:
                    vals['price_unit'] = product.lst_price

        records = super().create(vals_list)
        records._sync_booking_sale_order()
        return records

    def write(self, vals):
        if 'product_id' in vals and 'name' not in vals:
            product = vals.get('product_id') and self.env['product.product'].browse(vals['product_id']) or False
            if product:
                vals = dict(vals, name=product.get_product_multiline_description_sale())
                if 'price_unit' not in vals:
                    vals['price_unit'] = product.lst_price

        result = super().write(vals)
        self._sync_booking_sale_order()
        return result

    def unlink(self):
        bookings = self.mapped('booking_id')
        result = super().unlink()
        bookings._sync_sale_order()
        return result

    def _sync_booking_sale_order(self):
        bookings = self.mapped('booking_id')
        bookings._sync_sale_order()
