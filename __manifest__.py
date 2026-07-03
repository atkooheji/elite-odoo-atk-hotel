{
    'name': 'ATK - Hotel Management System',
    'version': '19.0.1.4.0',
    'summary': 'All-in-One Hotel Management & Booking Engine App',
    'description': """
        A complete, modern Hotel Management System for Odoo.
        Fully integrated with Odoo Website for real-time room bookings and guest portal.
    """,
    'category': 'Website',
    'author': 'Indokoding Sukses Makmur',
    'depends': [
        'base', 'mail', 'sale_management', 'account', 'web', 'website',
        'portal', 'payment', 'hr', 'loyalty', 'atk_prop_mgmt', 'maintenance',
        'spreadsheet_dashboard', 'fleet',
    ],
    'data': [
        # 1. Security & Core Data
        'security/hotel_security.xml',
        'security/cleaning_security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/hotel_room_data.xml',
        'data/al_faris_suite2_data.xml',
        'data/hotel_dashboard_data.xml',
        'data/spreadsheet_dashboard_hotel.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'data/hotel_addons_data.xml',
        'data/hotel_data.xml',

        # 2. THE ROOT MENU (Must come before any view that links to it)
        'views/menus/00_hotel_root_menu.xml',

        # 3. Reports
        'report/ir_actions_report_templates.xml',
        'report/mis_report_templates.xml',
        'report/daily_status_report_templates.xml',
        'report/report.xml',
        'report/hotel_intelligence_kit_report_templates.xml',
        'report/hotel_intelligence_kit_report.xml',
        'report/hotel_report_kit_templates.xml',
        'report/report_grc.xml',
        'report/cleaning_report_templates.xml',

        # 4. Wizards
        'views/wizards/wizard_views.xml',
        'views/wizards/hotel_mis_report_wizard_views.xml',
        'wizard/hotel_transfer_room_wizard_views.xml',
        'wizard/hotel_daily_status_wizard_views.xml',
        'wizard/hotel_report_kit_wizard_views.xml',

        # 5. Model Views
        'views/inherits/product_views.xml',
        'views/inherits/loyalty_points_update_views.xml',
        'views/inherits/sale_order_views.xml',
        'views/inherits/account_move_views.xml',
        'views/inherits/loyalty_inherit_views.xml',
        'views/inherits/res_partner_inherit_views.xml',
        'views/rooms/room_views.xml',
        'views/rooms/hotel_room_type_views.xml',
        'views/rooms/amenity_views.xml',
        'views/rooms/room_inspection_views.xml',
        'views/booking/book_history_views.xml',
        'views/booking/booking_source_views.xml',
        'views/core/mis_report_views.xml',
        'views/core/dashboard_views.xml',
        'views/service/cleaning_team_views.xml',
        'views/service/cleaning_request_views.xml',
        'views/service/maintenance_request_views.xml',
        'views/config/res_config_settings_views.xml',

        # 6. Website / Portal Templates
        'views/portal/homepage_template.xml',
        'views/portal/amenities_templates.xml',
        'views/portal/concierge_templates.xml',
        'views/portal/dining_templates.xml',
        'views/portal/templates.xml',
        'views/portal/hotel_footer.xml',
        'views/portal/portal_templates.xml',
        'views/portal/review_templates.xml',
        'views/portal/snippets.xml',
        'views/portal/layout_restoration.xml',
        'views/portal/essentials_footer.xml',
        'views/portal/menu.xml',

        # 7. Final Menus
        'views/menus/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
             'atk_hotel/static/src/scss/hotel_dashboard.scss',
             'atk_hotel/static/src/dashboard/dashboard.js',
             'atk_hotel/static/src/dashboard/dashboard.xml',
             'atk_hotel/static/src/js/global_filter_export_patch.js',
        ],
        # Website frontend assets disabled to restore default Odoo website behavior.
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
