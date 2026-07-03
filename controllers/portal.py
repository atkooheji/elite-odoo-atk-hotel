from odoo import fields, http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.web.controllers.report import ReportController
import logging

_logger = logging.getLogger(__name__)


class HotelPortal(CustomerPortal):
    """Frontend routes for searching rooms, booking and paying."""

    @http.route('/hotel/booking/<int:booking_id>/pay', type='http', auth='user', website=True)
    def hotel_booking_pay(self, booking_id, **kw):
        """Generate invoice and redirect to portal payment."""
        # CRIT-12 fix: verify the booking belongs to the requesting user
        booking = request.env['hotel.book.history'].sudo().browse(booking_id)
        if not booking.exists() or booking.partner_id != request.env.user.partner_id:
            _logger.warning(
                "IDOR attempt: user %s tried to access booking %s owned by partner %s",
                request.env.user.id, booking_id,
                booking.partner_id.id if booking.exists() else 'N/A',
            )
            return request.redirect('/hotel/rooms')

        sale_order = booking.sale_order_id
        if sale_order.state != 'sale':
            sale_order.action_confirm()
        invoices = sale_order._create_invoices()
        invoice = invoices and invoices[0]
        if invoice:
            invoice.action_post()
            return request.redirect(invoice.get_portal_url())
        return request.redirect('/hotel/rooms')

    @http.route(['/my/stays'], type='http', auth="user", website=True)
    def portal_my_stays(self, **kw):
        values = self._prepare_portal_layout_values()
        bookings = request.env['hotel.book.history'].sudo().search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ], order='check_in desc')
        values.update({
            'bookings': bookings,
            'page_name': 'hotel_stays',
        })
        return request.render("atk_hotel.portal_my_stays", values)


class CustomerPortalInherit(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'hotel_booking_count' in counters:
            values['hotel_booking_count'] = request.env['hotel.book.history'].sudo().search_count([
                ('partner_id', '=', request.env.user.partner_id.id)
            ])
        return values


class SalePortalFix(CustomerPortal):
    """
    Overrides the portal order page to force direct PDF rendering on iOS.
    This prevents the common 'broken HTML page' issue caused by Safari stalls.
    """
    @http.route(['/my/orders/<int:order_id>'], type='http', auth="public", website=True)
    def portal_order_page(self, order_id, report_type=None, access_token=None, **kw):
        if report_type == 'pdf':
            _logger.info("Direct PDF Stream triggered for Sale Order %s (iOS Fix)", order_id)
            try:
                # Access the order with sudo to bypass multi-hop auth checks
                order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
                if not order_sudo:
                    return request.redirect('/my/orders')
                
                # Render the PDF specifically using the standard Sale Order template
                report = request.env.ref('sale.action_report_saleorder')
                pdf_content, _ = report.sudo()._render_qweb_pdf([order_sudo.id])
                
                # Serve with clear PDF headers - Safari will open this in a new tab normally
                filename = "SaleOrder_%s.pdf" % order_sudo.name
                return request.make_response(pdf_content, headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Length', len(pdf_content)),
                    ('Content-Disposition', 'inline; filename="%s"' % filename),
                    ('X-Content-Type-Options', 'nosniff'),
                ])
            except Exception as e:
                _logger.error("Direct PDF Render Failed: %s", str(e))
        
        return super(SalePortalFix, self).portal_order_page(order_id, report_type=report_type, access_token=access_token, **kw)


class SaleReportFix(ReportController):
    """
    Intercepts the backend report route for Sale Orders.
    Ensures that PDF requests are handled with absolute session priority.
    """
    @http.route(['/report/pdf/sale.report_saleorder/<string:docids>', 
                 '/report/pdf/sale.report_saleorder_pro_forma/<string:docids>'], 
                type='http', auth="user")
    def report_saleorder_ios_backend(self, docids, **data):
        _logger.info("Backend PDF Fix for Sale Order %s", docids)
        return super(SaleReportFix, self).report_download('sale.report_saleorder', docids, converter='pdf', **data)
