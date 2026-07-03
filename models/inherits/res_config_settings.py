from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # AI Settings
    openai_api_key = fields.Char(
        string="OpenAI API Key",
        config_parameter='hotel.ai.openai_key',
        help="API Key for OpenAI (GPT-4o)"
    )
    
    gemini_api_key = fields.Char(
        string="Gemini API Key",
        config_parameter='hotel.ai.gemini_key',
        help="API Key for Google Gemini"
    )
    
    claude_api_key = fields.Char(
        string="Claude API Key",
        config_parameter='hotel.ai.claude_key',
        help="API Key for Anthropic Claude"
    )

    # Operational Settings
    hotel_checkin_time = fields.Float(
        string="Check-in Time",
        config_parameter='hotel.policy.checkin_time',
        default=15.0,
        help="Default check-in time (e.g. 15.0 for 3 PM)"
    )
    
    hotel_checkout_time = fields.Float(
        string="Check-out Time",
        config_parameter='hotel.policy.checkout_time',
        default=12.0,
        help="Default check-out time (e.g. 12.0 for 12 PM)"
    )

    # Financial Settings
    hotel_vat_rate = fields.Float(
        string="VAT Rate (%)",
        config_parameter='hotel.policy.vat_rate',
        default=15.0
    )
    
    hotel_service_rate = fields.Float(
        string="Service Charge (%)",
        config_parameter='hotel.policy.service_rate',
        default=10.0
    )

    hotel_accommodation_fee = fields.Float(
        string="Accommodation Fee (Inclusive)",
        config_parameter='hotel.policy.accommodation_fee',
        default=3.300
    )

    # Housekeeping Settings
    hotel_default_cleaning_team_id = fields.Many2one(
        'cleaning.team',
        string="Default Cleaning Team",
        config_parameter='hotel.housekeeping.default_team_id'
    )

    # AI Orchestration
    hotel_ai_primary_brain = fields.Selection([
        ('openai', 'OpenAI (GPT-4o)'),
        ('gemini', 'Google Gemini'),
        ('claude', 'Anthropic Claude')
    ], string="Primary AI Brain", config_parameter='hotel.ai.primary_brain', default='openai')

    hotel_ai_enable_failover = fields.Boolean(
        string="Enable Auto-Failover",
        config_parameter='hotel.ai.enable_failover',
        default=True,
        help="If the primary brain fails, automatically try other configured providers."
    )

    def action_test_openai(self):
        return self._test_ai_provider('openai')

    def action_test_gemini(self):
        return self._test_ai_provider('gemini')

    def action_test_claude(self):
        return self._test_ai_provider('claude')

    def _test_ai_provider(self, provider):
        self.ensure_one()
        # We use a dummy query to test the connection
        try:
            ai_engine = self.env['hotel.ai.engine']
            # Using a very simple prompt to minimize tokens
            response = ai_engine._try_provider(provider, "Respond with exactly the word: 'OK'")
            
            if response and "OK" in response.upper():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Successful'),
                        'message': _('The %s brain is working perfectly!') % provider.capitalize(),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_msg = _("Received unexpected response: %s") % (response or "None")
                return self._show_error(provider, error_msg)
        except Exception as e:
            return self._show_error(provider, str(e))

    def _show_error(self, provider, error):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('%s Connection Failed') % provider.capitalize(),
                'message': error,
                'type': 'danger',
                'sticky': True,
            }
        }
