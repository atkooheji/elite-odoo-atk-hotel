from odoo import models, fields, api


class LoyaltyPointsUpdateWizard(models.TransientModel):
    _name = 'loyalty.points.update.wizard'
    _description = 'Update Loyalty Card Points'

    # This field holds the ID of the loyalty.card record the wizard was opened from
    card_id = fields.Many2one(
        'loyalty.card',
        string="Loyalty Card",
        required=True,
        ondelete='cascade',
    )

    points_change = fields.Float(
        string="Points (+/-)",
        required=True,
        default=0.0,
        help="Enter a positive value to add points, or a negative value to deduct points."
    )

    reason = fields.Char(
        string="Reason/Description",
        required=True,
        help="The reason for this manual adjustment, which will be saved in the history."
    )

    def action_update_points(self):
        """
        Called when the user clicks the 'Update Points' button.
        It calls the add_points method on the loyalty.card record.
        """
        self.ensure_one()

        # We ensure points_change is not zero for a meaningful history record
        if self.points_change == 0.0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Change',
                    'message': 'Points change must be a non-zero value.',
                    'sticky': False,
                }
            }

        # Call the existing utility method on the loyalty.card record
        self.card_id.with_context(allow_loyalty_accrual=True).add_points(
            points=self.points_change,
            description=f"Manual Adjustment: {self.reason}"
        )

        # Return a window action to close the wizard and refresh the card view
        return {'type': 'ir.actions.act_window_close'}
