from odoo import models, fields, api, _
import base64
import logging

_logger = logging.getLogger(__name__)

class HotelReportingAgent(models.TransientModel):
    """
    Generates AI-enhanced reports for the hotel.
    """
    _name = 'hotel.reporting.agent'
    _description = 'Hotel Al Reporting Agent'

    report_type = fields.Selection([
        ('morning_brief', 'Morning Briefing'),
        ('weekly_summary', 'Weekly Performance'),
        ('investor_update', 'Investor Update')
    ], string="Report Type", required=True)
    
    period = fields.Selection([
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month')
    ], default='today')
    
    generated_content = fields.Html("Generated Content", readonly=True)

    def action_generate(self):
        """Analyzes data and generates the report text."""
        dashboard_service = self.env['hotel.dashboard.service']
        
        # 1. Fetch Data
        # We need to contextually call get_dashboard_data logic
        # For simplicity, we initialize the service and get raw data
        # Note: dashboard service usually returns data based on context/args
        raw_data = dashboard_service.get_dashboard_data(period=self.period)
        
        # 2. Prepare Prompt
        prompt = f"Generate a {dict(self._fields['report_type'].selection).get(self.report_type)} for the {self.period}."
        
        # 3. Call AI
        ai_response = self.env['hotel.ai.engine'].query_bot(prompt, raw_data)
        
        self.generated_content = ai_response
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.reporting.agent',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_download_pdf(self):
        # Placeholder for real PDF generation
        # In a real scenario, we'd pass 'generated_content' to QWeb report
        return {'type': 'ir.actions.act_window_close'}
