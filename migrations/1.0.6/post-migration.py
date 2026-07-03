"""Ensure the Hotel Daily Status report actions exist."""

import logging

from odoo import SUPERUSER_ID, api

_LOGGER = logging.getLogger(__name__)

_REPORTS = (
    ("action_report_hotel_daily_status_pdf", "Hotel Daily Status", "qweb-pdf"),
    ("action_report_hotel_daily_status_html", "Hotel Daily Status (HTML)", "qweb-html"),
)


def _create_missing_report(env, xmlid, name, report_type, binding_model_id=None):
    report_action = env["ir.actions.report"].create({
        "name": name,
        "model": "hotel.dashboard",
        "report_name": "atk_hotel.report_hotel_daily_status_document",
        "report_file": "atk_hotel.report_hotel_daily_status_document",
        "report_type": report_type,
        "binding_model_id": binding_model_id,
        "binding_type": "report",
        "print_report_name": "'Hotel Daily Status - %s' % (object.date_range_label or 'Today')",
    })

    env["ir.model.data"].create({
        "module": "atk_hotel",
        "name": xmlid,
        "model": "ir.actions.report",
        "res_id": report_action.id,
    })

    return report_action


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    template = env.ref("atk_hotel.report_hotel_daily_status_document", raise_if_not_found=False)
    if not template:
        _LOGGER.warning(
            "Skipping Hotel Daily Status report action recreation because the template is missing."
        )
        return

    binding_model = env.ref("atk_hotel.model_hotel_dashboard", raise_if_not_found=False)

    for xmlid, name, report_type in _REPORTS:
        action = env.ref(f"atk_hotel.{xmlid}", raise_if_not_found=False)
        if action:
            continue

        _LOGGER.info("Creating missing Hotel Daily Status report action: %s", xmlid)
        _create_missing_report(env, xmlid, name, report_type, binding_model.id if binding_model else None)
