from odoo import models, fields, api

class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'website.published.mixin']

    # field model 
    is_room = fields.Boolean(string="Is room", help="Check if this product is a hotel's room type")
    is_hotel_service = fields.Boolean(string="Is Hotel Service", help="Check if this product is a service (e.g., breakfast, transfer)")
    max_allowed_person = fields.Integer(string="Max allowed person", default=1)

    # field constraint 
    amenity_line_ids = fields.One2many('hotel.amenity.line', 'product_id', string="Amenities")
    room_ids = fields.One2many('hotel.room', 'room_type', string="Rooms")

    rating_avg = fields.Float(string="Average Rating", compute="_compute_rating_stats", store=True)
    rating_count = fields.Integer(string="Rating Count", compute="_compute_rating_stats", store=True)
    review_count = fields.Integer(string="Review Count", compute="_compute_rating_stats", store=True)

    @api.depends('room_ids.rating_avg', 'room_ids.review_count')
    def _compute_rating_stats(self):
        for template in self:
            if template.is_room:
                rooms = template.room_ids
                if rooms:
                    template.rating_avg = sum(r.rating_avg for r in rooms) / len(rooms)
                    template.review_count = sum(r.review_count for r in rooms)
                    template.rating_count = template.review_count
                else:
                    template.rating_avg = 0.0
                    template.review_count = 0
                    template.rating_count = 0
            else:
                template.rating_avg = 0.0
                template.review_count = 0
                template.rating_count = 0


    def unlink(self):
        sale_lines = self.env['sale.order.line'].sudo().search([
            ('product_id.product_tmpl_id', 'in', self.ids)
        ])

        archived_templates = self.filtered(lambda template: template.id in sale_lines.mapped('product_id.product_tmpl_id').ids)
        deletable_templates = self - archived_templates

        if archived_templates:
            archived_templates.write({'active': False})

        if deletable_templates:
            return super(ProductTemplate, deletable_templates).unlink()

        return True


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def unlink(self):
        sale_lines = self.env['sale.order.line'].sudo().search([
            ('product_id', 'in', self.ids)
        ])

        archived_products = self.filtered(lambda product: product.id in sale_lines.mapped('product_id').ids)
        deletable_products = self - archived_products

        if archived_products:
            archived_products.write({'active': False})

        if deletable_products:
            return super(ProductProduct, deletable_products).unlink()

        return True
