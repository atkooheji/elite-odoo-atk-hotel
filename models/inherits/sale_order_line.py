from odoo import models, fields, api, _
from odoo.fields import Command
from odoo.exceptions import ValidationError

import datetime

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    duration = fields.Integer(string="Duration", required=True, default=1)
    
    # override _compute_amount
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_ids', 'duration')
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_ids', 'duration')
    def _compute_amount(self):
        for line in self:
            quantity = line.product_uom_qty * line.duration
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            
            # Use robust compute_all to calculate taxes
            taxes = line.tax_ids.compute_all(
                price, 
                line.order_id.currency_id, 
                quantity, 
                product=line.product_id, 
                partner=line.order_id.partner_shipping_id
            )
            
            line.update({
                'price_subtotal': taxes['total_excluded'],
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
            })
        
    def _prepare_invoice_line(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.
        """
        self.ensure_one()
        res = super()._prepare_invoice_line(**optional_values)
        res['duration'] = self.duration
        return res

    def _convert_to_tax_base_line_dict(self):
        """ Inject duration into quantity for Odoo 17/18 Tax Engine """
        res = super()._convert_to_tax_base_line_dict()
        if self.duration:
            res['quantity'] *= self.duration
        return res
