from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

import datetime

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    duration = fields.Integer(string="Duration", default=1)
    
    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    def _compute_totals(self):
        res = super(AccountMoveLine, self)._compute_totals()
        
        for line in self:
            if line.display_type != 'product':
                line.price_total = line.price_subtotal = False
            # Compute 'price_subtotal'.
            line_discount_price_unit = line.price_unit * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line.duration * line_discount_price_unit

            # Compute 'price_total'.
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=line.quantity * line.duration,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
            else:
                line.price_total = line.price_subtotal = subtotal
                
        return res
    
    def _prepare_base_line_for_taxes_computation(self):
        """ Inject duration into quantity for Odoo 17/18 Tax Engine """
        res = super()._prepare_base_line_for_taxes_computation()
        if self.display_type == 'product' and self.duration:
            res['quantity'] *= self.duration
        return res

    def _convert_to_tax_base_line_dict(self):
        """ Fallback for certain Odoo 17 subversions """
        res = super()._convert_to_tax_base_line_dict()
        if self.display_type == 'product' and self.duration:
            res['quantity'] *= self.duration
        return res
    
    
