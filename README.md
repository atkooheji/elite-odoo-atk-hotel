# ATK - Hotel Management System

## Overview

A complete, modern Hotel Management System for Odoo. Fully integrated with Odoo Website for real-time room bookings and guest portal.

This repository contains the standalone Odoo addon `atk_hotel` extracted from the Elite Sport Odoo project. It is intended to be versioned, reviewed, and reused independently from the full Odoo deployment repository.

## Project Details

- **Technical module name:** `atk_hotel`
- **GitHub repository:** `https://github.com/atkooheji/elite-odoo-atk-hotel`
- **Odoo version target:** Odoo 19
- **Module version:** `19.0.1.4.0`
- **Author:** Indokoding Sukses Makmur
- **License:** `LGPL-3`
- **Installable:** `True`
- **Application module:** `True`

## What This Module Does

All-in-One Hotel Management & Booking Engine App

Use this addon as part of the Elite Sport custom Odoo stack. It may depend on other ATK/Elite modules, so install dependencies first when deploying it outside the original monorepo.

## Dependencies

- `base`
- `mail`
- `sale_management`
- `account`
- `web`
- `website`
- `portal`
- `payment`
- `hr`
- `loyalty`
- `atk_prop_mgmt`
- `maintenance`
- `spreadsheet_dashboard`
- `fleet`

## Included Data and Views

- `security/hotel_security.xml`
- `security/cleaning_security.xml`
- `security/ir.model.access.csv`
- `data/sequence.xml`
- `data/hotel_room_data.xml`
- `data/al_faris_suite2_data.xml`
- `data/hotel_dashboard_data.xml`
- `data/spreadsheet_dashboard_hotel.xml`
- `data/mail_template_data.xml`
- `data/ir_cron_data.xml`
- `data/hotel_addons_data.xml`
- `data/hotel_data.xml`
- `views/menus/00_hotel_root_menu.xml`
- `report/ir_actions_report_templates.xml`
- `report/mis_report_templates.xml`
- `report/daily_status_report_templates.xml`
- `report/report.xml`
- `report/hotel_intelligence_kit_report_templates.xml`
- `report/hotel_intelligence_kit_report.xml`
- `report/hotel_report_kit_templates.xml`
- `report/report_grc.xml`
- `report/cleaning_report_templates.xml`
- `views/wizards/wizard_views.xml`
- `views/wizards/hotel_mis_report_wizard_views.xml`
- `wizard/hotel_transfer_room_wizard_views.xml`
- `wizard/hotel_daily_status_wizard_views.xml`
- `wizard/hotel_report_kit_wizard_views.xml`
- `views/inherits/product_views.xml`
- `views/inherits/loyalty_points_update_views.xml`
- `views/inherits/sale_order_views.xml`
- `views/inherits/account_move_views.xml`
- `views/inherits/loyalty_inherit_views.xml`
- `views/inherits/res_partner_inherit_views.xml`
- `views/rooms/room_views.xml`
- `views/rooms/hotel_room_type_views.xml`
- `views/rooms/amenity_views.xml`
- `views/rooms/room_inspection_views.xml`
- `views/booking/book_history_views.xml`
- `views/booking/booking_source_views.xml`
- `views/core/mis_report_views.xml`
- `views/core/dashboard_views.xml`
- `views/service/cleaning_team_views.xml`
- `views/service/cleaning_request_views.xml`
- `views/service/maintenance_request_views.xml`
- `views/config/res_config_settings_views.xml`
- `views/portal/homepage_template.xml`
- `views/portal/amenities_templates.xml`
- `views/portal/concierge_templates.xml`
- `views/portal/dining_templates.xml`
- `views/portal/templates.xml`
- `views/portal/hotel_footer.xml`
- `views/portal/portal_templates.xml`
- `views/portal/review_templates.xml`
- `views/portal/snippets.xml`
- `views/portal/layout_restoration.xml`
- `views/portal/essentials_footer.xml`
- `views/portal/menu.xml`
- `views/menus/menu_views.xml`

## Demo Data

- None declared

## Repository Structure

- `__manifest__.py` - Odoo module manifest
- `__init__.py` - module initialization
- `models/` - 36 file(s)
- `views/` - 38 file(s)
- `security/` - 3 file(s)
- `data/` - 10 file(s)
- `controllers/` - 5 file(s)
- `static/` - 24 file(s)
- `wizard/` - 14 file(s)
- `report/` - 13 file(s)
- `docs/` - 9 file(s)
- `tests/` - 3 file(s)

## Installation

1. Copy this addon folder into an Odoo addons path, for example `/mnt/extra-addons/atk_hotel`.
2. Make sure all dependencies listed above are installed or available in the same Odoo database.
3. Restart the Odoo service so the addon path is rescanned.
4. Activate developer mode in Odoo.
5. Go to **Apps**, update the apps list, search for `atk_hotel`, and install it.

## Upgrade

After pulling changes into an existing Odoo environment, upgrade the module with:

```bash
odoo-bin -d <database_name> -u atk_hotel --stop-after-init
```

For Odoo.sh, push the branch and upgrade the module from the Odoo Apps interface or through the deployment upgrade flow.

## Development Workflow

1. Create a feature branch from `main`.
2. Make changes inside this addon only.
3. Test installation and upgrade on a local/staging database.
4. Check server logs for registry, XML, access-rights, and dependency errors.
5. Commit with a clear message and open a pull request before production use.

## Testing Checklist

- Module installs without registry errors.
- Module upgrades cleanly from the previous version.
- Menus, views, security groups, and access rights load correctly.
- Any scheduled actions, controllers, or integrations run as expected.
- No secrets, database dumps, or environment files are committed.

## Security Notes

This is a public repository. Do not commit `.env` files, credentials, customer data, database backups, private tokens, or production logs. Keep deployment-specific configuration outside the addon source.

## Source Context

Extracted from the Elite Sport Odoo project under:

```text
D:\001-AntiGravity\003-Odoo\elite_sport_project-main\elite_sport_project-main\addons\atk_hotel
```
