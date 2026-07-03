import logging
import json

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Backfill hotel.room rows that have no room_type_id.
    This runs BEFORE Odoo tries to add the NOT NULL constraint, so the
    constraint can actually be applied successfully.
    """
    # Nothing to do on a fresh install (table may not exist yet)
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'hotel_room'
        )
    """)
    if not cr.fetchone()[0]:
        _logger.info("[atk_hotel] 19.0.3.6 pre-migrate: hotel_room table does not exist — skipping.")
        return

    cr.execute("SELECT COUNT(*) FROM hotel_room WHERE room_type_id IS NULL")
    null_count = cr.fetchone()[0]
    if null_count == 0:
        _logger.info("[atk_hotel] 19.0.3.6 pre-migrate: no NULL room_type_id rows — nothing to do.")
        return

    _logger.info("[atk_hotel] 19.0.3.6 pre-migrate: %s room(s) have null room_type_id — backfilling...", null_count)

    # Check if hotel_room_type table exists
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'hotel_room_type'
        )
    """)
    type_table_exists = cr.fetchone()[0]

    if not type_table_exists:
        # Fresh install: hotel_room_type hasn't been created yet.
        # The XML data will populate it during post-init. Skip.
        _logger.info("[atk_hotel] 19.0.3.6 pre-migrate: hotel_room_type table does not exist yet — skipping backfill.")
        return

    # Prefer an already-existing room type
    default_type_id = None
    cr.execute("SELECT id FROM hotel_room_type ORDER BY id LIMIT 1")
    row = cr.fetchone()
    if row:
        default_type_id = row[0]

    if default_type_id is None:
        # Create a minimal placeholder room type so the constraint can be satisfied.
        # IMPORTANT: In Odoo 19, translatable Char fields (translate=True) are stored
        # as JSONB columns in PostgreSQL. We must insert valid JSON, not a plain string.
        # The proper types will be loaded from hotel_room_data.xml during post-init.
        name_json = json.dumps({"en_US": "Default"})
        cr.execute("""
            INSERT INTO hotel_room_type
                (name, max_adults, max_children, default_price, sequence,
                 create_date, write_date, create_uid, write_uid)
            VALUES
                (%s::jsonb, 2, 2, 0.0, 10, NOW(), NOW(), 1, 1)
            RETURNING id
        """, (name_json,))
        default_type_id = cr.fetchone()[0]
        _logger.info("[atk_hotel] 19.0.3.6 pre-migrate: created placeholder hotel.room.type id=%s", default_type_id)

    cr.execute(
        "UPDATE hotel_room SET room_type_id = %s WHERE room_type_id IS NULL",
        (default_type_id,),
    )
    _logger.info("[atk_hotel] 19.0.3.6 pre-migrate: assigned room_type_id=%s to %s room(s)", default_type_id, cr.rowcount)
