import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    19.0.3.11 pre-migrate: Purge stale orphan footer views that reference
    the obsolete web.brand_promotion xpath (removed in Odoo 19).

    The ghost view ir.ui.view with xmlid 'atk_hotel_footer_final_v5'
    (name: 'Planning Frontend Layout') remains in the DB from a previous
    dev iteration. When Odoo validates website.layout's child views during
    upgrade, it tries to compile this broken arch and crashes.

    This migration surgically removes that view BEFORE Odoo processes any XML.
    """
    # Step 1: Identify ALL atk_hotel views that contain brand_promotion OR have stale XML IDs
    stale_names = [
        'atk_hotel_footer_final_v5',
        'atk_hotel_footer_final_v4',
        'atk_hotel_footer_final_v3',
        'atk_hotel_footer_final_v2',
        'atk_hotel_footer_final_v1',
        'hotel_footer_v2',
        'hotel_footer_v3',
        'hotel_footer_v4',
        'hotel_footer_v5',
        'atk_hotel_footer_v1',
        'atk_hotel_footer_v2',
        'atk_hotel_footer_v3',
    ]

    # Find view IDs to delete
    cr.execute("""
        SELECT v.id, imd.name 
        FROM ir_ui_view v
        JOIN ir_model_data imd ON (imd.res_id = v.id AND imd.model = 'ir.ui.view')
        WHERE imd.module = 'atk_hotel'
          AND (imd.name = ANY(%s) OR v.arch_db::text LIKE '%%brand_promotion%%' OR v.name = 'Planning Frontend Layout')
    """, (stale_names,))
    
    to_delete = cr.fetchall()
    if not to_delete:
        _logger.info("[atk_hotel] 19.0.3.11: No stale views found to purge.")
        return

    view_ids = [r[0] for r in to_delete]
    xml_names = [r[1] for r in to_delete]

    _logger.info("[atk_hotel] 19.0.3.11: Found %d stale views to purge: %s", len(view_ids), xml_names)

    # Step 2: Delete from ir_model_data first to avoid constraint issues during Odoo's own loading
    cr.execute("DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND module = 'atk_hotel' AND res_id IN %s", (tuple(view_ids),))
    
    # Step 3: Delete from ir_ui_view
    # We use a direct SQL delete to bypass Odoo's ORM validation which might fail due to the broken arch
    cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (tuple(view_ids),))
    
    # Step 4: Nuclear Purge - Delete ANY view in the system that matches our criteria
    # and might be causing the crash, regardless of whether it has ir_model_data
    cr.execute("""
        SELECT id FROM ir_ui_view 
        WHERE (name = 'Planning Frontend Layout' OR arch_db::text LIKE '%%brand_promotion%%')
          AND (id NOT IN (SELECT res_id FROM ir_model_data WHERE model = 'ir.ui.view' AND module != 'atk_hotel'))
    """)
    extra_ids = [r[0] for r in cr.fetchall()]
    if extra_ids:
        _logger.info("[atk_hotel] 19.0.3.11: Nuclear purge found %d additional orphan views: %s", len(extra_ids), extra_ids)
        cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (tuple(extra_ids),))

    _logger.info("[atk_hotel] 19.0.3.11: Successfully purged all stale views.")

