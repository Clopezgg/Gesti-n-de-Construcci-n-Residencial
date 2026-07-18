"""ERPNext hooks plus the ConstruControl operational extension.

The pinned upstream hook set remains in hooks_base.py. ConstruControl adds only
its validated business rules and a filtered audit hook; ERPNext vendor hooks are
not rewritten.
"""

from erpnext.hooks_base import *  # noqa: F401,F403

_cc_doc_events = {
    "CC Funding Source": {
        "validate": "erpnext.construcontrol.controllers.validate_funding_source",
    },
    "CC Expense Control": {
        "validate": "erpnext.construcontrol.controllers.validate_expense_control",
        "on_update": "erpnext.construcontrol.controllers.update_expense_relations",
        "on_trash": "erpnext.construcontrol.controllers.remove_expense_relations",
    },
    "CC Labor Contract": {
        "validate": "erpnext.construcontrol.controllers.validate_labor_contract",
    },
    "CC Material Ledger": {
        "validate": "erpnext.construcontrol.controllers.validate_material_ledger",
    },
    "CC Inventory Movement": {
        "validate": "erpnext.construcontrol.controllers.validate_inventory_movement",
        "on_update": "erpnext.construcontrol.controllers.update_inventory_balance",
        "on_trash": "erpnext.construcontrol.controllers.remove_inventory_balance",
    },
}

# Copy before extending so importing hooks_base never mutates its module-level object.
doc_events = {key: dict(value) for key, value in doc_events.items()}
doc_events.update(_cc_doc_events)

# Frappe applies wildcard events in addition to DocType-specific events. The
# handler returns immediately for non-ConstruControl records and for migration
# writes, so standard ERPNext traffic is not duplicated.
_global_events = dict(doc_events.get("*", {}))
for _event in ("after_insert", "on_update", "on_submit", "on_cancel", "on_trash"):
    _handler = "erpnext.construcontrol.audit.record_event"
    _existing = _global_events.get(_event)
    if not _existing:
        _global_events[_event] = _handler
    elif isinstance(_existing, (list, tuple)):
        _global_events[_event] = [*_existing, _handler] if _handler not in _existing else list(_existing)
    elif _existing != _handler:
        _global_events[_event] = [_existing, _handler]
doc_events["*"] = _global_events
