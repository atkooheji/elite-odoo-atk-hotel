from odoo import http, fields
from odoo.http import request
import io
import json
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class IntelligenceKitController(http.Controller):

    @http.route('/hotel/export_intelligence_kit', type='http', auth='user')
    def export_intelligence_kit(self, wizard_id, **kwargs):
        wizard = request.env['hotel.report.kit.wizard'].browse(int(wizard_id))
        if not wizard.exists():
            return request.not_found()

        data = wizard._get_report_data()
        
        if not xlsxwriter:
            return request.make_response("Error: xlsxwriter library not found on this server. Please install it using 'pip install xlsxwriter'.")

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Styles
        title_style = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#C7A447'})
        header_style = workbook.add_format({'bold': True, 'bg_color': '#2C2C2C', 'font_color': 'white', 'border': 1})
        gold_style = workbook.add_format({'bold': True, 'font_color': '#C7A447'})
        money_style = workbook.add_format({'num_format': '#,##0.00'})
        pct_style = workbook.add_format({'num_format': '0.0%'})
        
        sheet = workbook.add_worksheet('Intelligence Kit')
        
        # Header
        sheet.write(0, 0, "AL FARIS INTELLIGENCE KIT", title_style)
        sheet.write(1, 0, f"Report Type: {wizard.report_type.upper()}")
        sheet.write(2, 0, f"Period: {wizard.date_from} to {wizard.date_to}")
        
        # KPI Summary
        sheet.write(4, 0, "EXECUTIVE SUMMARY", gold_style)
        sheet.write_row(5, 0, ["Metric", "Value"], header_style)
        summary_rows = [
            ["Occupancy %", data['summary']['occupancy_pct'] / 100.0],
            ["ADR", data['summary']['adr']],
            ["RevPAR", data['summary']['revpar']],
            ["GOPPAR", data['summary']['goppar']],
            ["Net Revenue", data['summary']['net_revenue']],
            ["GOP", data['summary']['gop']]
        ]
        for i, (label, val) in enumerate(summary_rows):
            sheet.write(6 + i, 0, label)
            if "%" in label:
                sheet.write(6 + i, 1, val, pct_style)
            else:
                sheet.write(6 + i, 1, val, money_style)
                
        # Room Type Profitability
        start_row = 14
        sheet.write(start_row, 0, "ROOM TYPE PROFITABILITY", gold_style)
        sheet.write_row(start_row + 1, 0, ["Room Type", "Occ %", "ADR", "RevPAR", "Rev Share %"], header_style)
        for i, row in enumerate(data['profitability']):
            r = start_row + 2 + i
            sheet.write(r, 0, row['room_type'])
            sheet.write(r, 1, row['occ_pct'] / 100.0, pct_style)
            sheet.write(r, 2, row['adr'], money_style)
            sheet.write(r, 3, row['revpar'], money_style)
            sheet.write(r, 4, row['revenue_share'] / 100.0, pct_style)

        workbook.close()
        output.seek(0)
        
        filename = f"Intelligence_Kit_{wizard.report_type}_{wizard.date_from}.xlsx"
        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}')
            ]
        )
