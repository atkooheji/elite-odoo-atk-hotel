# -*- coding: utf-8 -*-
"""Ensure the hotel customer flag exists on partners."""

import logging

from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Add the missing ``res_partner.is_hotel_customer`` column if required."""
    if column_exists(cr, 'res_partner', 'is_hotel_customer'):
        return

    _logger.info("Adding missing res_partner.is_hotel_customer column")
    cr.execute(
        """
        ALTER TABLE res_partner
        ADD COLUMN is_hotel_customer boolean DEFAULT false
        """
    )
    # Ensure no NULL values remain in the freshly created column.
    cr.execute(
        """
        UPDATE res_partner
        SET is_hotel_customer = false
        WHERE is_hotel_customer IS NULL
        """
    )
