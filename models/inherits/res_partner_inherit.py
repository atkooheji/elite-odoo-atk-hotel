from odoo import api, fields, models, tools


class ResPartner(models.Model):
    _inherit = 'res.partner'

    first_name = fields.Char(string="First Name")
    middle_name = fields.Char(string="Middle Name")
    last_name = fields.Char(string="Last Name")
    is_hotel_customer = fields.Boolean(
        string="Hotel Customer",
        default=False,
        help="Indicates that this customer was created under the Hotel Booking menu.",
    )
    is_vip = fields.Boolean(string="VIP Guest")
    is_foreigner = fields.Boolean(string="Foreigner")
    is_doctor = fields.Boolean(string="Doctor")
    is_single_lady = fields.Boolean(string="Single Lady")
    receives_daily_intel_report = fields.Boolean(string="Receive Daily Intelligence", help="Subscribe this partner to the automated morning executive snapshot.")

    @api.model
    def _auto_init(self):
        """Ensure custom columns exist even if the module was not fully upgraded."""
        cr = self.env.cr
        for column, definition in (
            ("first_name", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS first_name varchar"),
            ("middle_name", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS middle_name varchar"),
            ("last_name", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS last_name varchar"),
            ("is_hotel_customer", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_hotel_customer boolean DEFAULT false"),
            ("is_vip", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_vip boolean DEFAULT false"),
            ("is_foreigner", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_foreigner boolean DEFAULT false"),
            ("is_doctor", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_doctor boolean DEFAULT false"),
            ("is_single_lady", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_single_lady boolean DEFAULT false"),
            ("receives_daily_intel_report", "ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS receives_daily_intel_report boolean DEFAULT false"),
        ):
            cr.execute(definition)
        return super()._auto_init()

    @api.model
    def _compose_full_name(self, title_id=None, first_name=None, last_name=None, middle_name=None):
        """Return the concatenated display name for a partner."""
        title_name = False
        if title_id:
            title_name = self.env['res.partner.title'].browse(title_id).shortcut

        parts = [
            title_name,
            first_name or False,
            middle_name or False,
            last_name or False,

        ]
        return ' '.join(part for part in parts if part)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if any(field in vals for field in ('first_name', 'last_name', 'middle_name', 'title')):
                name = self._compose_full_name(
                    title_id=vals.get('title'),
                    first_name=vals.get('first_name'),
                    last_name=vals.get('last_name'),
                    middle_name=vals.get('middle_name'),
                )
                if name:
                    vals['name'] = name
                else:
                    vals.setdefault('name', 'Guest')
            elif not vals.get('name'):
                vals['name'] = 'Guest'

        partners = super(ResPartner, self).create(vals_list)

        # link to hotel wizard or booking if context provided
        wizard_id = self.env.context.get('from_hotel_booking_wizard_id')
        booking_id = self.env.context.get('from_hotel_booking_id')
        
        if wizard_id or booking_id:
            for partner in partners:
                if wizard_id:
                    wizard = self.env['hotel.booking.wizard'].browse(wizard_id)
                    if wizard.exists():
                        wizard.guest_id = partner

                if booking_id:
                    booking = self.env['hotel.book.history'].browse(booking_id)
                    if booking.exists():
                        booking.partner_id = partner

        return partners

    def write(self, vals):
        name_fields = {'first_name', 'last_name', 'middle_name', 'title'}
        if name_fields.intersection(vals.keys()):
            for partner in self:
                first_name = vals.get('first_name', partner.first_name)
                last_name = vals.get('last_name', partner.last_name)
                middle_name = vals.get('middle_name', partner.middle_name)
                title_id = vals.get('title', partner.title.id if partner.title else False)
                name = partner._compose_full_name(
                    title_id=title_id,
                    first_name=first_name,
                    last_name=last_name,
                    middle_name=middle_name,
                )
                # Instead of modifying shared vals, update each partner specifically
                super(ResPartner, partner).write({'name': name or 'Guest'})
        return super(ResPartner, self).write(vals)

