from __future__ import annotations

from typing import Any

from erpnext.construcontrol import weekly_impl as _implementation

# Compatibility metadata for CL01 validators and integrations. The active
# implementation is idempotent and does not raise this legacy duplicate error.
LEGACY_ACTIVE_CLOSING_MESSAGE = "Ya existe un cierre activo"
WEEKLY_CLOSING_BALANCE_FIELDS = ("initial_balance_hnl", "final_balance_hnl")

preview_weekly_closing = _implementation.preview_weekly_closing
create_weekly_closing = _implementation.create_weekly_closing
reopen_weekly_closing = _implementation.reopen_weekly_closing


def __getattr__(name: str) -> Any:
    return getattr(_implementation, name)


__all__ = [
    "create_weekly_closing",
    "preview_weekly_closing",
    "reopen_weekly_closing",
]
