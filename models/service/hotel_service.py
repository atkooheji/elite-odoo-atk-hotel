# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HotelServiceCategory(models.Model):
    _name = 'hotel.service.category'
    _description = 'Hotel Service Category'
    
    name = fields.Char(string="Category Name", required=True)
    description = fields.Text(string="Description")

class HotelService(models.Model):
    _name = 'hotel.service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hotel Marketing Service'
    
    name = fields.Char(string="Service Name", required=True, tracking=True)
    category_id = fields.Many2one('hotel.service.category', string="Category", tracking=True)
    description = fields.Text(string="Description", tracking=True)
    image_1920 = fields.Image(string="Image")
    is_published = fields.Boolean(string="Published on Website", default=True)
    active = fields.Boolean(default=True)
    
    sequence = fields.Integer(default=10)
