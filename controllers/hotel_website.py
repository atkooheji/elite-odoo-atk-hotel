from odoo import http, fields, _
from odoo.http import request
from datetime import datetime, timedelta
import json

class HotelWebsite(http.Controller):

    def _get_stay_details(self, kwargs):
        """Helper to extract and validate stay details."""
        check_in = kwargs.get('check_in')
        check_out = kwargs.get('check_out')
        adults = int(kwargs.get('adults', 2))
        children = int(kwargs.get('children', 0))
        
        ci_date = fields.Date.from_string(check_in) if check_in else None
        co_date = fields.Date.from_string(check_out) if check_out else None
        
        nights = 0
        if ci_date and co_date:
            nights = (co_date - ci_date).days
            if nights < 1: nights = 1
            
        return {
            'check_in': check_in,
            'check_out': check_out,
            'adults': adults,
            'children': children,
            'nights': nights,
        }

    def _get_booking_token(self, params):
        return (params.get('access_token') or params.get('token') or '').strip()

    def _can_access_booking(self, booking, params=None):
        """Allow portal owners or callers with the booking access token."""
        booking = booking.sudo()
        params = params or {}
        token = self._get_booking_token(params)
        if token and booking.access_token and token == booking.access_token:
            return True

        user = request.env.user
        if not user._is_public() and booking.partner_id == user.partner_id:
            return True

        return False

    def _booking_step_url(self, booking, step):
        booking = booking.sudo()
        token = booking._get_access_token()
        return f'/hotel/booking/{booking.id}/{step}?access_token={token}'

    @http.route(['/hotel', '/hotel-home'], type='http', auth='public', website=True)
    def hotel_home(self, **kwargs):
        """Dynamic Home Page with featured rooms and services."""
        featured_rooms = request.env['hotel.room.type'].sudo().search([
            ('is_published', '=', True)
        ], limit=3)
        if not featured_rooms:
            featured_rooms = request.env['hotel.room.type'].sudo().search([], limit=3)
        
        featured_services = request.env['hotel.service'].sudo().search([
            ('is_published', '=', True)
        ], limit=3)
        if not featured_services:
            featured_services = request.env['hotel.service'].sudo().search([], limit=3)
        
        stay = self._get_stay_details(kwargs)
        
        values = {
            'featured_rooms': featured_rooms,
            'featured_services': featured_services,
            'stay': stay,
        }
        return request.render('atk_hotel.alfaris_homepage', values)

    @http.route('/hotel/lifestyle', type='http', auth='public', website=True)
    def hotel_lifestyle(self, **kwargs):
        """Lifestyle page with dynamic services."""
        services = request.env['hotel.service'].sudo().search([
            ('is_published', '=', True),
            ('category_id.name', '!=', 'Dining')
        ])
        if not services:
            services = request.env['hotel.service'].sudo().search([
                ('category_id.name', '!=', 'Dining')
            ])
        return request.render('atk_hotel.alfaris_amenities', {
            'services': services,
        })

    @http.route('/hotel/dining', type='http', auth='public', website=True)
    def hotel_dining(self, **kwargs):
        """Dining page with dynamic dining services."""
        dining_services = request.env['hotel.service'].sudo().search([
            ('is_published', '=', True),
            ('category_id.name', '=', 'Dining')
        ])
        if not dining_services:
            dining_services = request.env['hotel.service'].sudo().search([
                ('category_id.name', '=', 'Dining')
            ])
        return request.render('atk_hotel.alfaris_dining', {
            'dining_services': dining_services,
        })

    @http.route('/hotel/rooms', type='http', auth='public', website=True)
    def hotel_rooms(self, **kwargs):
        """Premium room listing with live total calculation."""
        stay = self._get_stay_details(kwargs)
        
        # Fallback to all room types if published filter is too restrictive or not yet synced
        room_types = request.env['hotel.room.type'].sudo().search([('is_published', '=', True)])
        if not room_types:
            room_types = request.env['hotel.room.type'].sudo().search([], limit=10)
        
        available_types = room_types

        values = {
            'room_types': available_types,
            'stay': stay,
            'check_in': stay['check_in'],
            'check_out': stay['check_out'],
            'adults': stay['adults'],
            'children': stay['children'],
        }
        return request.render('atk_hotel.hotel_room_listing', values)

    @http.route('/hotel/room/<model("hotel.room.type"):room_type>', type='http', auth='public', website=True)
    def hotel_room_details(self, room_type, **kwargs):
        """Detailed view for a room type with price summary."""
        stay = self._get_stay_details(kwargs)
        reviews = request.env['hotel.room.review'].sudo().search([
            ('room_id.room_type_id', '=', room_type.id),
            ('is_published', '=', True)
        ], limit=5)
        
        return request.render('atk_hotel.hotel_room_details', {
            'room_type': room_type,
            'reviews': reviews,
            'stay': stay,
            'check_in': stay['check_in'],
            'check_out': stay['check_out'],
        })

    @http.route(['/hotel/book/start', '/hotel/reserve'], type='http', auth='public', website=True, methods=['GET', 'POST'])
    def hotel_booking_start(self, **post):
        """Initiate booking process (Public Access)."""
        room_type_id = int(post.get('room_type_id', 0))
        if not room_type_id:
             return request.redirect('/hotel/rooms')
        check_in = post.get('check_in')
        check_out = post.get('check_out')
        adults = int(post.get('adults', 2))
        children = int(post.get('children', 0))
        
        # Room Selection Logic
        room_type = request.env['hotel.room.type'].sudo().browse(room_type_id)
        ci = fields.Date.from_string(check_in)
        co = fields.Date.from_string(check_out)
        
        rooms = request.env['hotel.room'].sudo().search([('room_type_id', '=', room_type.id)])
        available_room = next((r for r in rooms if r.is_available_for_dates(ci, co)), None)
        
        if not available_room:
            return request.redirect('/hotel/rooms?error=no_availability')
            
        # Create draft booking
        # If user is logged in, link partner. If not, leave for confirmation step.
        partner = request.env.user.partner_id if not request.env.user._is_public() else False
        
        booking_vals = {
            'room_id': available_room.id,
            'check_in': ci,
            'check_out': co,
            'total_adults': adults,
            'total_children': children,
            'state': 'draft',
        }
        if partner:
            booking_vals['partner_id'] = partner.id
            
        booking = request.env['hotel.book.history'].sudo().create(booking_vals)
        booking._get_access_token()
        
        return request.redirect(self._booking_step_url(booking, 'confirm'))

    @http.route('/hotel/booking/<model("hotel.book.history"):booking>/confirm', type='http', auth='public', website=True)
    def hotel_booking_confirm(self, booking, **kw):
        """Step 2: Guest Details."""
        if not self._can_access_booking(booking, kw):
             return request.redirect('/hotel')

        return request.render('atk_hotel.hotel_booking_details', {
            'booking': booking.sudo(),
            'is_public': request.env.user._is_public(),
            'access_token': self._get_booking_token(kw),
        })

    @http.route('/hotel/booking/<model("hotel.book.history"):booking>/details/save', type='http', auth='public', website=True, methods=['POST'])
    def hotel_booking_details_save(self, booking, **post):
        """Save guest details and move to Enhance step."""
        booking_sudo = booking.sudo()
        if not self._can_access_booking(booking_sudo, post):
            return request.redirect('/hotel')
        if booking_sudo.state != 'draft':
            return request.redirect('/hotel')

        if request.env.user._is_public():
            email = post.get('email')
            name = post.get('name')
            phone = post.get('phone')
            
            Partner = request.env['res.partner'].sudo()
            partner = Partner.search([('email', '=', email)], limit=1)
            if not partner:
                partner = Partner.create({
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'is_hotel_customer': True,
                })
            booking_sudo.write({'partner_id': partner.id})
        
        return request.redirect(self._booking_step_url(booking_sudo, 'enhance'))

    @http.route('/hotel/booking/<model("hotel.book.history"):booking>/enhance', type='http', auth='public', website=True)
    def hotel_booking_enhance(self, booking, **kw):
        """Step 3: Upselling / Add-ons."""
        booking_sudo = booking.sudo()
        if not self._can_access_booking(booking_sudo, kw) or booking_sudo.state != 'draft':
            return request.redirect('/hotel')

        add_ons = request.env['product.template'].sudo().search([
            ('is_hotel_service', '=', True),
            ('sale_ok', '=', True)
        ])

        return request.render('atk_hotel.hotel_booking_addons', {
            'booking': booking_sudo,
            'add_ons': add_ons,
            'access_token': self._get_booking_token(kw),
        })

    @http.route('/hotel/booking/<model("hotel.book.history"):booking>/enhance/save', type='http', auth='public', website=True, methods=['POST'])
    def hotel_booking_enhance_save(self, booking, **post):
        """Save add-ons and move to Payment."""
        booking_sudo = booking.sudo()
        if not self._can_access_booking(booking_sudo, post) or booking_sudo.state != 'draft':
            return request.redirect('/hotel')

        # Clear existing add-ons if any (re-entry logic)
        booking_sudo.additional_product_line_ids.unlink()

        for key, value in post.items():
            if key.startswith('addon_') and value == 'on':
                product_id = int(key.split('_')[1])
                product = request.env['product.template'].sudo().browse(product_id)
                if product.exists():
                    request.env['hotel.book.history.product.line'].sudo().create({
                        'booking_id': booking_sudo.id,
                        'product_id': product.product_variant_id.id,
                        'qty': 1,
                        'price_unit': product.list_price,
                    })
        
        # Finalize booking
        booking_sudo.action_confirm()
        
        return request.render('atk_hotel.hotel_booking_thank_you', {
            'booking': booking_sudo,
        })

    @http.route('/hotel/booking/<model("hotel.book.history"):booking>/review', type='http', auth='user', website=True)
    def hotel_review_form(self, booking, **kw):
        """Render review form for a completed booking (Logged in)."""
        if booking.state != 'checked_out' or booking.partner_id != request.env.user.partner_id:
            return request.redirect('/hotel')
        if booking.has_review:
            return request.render('atk_hotel.hotel_review_thanks')
            
        return request.render('atk_hotel.hotel_room_review_form', {'booking': booking})

    @http.route('/hotel/review/token/<string:token>', type='http', auth='public', website=True)
    def hotel_review_form_token(self, token, **kw):
        """Render review form for a completed booking using access token (Public)."""
        booking = request.env['hotel.book.history'].sudo().search([('access_token', '=', token)], limit=1)
        if not booking or booking.state != 'checked_out':
            return request.redirect('/hotel')
        if booking.has_review:
            return request.render('atk_hotel.hotel_review_thanks')
            
        return request.render('atk_hotel.hotel_room_review_form', {
            'booking': booking,
            'token': token
        })

    @http.route('/my/stay/dashboard', type='http', auth='user', website=True)
    def hotel_stay_dashboard(self, **kw):
        """Render the Digital Concierge for the currently checked-in stay."""
        partner = request.env.user.partner_id
        # Find active stay (checked_in)
        booking = request.env['hotel.book.history'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'checked_in')
        ], limit=1, order='check_in desc')
        
        if not booking:
            # Fallback to last confirmed booking or redirect to my stays
            return request.redirect('/my/stays')
            
        return request.render('atk_hotel.portal_my_stay_dashboard', {
            'booking': booking,
        })

    @http.route('/hotel/review/submit', type='http', auth='public', website=True, methods=['POST'])
    def hotel_review_submit(self, **post):
        """Create a review record (Public or User)."""
        booking_id = int(post.get('booking_id'))
        token = post.get('token')
        
        if token:
            booking = request.env['hotel.book.history'].sudo().search([
                ('id', '=', booking_id),
                ('access_token', '=', token)
            ], limit=1)
        else:
            if not request.env.user.partner_id:
                return request.redirect('/hotel')
            booking = request.env['hotel.book.history'].sudo().browse(booking_id)
            if booking.partner_id != request.env.user.partner_id:
                return request.redirect('/hotel')

        if not booking or booking.has_review or booking.state != 'checked_out':
            return request.redirect('/hotel')
            
        request.env['hotel.room.review'].sudo().create({
            'partner_id': booking.partner_id.id,
            'room_id': booking.room_id.id,
            'booking_id': booking.id,
            'rating': post.get('rating', '5'),
            'comment': post.get('comment'),
            'is_published': True, # Auto-publish for now
        })
        
        return request.render('atk_hotel.hotel_review_thanks')

