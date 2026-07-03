"""Ensure partner name columns exist for the hotel module."""

import logging

from odoo.tools.sql import column_exists

_LOGGER = logging.getLogger(__name__)


_COLUMNS = (
    ("first_name", "ALTER TABLE res_partner ADD COLUMN first_name varchar"),
    ("middle_name", "ALTER TABLE res_partner ADD COLUMN middle_name varchar"),
    ("last_name", "ALTER TABLE res_partner ADD COLUMN last_name varchar"),
)


def migrate(cr, version):
    """Add missing partner name columns introduced by the hotel module."""
    for column, ddl in _COLUMNS:
        if column_exists(cr, "res_partner", column):
            continue

        _LOGGER.info("Adding missing res_partner.%s column", column)
        cr.execute(ddl)
