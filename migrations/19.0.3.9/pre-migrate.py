import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    19.0.3.9 pre-migrate: Purge stale orphan footer views left over from
    old development iterations that reference web.brand_promotion xpath
    which no longer exists in Odoo 19's website.layout.

    These orphan views cause a ParseError during module load:
        Element '<xpath expr="//t[@t-call='web.brand_promotion']">'
        cannot be located in parent view
    """
    stale_xmlids = [
        'atk_hotel.atk_hotel_footer_final_v5',
        'atk_hotel.hotel_footer_v2',
        'atk_hotel.hotel_footer_v3',
        'atk_hotel.hotel_footer_v4',
        'atk_hotel.atk_hotel_footer_v1',
        'atk_hotel.atk_hotel_footer_v2',
        'atk_hotel.atk_hotel_footer_v3',
    ]

    # Step 1: delete orphan ir.ui.view records by xmlid
    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE model = 'ir.ui.view'
              AND module = 'atk_hotel'
              AND name IN %s
        )
    """, (tuple(name.split('.', 1)[1] for name in stale_xmlids),))

    deleted_views = cr.rowcount
    if deleted_views:
        _logger.info("[atk_hotel] 19.0.3.9: Deleted %d stale orphan view(s).", deleted_views)

    # Step 2: clean the ir_model_data entries for these xmlids
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE model = 'ir.ui.view'
          AND module = 'atk_hotel'
          AND name IN %s
    """, (tuple(name.split('.', 1)[1] for name in stale_xmlids),))

    deleted_refs = cr.rowcount
    if deleted_refs:
        _logger.info("[atk_hotel] 19.0.3.9: Cleaned %d stale ir_model_data ref(s).", deleted_refs)

    # Step 3: nuclear option — delete ANY view that uses the broken xpath pattern
    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE arch_db::text LIKE '%%brand_promotion%%'
          AND (SELECT module FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id = ir_ui_view.id LIMIT 1) = 'atk_hotel'
    """)
    nuclear_count = cr.rowcount
    if nuclear_count:
        _logger.info("[atk_hotel] 19.0.3.9: Nuclear purge removed %d view(s) with brand_promotion xpath.", nuclear_count)

    # Also clean up any view named 'Planning Frontend Layout' from atk_hotel
    cr.execute("""
        DELETE FROM ir_ui_view v
        USING ir_model_data d
        WHERE d.model = 'ir.ui.view'
          AND d.res_id = v.id
          AND d.module = 'atk_hotel'
          AND v.name = 'Planning Frontend Layout'
    """)
    named_count = cr.rowcount
    if named_count:
        _logger.info("[atk_hotel] 19.0.3.9: Removed %d 'Planning Frontend Layout' orphan view(s).", named_count)

    _logger.info("[atk_hotel] 19.0.3.9: Stale footer view purge complete.")
