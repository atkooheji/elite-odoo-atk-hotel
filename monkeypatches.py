"""Runtime monkey patches for Odoo quirks.

The real Odoo ORM occasionally leaves placeholder ``_unknown`` values on
many2one fields during onchanges.  When the web client attempts to read
these unresolved values it triggers an ``AttributeError`` because the
placeholder lacks an ``id`` attribute.  That exception bubbles up as the
``'_unknown' object has no attribute 'id'`` RPC error seen in the UI.

To keep the UI responsive we defensively intercept that situation and
coerce unresolved values to ``False`` instead of letting the error
propagate.  The patch is only applied when a real Odoo environment is
available and is idempotent so it won't be reapplied during module
reloads.
"""

from __future__ import annotations

from typing import Any, Callable
import logging

_logger = logging.getLogger(__name__)


def patch_safe_many2one_convert_to_read() -> None:
    """Make :class:`~odoo.fields.Many2one` tolerant of unresolved values.

    The patch wraps ``convert_to_read`` so that placeholder values without
    an ``id`` (e.g. ``_unknown``) are treated as ``False`` rather than
    raising an :class:`AttributeError` during web client onchange diffs.
    """

    try:
        from odoo import fields  # type: ignore
    except Exception:  # pragma: no cover - executed only in real Odoo
        return

    # Avoid stacking the wrapper if the module is reloaded.
    if getattr(fields.Many2one, "_safe_convert_to_read_patched", False):
        return

    original_convert: Callable[[Any, Any, Any, bool], Any] = fields.Many2one.convert_to_read

    def safe_convert(self, value: Any, record: Any, use_display_name: bool = False):  # type: ignore[override]
        if value and not hasattr(value, "id"):
            placeholder_name = getattr(value.__class__, "__name__", "<unknown>")
            if placeholder_name == "_unknown":
                _logger.debug("Treating unresolved many2one value as False for %s", self.name)
                return False

        try:
            return original_convert(self, value, record, use_display_name)
        except AttributeError:
            return False

    fields.Many2one.convert_to_read = safe_convert  # type: ignore[assignment]
    fields.Many2one._safe_convert_to_read_patched = True


__all__ = ["patch_safe_many2one_convert_to_read"]
