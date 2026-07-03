from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from math import ceil
from datetime import datetime, time, timedelta
import uuid


class HotelBookHistory(models.Model):
    _name = 'hotel.book.history'
    _description = 'Hotel Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'check_in desc'

    name = fields.Char(string="Booking Reference", copy=False, readonly=True, default="New")
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        compute='_compute_company_id', 
        store=True, 
        readonly=False, 
        default=lambda self: self.env.company
    )

    @api.depends()
    def _compute_company_id(self):
        for record in self:
            if not record.company_id:
                record.company_id = self.env.company
    partner_id = fields.Many2one('res.partner', string="Guest", tracking=True)
    booking_source_id = fields.Many2one('hotel.booking.source', string="Agent/OTA", tracking=True)
    ota_source_id = fields.Many2one('hotel.booking.source', string="OTA Source", tracking=True)
    room_id = fields.Many2one('hotel.room', string="Room")
    room_type_id = fields.Many2one('product.template', string="Service Product Type", compute='_compute_room_type_id',
                                   store=True)
    physical_room_type_id = fields.Many2one('hotel.room.type', string="Room Type", compute='_compute_physical_room_type_id',
                                            store=True)

    check_in = fields.Datetime(string="Check-in", tracking=True)
    check_out = fields.Datetime(string="Check-out", tracking=True)

    duration_hours = fields.Float(string="Duration (Hours)", compute='_compute_duration', store=True)
    duration = fields.Char(string="Duration", compute='_compute_duration', store=True)
    duration_days_decimal = fields.Float(string="Duration (Days Decimal)", compute='_compute_duration', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('tentative', 'Tentative'),
        ('waitlist', 'Waitlist'),
        ('to_approve', 'To Approve'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
    ], string="Status", default='draft', required=True, tracking=True)

    is_complimentary = fields.Boolean(string="Complimentary")
    is_house_use = fields.Boolean(string="House Use")

    sale_order_id = fields.Many2one('sale.order', string="Folio")
    currency_id = fields.Many2one('res.currency', string="Currency", compute='_compute_currency_id', store=True, readonly=False)

    @api.depends('sale_order_id', 'company_id')
    def _compute_currency_id(self):
        for record in self:
            currency = False
            if record.sale_order_id:
                currency = record.sale_order_id.currency_id
            
            if not currency and record.company_id:
                currency = record.company_id.currency_id
            
            if not currency:
                currency = self.env.company.currency_id
            
            # Absolute fallback to USD or BHD if company has no currency
            if not currency:
                currency = self.env.ref('base.BHD', raise_if_not_found=False) or self.env.ref('base.USD')
            
            record.currency_id = currency

    total_amount = fields.Monetary(string="Total Amount (Gross)", compute="_compute_total_amount", store=True, readonly=True,
                                   currency_field='currency_id')
    commission_rate = fields.Float(string="Commission %", default=0.0, tracking=True)
    commission_amount = fields.Monetary(string="Commission Amount", compute="_compute_commission_amount", store=True, currency_field='currency_id')
    net_amount = fields.Monetary(string="Net Amount", compute="_compute_total_amount", store=True, currency_field='currency_id')
    has_sale_order = fields.Boolean(compute='_compute_has_sale_order')
    loyalty_card_id = fields.Many2one(
        'loyalty.card',
        string="Loyalty Card",
        compute='_compute_loyalty_card',
        store=False,
    )

    additional_product_line_ids = fields.One2many(
        'hotel.book.history.product.line',
        'booking_id',
        string="Additional Products",
    )

    passport_no = fields.Char("Passport No")
    passport_place = fields.Char("Passport Place of Issue")
    passport_expiry = fields.Date("Passport Expiry Date")

    visa_no = fields.Char("Visa No")
    visa_place = fields.Char("Visa Place of Issue")
    visa_expiry = fields.Date("Visa Expiry Date")
    visa_type = fields.Char("Visa Entry Type")

    corporate = fields.Char("Corporate")
    arrived_from = fields.Char("Arrived From")
    proceed_to = fields.Char("Proceed To")

    total_adults = fields.Integer(string="Adults", default=0)
    total_children = fields.Integer(string="Children", default=0)
    total_infants = fields.Integer(string="Infants", default=0)

    customer_signature = fields.Binary("Customer Signature")
    customer_signed_by = fields.Char("Customer Signed By", tracking=True)
    customer_signed_date = fields.Datetime("Customer Signed On", tracking=True)

    receptionist_signature = fields.Binary("Receptionist Signature")
    receptionist_signed_by = fields.Char("Receptionist Signed By", tracking=True)
    receptionist_signed_date = fields.Datetime("Receptionist Signed On", tracking=True)
    
    # QMS & MIS Tracking Fields
    approver_id = fields.Many2one('res.users', string="Approved By", readonly=True, tracking=True)
    approved_date = fields.Datetime(string="Approved On", readonly=True, tracking=True)
    
    # SLA & Performance Timestamps
    arrival_date = fields.Datetime(string="Guest Arrival Time", tracking=True, help="Actual time guest arrived at reception")
    checkin_delay = fields.Float(string="Check-in Delay (Mins)", compute="_compute_performance_metrics", store=True)
    actual_checkout_date = fields.Datetime(string="Actual Checkout Time", tracking=True)
    stay_duration_actual = fields.Float(string="Actual Stay (Hours)", compute="_compute_performance_metrics", store=True)

    show_price_split = fields.Boolean(
        string="Show Price Split-up",
        help="If enabled, Sale Order will show room rent, lavy, VAT, and fee separately. Otherwise, total inclusive price will be shown as one line.",default=True
    )

    deposit_amount = fields.Monetary(string="Deposit Amount")
    deposit_paid = fields.Boolean(string="Deposit Paid", default=False)
    deposit_payment_id = fields.Many2one('account.payment', string="Deposit Payment")
    daily_line_ids = fields.One2many(
        'hotel.booking.daily.line',
        'booking_id',
        string="Daily Breakdown",
        copy=False
    )
    # Review & Feedback
    review_ids = fields.One2many('hotel.room.review', 'booking_id', string="Reviews")
    has_review = fields.Boolean(string="Has Review", compute='_compute_has_review', store=True)
    review_request_sent = fields.Boolean(string="Review Request Sent", default=False)
    access_token = fields.Char(string="Access Token", copy=False)

    def _get_access_token(self):
        self.ensure_one()
        if not self.access_token:
            self.access_token = str(uuid.uuid4())
        return self.access_token


    @api.depends('review_ids')
    def _compute_has_review(self):
        for record in self:
            record.has_review = bool(record.review_ids)
    payment_status = fields.Selection(
        [
            ('not_invoiced', 'Not Invoiced'),
            ('invoiced', 'Invoiced'),
            ('paid', 'Paid'),
            ('partial', 'Partially Paid'),
        ],
        string="Invoice Payment Status",
        compute="_compute_payment_status",
        store=True
    )

    @api.depends('sale_order_id.invoice_ids.payment_state')
    def _compute_payment_status(self):
        for booking in self:
            if not booking.sale_order_id or not booking.sale_order_id.invoice_ids:
                booking.payment_status = 'not_invoiced'
            else:
                # Assuming single invoice
                invoice = booking.sale_order_id.invoice_ids[0]
                if invoice.payment_state == 'paid':
                    booking.payment_status = 'paid'
                elif invoice.payment_state == 'in_payment':
                    booking.payment_status = 'partial'
                else:
                    booking.payment_status = 'invoiced'

    @api.model
    def cron_request_reviews(self):
        """Send automated review requests to checked-out guests after 24 hours."""
        template = self.env.ref('atk_hotel.mail_template_hotel_review_request', raise_if_not_found=False)
        if not template:
            return
            
        one_day_ago = fields.Datetime.now() - timedelta(days=1)
        bookings = self.search([
            ('state', '=', 'checked_out'),
            ('review_request_sent', '=', False),
            ('check_out', '<=', one_day_ago),
            ('partner_id.email', '!=', False)
        ])
        
        for booking in bookings:
            booking._get_access_token()
            booking.with_context(force_send=True).message_post_with_template(template.id)
            booking.review_request_sent = True


    def action_refund_payment_al(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_("No Sale Order linked to this booking."))

        payments = self.env['account.payment'].search([
            ('payment_type', '=', 'inbound'),
            ('partner_id', '=', self.partner_id.id),
            ('state', '=', 'posted'),
            ('sale_id', '=', self.sale_order_id.id),
        ])

        if not payments:
            raise UserError(_("No payment found to refund."))

        # Create a refund payment
        for payment in payments:
            refund = self.env['account.payment'].create({
                'payment_type': 'outbound',
                'partner_type': 'customer',
                'partner_id': payment.partner_id.id,
                'amount': payment.amount,
                'journal_id': payment.journal_id.id,
                'payment_method_id': payment.payment_method_id.id,
                'payment_reference': f"Refund for {payment.name}",
            })
            refund.action_post()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Refund processed'),
                'message': _('Refund created for the payment(s) linked to this booking.'),
                'type': 'success',
                'sticky': False,
            }
        }

    # def action_view_deposit_payment(self):
    #     self.ensure_one()
    #     return {
    #         'name': 'Deposit Payment',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'account.payment',
    #         'view_mode': 'form',
    #         'res_id': self.deposit_payment_id.id,
    #     }
    #
    # def action_view_sale_order(self):
    #     self.ensure_one()
    #     return {
    #         'name': 'Sale Order',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'sale.order',
    #         'view_mode': 'form',
    #         'res_id': self.sale_order_id.id,
    #     }

    # === ONCHANGE METHODS ===
    @api.onchange('customer_signature')
    def _onchange_customer_signature(self):
        if self.customer_signature and not self.customer_signed_date:
            self.customer_signed_date = fields.Datetime.now()
            if self.partner_id:
                self.customer_signed_by = self.partner_id.name

    @api.onchange('receptionist_signature')
    def _onchange_receptionist_signature(self):
        if self.receptionist_signature and not self.receptionist_signed_date:
            self.receptionist_signed_date = fields.Datetime.now()
            self.receptionist_signed_by = self.env.user.name


    # === COMPUTE METHODS ===
    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for record in self:
            if record.check_in and record.check_out:
                params = self.env['ir.config_parameter'].sudo()
                cin_time = float(params.get_param('hotel.policy.checkin_time', 15.0))
                cout_time = float(params.get_param('hotel.policy.checkout_time', 12.0))

                # Convert float time to time object
                def float_to_time(f):
                    h = int(f)
                    m = int((f - h) * 60)
                    return time(h, m)

                POLICY_CHECK_IN = float_to_time(cin_time)
                POLICY_CHECK_OUT = float_to_time(cout_time)

                # Normalize times
                cin = datetime.combine(record.check_in.date(), POLICY_CHECK_IN)
                cout = datetime.combine(record.check_out.date(), POLICY_CHECK_OUT)

                # Calculate nights
                nights = (cout.date() - cin.date()).days
                if nights < 1:
                    nights = 1

                record.duration_days_decimal = nights
                record.duration = f"{nights} day(s)"
            else:
                record.duration_days_decimal = 0
                record.duration = "0 days"

    # ----------------------------------------------
    # 2. ONCHANGE: UPDATE CHECKOUT WHEN DURATION CHANGES
    # ----------------------------------------------
    @api.onchange('duration_days_decimal', 'check_in')
    def _onchange_duration(self):
        if self.check_in and self.duration_days_decimal:
            params = self.env['ir.config_parameter'].sudo()
            cin_time = float(params.get_param('hotel.policy.checkin_time', 15.0))
            cout_time = float(params.get_param('hotel.policy.checkout_time', 12.0))

            def float_to_time(f):
                h = int(f)
                m = int((f - h) * 60)
                return time(h, m)

            POLICY_CHECK_IN = float_to_time(cin_time)
            POLICY_CHECK_OUT = float_to_time(cout_time)

            checkin_dt = datetime.combine(self.check_in.date(), POLICY_CHECK_IN)

            # Add nights
            new_checkout_date = checkin_dt + timedelta(days=self.duration_days_decimal)

            # Apply checkout policy time
            self.check_out = datetime.combine(new_checkout_date.date(), POLICY_CHECK_OUT)

    # ----------------------------------------------
    # 3. ONCHANGE: UPDATE DURATION WHEN CHECKOUT CHANGES
    # ----------------------------------------------
    @api.onchange('check_out')
    def _onchange_checkout(self):
        if self.check_in and self.check_out:
            params = self.env['ir.config_parameter'].sudo()
            cin_time = float(params.get_param('hotel.policy.checkin_time', 15.0))
            cout_time = float(params.get_param('hotel.policy.checkout_time', 12.0))

            def float_to_time(f):
                h = int(f)
                m = int((f - h) * 60)
                return time(h, m)

            POLICY_CHECK_IN = float_to_time(cin_time)
            POLICY_CHECK_OUT = float_to_time(cout_time)

            cin = datetime.combine(self.check_in.date(), POLICY_CHECK_IN)
            cout = datetime.combine(self.check_out.date(), POLICY_CHECK_OUT)

            nights = (cout.date() - cin.date()).days
            if nights < 1:
                nights = 1

            self.duration_days_decimal = nights

    @api.depends('sale_order_id', 'state')
    def _compute_has_sale_order(self):
        for record in self:
            record.has_sale_order = record.state == 'checked_out' and bool(record.sale_order_id)

    @api.depends('partner_id')
    def _compute_loyalty_card(self):
        for booking in self:
            booking.loyalty_card_id = self.env['loyalty.card'].search(
                [('partner_id', '=', booking.partner_id.id)],
                limit=1
            ) if booking.partner_id else False

    @api.depends('room_id.room_type')
    def _compute_room_type_id(self):
        for record in self:
            record.room_type_id = record.room_id.room_type.product_tmpl_id

    @api.depends('room_id.room_type_id')
    def _compute_physical_room_type_id(self):
        for record in self:
            record.physical_room_type_id = record.room_id.room_type_id

    @api.depends('total_amount', 'commission_rate')
    def _compute_commission_amount(self):
        for record in self:
            record.commission_amount = (record.total_amount * record.commission_rate) / 100.0

    @api.depends(
        'daily_line_ids.amount',
        'additional_product_line_ids.subtotal',
        'commission_amount',
    )
    def _compute_total_amount(self):
        for record in self:
            # Total from daily lines
            daily_total = sum(record.daily_line_ids.mapped('amount'))

            # Total from additional product lines
            additional_total = sum(record.additional_product_line_ids.mapped('subtotal'))

            # Final total (Gross)
            record.total_amount = daily_total + additional_total
            # Net amount
            record.net_amount = record.total_amount - record.commission_amount

    @api.depends('arrival_date', 'check_in', 'actual_checkout_date')
    def _compute_performance_metrics(self):
        for record in self:
            # Check-in Delay (Minutes)
            if record.arrival_date and record.state in ['checked_in', 'checked_out']:
                # Assume actual check-in happened when state changed to 'checked_in'
                # For this to be accurate, we'd need to store the check-in time specifically
                # For now, if arrival_date is set, we compare it to the planned check-in
                diff = (record.arrival_date - record.check_in).total_seconds() / 60.0
                record.checkin_delay = max(diff, 0.0)
            else:
                record.checkin_delay = 0.0

            # Actual Stay Duration (Hours)
            if record.arrival_date and record.actual_checkout_date:
                diff_stay = (record.actual_checkout_date - record.arrival_date).total_seconds() / 3600.0
                record.stay_duration_actual = max(diff_stay, 0.0)
            else:
                record.stay_duration_actual = 0.0

    def action_approve(self):
        self.ensure_one()
        if not self.env.user.has_group('atk_hotel.group_hotel_manager'):
            raise UserError(_("Only managers can approve sensitive bookings."))
        self.write({
            'state': 'confirmed',
            'approver_id': self.env.user.id,
            'approved_date': fields.Datetime.now()
        })
        self._handle_room_reservation()

    def _handle_room_reservation(self):
        if self.room_id:
            if self.room_id.state == 'occupied':
                self.room_id.is_future_reserved = True
            else:
                self.room_id.state = 'reserved'

    def action_open_guest_form(self):
        self.ensure_one()
        return {
            'name': _('Create Guest'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'view_id': self.env.ref('atk_hotel.view_hotel_partner_form').id,
            'target': 'new',
            'flags': {'initial_mode': 'edit'},
            'context': {
                'default_is_hotel_customer': True,
                'default_company_type': 'person',
                'default_type': 'contact',
                'from_hotel_booking_id': self.id,
                'active_model': self._name,
                'active_id': self.id,
            },
        }

    def _action_open_loyalty_card(self, card):
        return {
            'name': _('Loyalty Card'),
            'type': 'ir.actions.act_window',
            'res_model': 'loyalty.card',
            'view_mode': 'form',
            'res_id': card.id,
            'target': 'current',
        }

    def action_create_loyalty_card(self):
        self.ensure_one()

        if not self.partner_id:
            raise ValidationError(_('Please add a guest before creating a loyalty card.'))

        card = self.loyalty_card_id or self.env['loyalty.card'].search(
            [('partner_id', '=', self.partner_id.id)],
            limit=1,
        )

        if not card:
            program = self.env['loyalty.program'].search([
                '|',
                ('company_id', '=', self.env.company.id),
                ('company_id', '=', False),
            ], limit=1)
            if not program:
                raise ValidationError(_('Please configure a loyalty program before creating a card.'))

            card = self.env['loyalty.card'].with_context(
                allow_loyalty_card_creation=True,
            ).create({
                'partner_id': self.partner_id.id,
                'program_id': program.id,
            })

        return self._action_open_loyalty_card(card)

    # === VALIDATIONS ===
    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for record in self:
            if record.check_in:
                if record.check_out <= record.check_in:
                    raise ValidationError(_("Check-out must be after check-in."))

    # @api.constrains('check_in')
    # def _check_booking_date(self):
    #     for record in self:
    #         if record.check_in and record.check_in < fields.Datetime.now():
    #             raise ValidationError(_("Booking date cannot be in the past."))

    @api.constrains('check_in', 'check_out', 'room_id')
    def _validate_availability(self):
        for record in self:
            record._check_availability()

    def _check_availability(self):
        self.ensure_one()
        if not self.check_in or not self.check_out:
            return
        if not self.room_id:
            return

        conflicts = self.env['hotel.book.history'].search([
            ('room_id', '=', self.room_id.id),
            ('id', '!=', self.id),
            ('state', 'in', ['confirmed', 'checked_in']),
            ('check_in', '<', self.check_out),
            ('check_out', '>', self.check_in),
        ])
        if conflicts:
            raise ValidationError(_("Room %s is not available from %s to %s.") % (
                self.room_id.name, self.check_in, self.check_out))

    def _generate_daily_lines(self):
        """Generate daily lines based on check-in/out duration"""
        for record in self:
            if not record.check_in or not record.check_out:
                continue

            # Convert datetimes to dates
            start_date = record.check_in.date()
            end_date = record.check_out.date()
            num_days = (end_date - start_date).days

            if num_days <= 0:
                continue

            # Remove old lines and recreate
            record.daily_line_ids.unlink()

            # Calculate base price per day (example: evenly distributed)
            # base_amount = 0
            # if record.sale_order_id:
            #     base_amount = record.sale_order_id.amount_total / num_days if num_days > 0 else 0

            # Prefer default_price from physical room type, fallback to product list_price
            room_price = record.physical_room_type_id.default_price or record.room_type_id.list_price or 0.0
            for i in range(num_days):
                day = start_date + timedelta(days=i)
                self.env['hotel.booking.daily.line'].create({
                    'booking_id': record.id,
                    'date': day,
                    'amount': room_price,
                })

    # === CRUD & BUTTONS ===
    @api.model_create_multi
    def create(self, vals_list):
        sequence_model = self.env['ir.sequence'].sudo()
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self._generate_booking_reference(sequence_model)

            partner_id = vals.get('partner_id')
            if partner_id:
                partner = self.env['res.partner'].browse(partner_id)
                if not partner.is_hotel_customer:
                    partner.is_hotel_customer = True
        records = super().create(vals_list)
        for record in records:
            record._generate_daily_lines()
        # for record in records:
        #     record.sale_order_id = record._create_sale_order(record).id
        return records

    @api.model
    def _generate_booking_reference(self, sequence_model):
        booking_code = 'hotel.booking.number'
        next_code = sequence_model.next_by_code(booking_code)
        if next_code:
            return next_code

        sequence = sequence_model.search([
            ('code', '=', booking_code),
            ('company_id', 'in', [self.env.company.id, False]),
        ], order='company_id desc', limit=1)
        if not sequence:
            sequence = sequence_model.create({
                'name': _('Hotel Booking Number'),
                'code': booking_code,
                'padding': 7,
                'company_id': self.env.company.id,
                'implementation': 'no_gap',
            })
        return sequence_model.next_by_code(booking_code) or 'New'

    # === STATE TRANSITIONS ===
    def action_confirm(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft bookings can be confirmed."))
        
        self._check_availability()
        
        # QMS Control: Manager Approval for sensitive bookings
        if self.is_complimentary or self.is_house_use:
            self.state = 'to_approve'
            return

        self.state = 'confirmed'
        
        # Folio & Deposit logic
        if not self.sale_order_id and self.total_amount > 0:
            self._create_pay_deposit()
        
        self._handle_room_reservation()

    def action_checkin(self):
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(_("Only confirmed bookings can be checked in."))
        
        # MIS Timestamp: Arrival
        self.arrival_date = fields.Datetime.now()
        
        # Validation
        if self.arrival_date < self.check_in:
             # Allowed, but log for MIS if needed. 
             pass

        self.state = 'checked_in'
        if self.room_id:
            self.room_id.state = 'occupied'

    def action_checkout(self):
        self.ensure_one()
        if self.state != 'checked_in':
            raise UserError(_("Only checked-in bookings can be checked out."))

        # MIS Timestamp: Actual Checkout
        self.actual_checkout_date = fields.Datetime.now()

        # Create Folio if missing
        if not self.sale_order_id and self.total_amount > 0:
            sale_order = self._create_sale_order(self)
            self.sale_order_id = sale_order.id

        self.state = 'checked_out'

        # Room Logic
        if self.room_id:
            if self.room_id.is_future_reserved:
                self.room_id.state = 'reserved'
                self.room_id.is_future_reserved = False
            else:
                self.room_id.state = 'available'

        # Trigger Cleaning
        self._create_checkout_cleaning_requests()

    def action_cancel(self):
        self.ensure_one()
        if self.state in ['checked_out', 'cancelled']:
            raise UserError(_("Cannot cancel completed or already cancelled booking."))
        self.state = 'cancelled'
        if self.room_id:
            self.room_id.state = 'available'
        if self.sale_order_id:
            self.sale_order_id.action_cancel()

    # def action_refund_payment(self):
    #     self.ensure_one()
    #
    #     if not self.sale_order_id:
    #         raise UserError(_("No sale order linked to this booking. Cannot refund."))
    #
    #     # Get all inbound payments related to this sale order
    #     payments = self.env['account.payment'].search([
    #         ('partner_id', '=', self.partner_id.id),
    #         ('payment_type', '=', 'inbound'),
    #         ('state', '=', 'posted'),
    #         ('invoice_ids', 'in', self.sale_order_id.invoice_ids.ids),
    #     ])
    #
    #     if not payments:
    #         raise UserError(_("No valid payments found to refund."))
    #
    #     # For simplicity, refund the first payment found
    #     payment_to_refund = payments[0]
    #     refund_amount = payment_to_refund.amount
    #
    #     # Create outbound payment (refund)
    #     refund_payment = self.env['account.payment'].create({
    #         'payment_type': 'outbound',
    #         'partner_type': 'customer',
    #         'partner_id': self.partner_id.id,
    #         'amount': refund_amount,
    #         'journal_id': payment_to_refund.journal_id.id,
    #         'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
    #         'payment_reference': f'Refund for {self.name}',
    #     })
    #     refund_payment.action_post()
    #
    #     # Optional: Log in chatter
    #     self.message_post(body=_("Refund of %s has been processed.") % refund_amount)
    #
    #     return {
    #         'type': 'ir.actions.client',
    #         'tag': 'reload',
    #     }

    # === SALE ORDER CREATION & UPDATES ===
    # === SALE ORDER CREATION / UPDATE ===
    def _prepare_sale_order_lines(self):
        self.ensure_one()
        order_lines = []

        # Ensure Accommodation Fee Product Exists
        fee_product = self.env['product.product'].search([('name', '=', 'Accommodation Fee')], limit=1)
        if not fee_product:
            fee_product = self.env['product.product'].create({
                'name': 'Accommodation Fee',
                'type': 'service',
                'sale_ok': True,
                'invoice_policy': 'order',
                'list_price': 3.3,  # inclusive of 10% VAT
                'uom_id': self.env.ref('uom.product_uom_unit').id,
            })

        room_type = self.room_id.room_type if self.room_id else False
        room_product = room_type.product_variant_id if room_type else False

        for daily in self.daily_line_ids:
            day_date = daily.date
            day_amount_inclusive = daily.amount or 0.0

            if not day_amount_inclusive:
                continue  # skip zero-value days safely

            if self.show_price_split:
                params = self.env['ir.config_parameter'].sudo()
                accom_inclusive = float(params.get_param('hotel.policy.accommodation_fee', 3.300))
                vat_rate = float(params.get_param('hotel.policy.vat_rate', 15.0)) / 100.0
                service_rate = float(params.get_param('hotel.policy.service_rate', 10.0)) / 100.0
                
                room_inclusive = max(day_amount_inclusive - accom_inclusive, 0.0)

                # Reverse calculate base + taxes
                # Assuming room rent has VAT (e.g. 15%)
                room_base = room_inclusive / (1.0 + vat_rate)
                # Assuming accommodation fee has some other tax or service (e.g. 10%)
                accom_base = accom_inclusive / (1.0 + service_rate)

                # --- Room Rent line ---
                if room_product:
                    order_lines.append((0, 0, {
                        'name': f"{self.room_id.name} - Room Rent ({day_date})",
                        'product_id': room_product.id,
                        'product_uom_id': room_product.uom_id.id,
                        'product_uom_qty': 1.0,
                        'price_unit': round(room_base, 3),
                        'tax_ids': [(6, 0, room_product.taxes_id.ids)] if room_product.taxes_id else False,
                    }))

                # --- Accommodation Fee line ---
                order_lines.append((0, 0, {
                    'name': f"Accommodation Fee ({day_date})",
                    'product_id': fee_product.id,
                    'product_uom_id': fee_product.uom_id.id,
                    'product_uom_qty': 1.0,
                    'price_unit': round(accom_base, 3),
                    'tax_ids': [(6, 0, fee_product.taxes_id.ids)] if fee_product.taxes_id else False,
                }))

                # --- Optional note ---
                order_lines.append((0, 0, {
                    'display_type': 'line_note',
                    'name': f"{day_date}: Room={room_inclusive:.3f}, Accom={accom_inclusive:.3f}, Total={day_amount_inclusive:.3f}",
                }))

            else:
                # Single daily line
                if room_product:
                    order_lines.append((0, 0, {
                        'name': f"Room Rent ({day_date})",
                        'product_id': room_product.id,
                        'product_uom_id': room_product.uom_id.id,
                        'product_uom_qty': 1.0,
                        'price_unit': round(day_amount_inclusive, 3),
                        'tax_ids': [(6, 0, room_product.taxes_id.ids)] if room_product.taxes_id else False,
                    }))

        # Additional product lines
        for line in self.additional_product_line_ids:
            if not line.product_id:
                continue
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_id': line.product_id.uom_id.id,
                'name': line.name or line.product_id.get_product_multiline_description_sale(),
                'product_uom_qty': line.quantity or 1.0,
                'price_unit': line.price_unit or 0.0,
                'tax_ids': [(6, 0, line.product_id.taxes_id.ids)] if line.product_id.taxes_id else False,
            }))

        return order_lines

    def _create_sale_order(self, record):
        order_lines = record._prepare_sale_order_lines()

        sale_order = self.env['sale.order'].create({
            'partner_id': record.partner_id.id,
            'date_order': record.check_in,
            'is_rental_order': True,
            'rental_start_date': record.check_in,
            'rental_return_date': record.check_out,
            'order_line': order_lines,
        })
        return sale_order

    def _sync_sale_order(self):
        for record in self:
            if not record.sale_order_id:
                continue

            order_vals = {}
            if record.check_in:
                order_vals.update({
                    'date_order': record.check_in,
                    'rental_start_date': record.check_in,
                })
            if record.check_out:
                order_vals['rental_return_date'] = record.check_out

            order_lines = [(5, 0, 0)] + record._prepare_sale_order_lines()
            order_vals['order_line'] = order_lines

            record.sale_order_id.write(order_vals)

    def write(self, vals):
        partner_id = vals.get('partner_id')
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            if partner.exists() and not partner.is_hotel_customer:
                partner.is_hotel_customer = True

        # Track bookings where checkout requests need to be created
        checkout_records = self.env['hotel.book.history']
        if vals.get('state') == 'checked_out':
            checkout_records = self.filtered(lambda rec: rec.state != 'checked_out')

        result = super().write(vals)

        # Recompute duration if check-in or check-out changed
        if 'check_in' in vals or 'check_out' in vals:
            self._compute_duration()

        tracked_fields = {
            'check_in',
            'check_out',
            'room_id',
            'show_price_split',
            'additional_product_line_ids',
        }
        if tracked_fields.intersection(vals):
            self._sync_sale_order()

        # Handle checkout cleaning requests
        if vals.get('state') == 'checked_out' and checkout_records:
            for booking in checkout_records:
                booking._create_checkout_cleaning_requests()

        if 'check_in' in vals or 'check_out' in vals:
            self._generate_daily_lines()

        return result

    # === CLEANING REQUESTS ===
    def _create_checkout_cleaning_requests(self):
        params = self.env['ir.config_parameter'].sudo()
        team_id = params.get_param('hotel.housekeeping.default_team_id')
        
        cleaning_team = False
        if team_id:
            cleaning_team = self.env['cleaning.team'].browse(int(team_id))
        
        if not cleaning_team or not cleaning_team.exists():
            cleaning_team = self.env['cleaning.team'].search([], limit=1)
            
        if not cleaning_team:
            raise UserError(_("Please configure a cleaning team in Settings to handle checkout cleanings."))

        cleaning_request_model = self.env['cleaning.request']
        for booking in self:
            if not booking.room_id:
                continue
            existing_request = cleaning_request_model.search([
                ('cleaning_type', '=', 'room'),
                ('room_id', '=', booking.room_id.id),
                ('state', '!=', 'done'),
            ], limit=1)
            if existing_request:
                booking.room_id.cleaning_status = 'dirty'
                continue
            cleaning_request_model.create({
                'cleaning_type': 'room',
                'room_id': booking.room_id.id,
                'team_id': cleaning_team.id,
                'description': _('Cleaning after checkout for booking %s') % booking.name,
            })

    # === UI ACTIONS ===
    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_("No sale order linked."))
        return {
            'name': _('Folio'),
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'type': 'ir.actions.act_window',
        }

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self._context.get('active_room_id'):
            res['room_id'] = self._context.get('active_room_id')
        return res

    def action_print_grc(self):
        self.ensure_one()
        report_action = self.env.ref('atk_hotel.action_report_grc', raise_if_not_found=False)
        if not report_action:
            report_template = self.env.ref('atk_hotel.report_grc_template', raise_if_not_found=False)
            if not report_template:
                raise UserError(
                    _("The Guest Registration Card template is missing. Please upgrade the Hotel module or contact your administrator."))
            report_action = self.env['ir.actions.report'].sudo().create({
                'name': _('Guest Registration Card'),
                'model': 'hotel.book.history',
                'report_name': 'atk_hotel.report_grc_template',
                'report_file': 'atk_hotel.report_grc_template',
                'report_type': 'qweb-pdf',
                'print_report_name': "'GRC - %s' % (object.name)",
            })
            self.env['ir.model.data'].sudo().create({
                'module': 'atk_hotel',
                'name': 'action_report_grc',
                'model': 'ir.actions.report',
                'res_id': report_action.id,
                'noupdate': True,
            })
        return report_action.report_action(self)

    def action_print_mis_summary(self):
        self.ensure_one()
        report_action = self.env.ref('atk_hotel.action_report_hotel_booking_summary_pdf', raise_if_not_found=False)
        if not report_action:
            report_action = self.env['ir.actions.report'].sudo().search([
                ('report_name', '=', 'atk_hotel.report_hotel_booking_summary_document')
            ], limit=1)
        if not report_action:
            raise UserError(_(
                "The booking summary report is not available. Please update the Hotel module or contact your administrator."
            ))
        return report_action.report_action(self)

    def _create_pay_deposit(self):
        self.ensure_one()
        # if self.deposit_amount <= 0:
        #     raise UserError("Deposit amount must be greater than zero.")

        # Check if deposit already paid
        if self.deposit_paid:
            raise UserError("Deposit has already been paid.")
        if self.deposit_amount > 0:
            payment = self.env['account.payment'].create({
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_id.id,
                'amount': self.deposit_amount,
                'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
                'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                'payment_reference': f'Hotel Booking Deposit: {self.name}',
            })
            # Validate the payment
            # payment.action_post()

            # Mark deposit as paid
            self.deposit_paid = True
            self.deposit_payment_id = payment.id


class HotelBookingDailyLine(models.Model):
    _name = 'hotel.booking.daily.line'
    _description = 'Daily Price Line for Hotel Booking'
    _order = 'date asc'

    booking_id = fields.Many2one('hotel.book.history', string="Booking", ondelete='cascade')
    date = fields.Date(string="Date", required=True)
    amount = fields.Monetary(string="Amount", required=True)
    currency_id = fields.Many2one('res.currency', related='booking_id.currency_id', store=True, readonly=True)

