# -*- coding: utf-8 -*-
"""Extend Hr Employee for hotel customizations."""
from odoo import fields, models


class HrEmployee(models.Model):
    """Provide compatibility fields used by the hotel module views."""

    _inherit = 'hr.employee'

    mobile = fields.Char(
        related='mobile_phone',
        readonly=False,
        string='Mobile',
        help="Employee mobile number (alias of the mobile phone field).",
    )
