"""ERPNext hooks plus the ConstruControl operational extension.

The pinned upstream hook set remains in hooks_base.py. ConstruControl adds only
its validated business rules and a filtered audit hook; ERPNext vendor hooks are
not rewritten.
"""

from erpnext.hooks_base import *  # noqa: F401,F403

_cc_doc_events = {
    "CC Funding Source": {
        "validate": [
            "erpnext.construcontrol.finance.validate_treasury_source",
            "erpnext.construcontrol.controllers.validate_funding_source",
        ],
    },
    "CC Expense Control": {
        "validate": [
            "erpnext.construcontrol.expenses.validate_professional_expense",
            "erpnext.construcontrol.controllers.validate_expense_control",
        ],
        "on_update": [
            "erpnext.construcontrol.controllers.update_expense_relations",
            "erpnext.construcontrol.expenses.sync_payable_from_expense",
        ],
        "on_trash": [
            "erpnext.construcontrol.controllers.remove_expense_relations",
            "erpnext.construcontrol.expenses.archive_payable_from_expense",
        ],
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
    "CC Financial Institution": {
        "on_trash": "erpnext.construcontrol.finance.protect_financial_institution_delete",
    },
}

doc_events = {key: dict(value) for key, value in doc_events.items()}
doc_events.update(_cc_doc_events)

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

if isinstance(app_include_css, str):
    app_include_css = [app_include_css]
else:
    app_include_css = list(app_include_css or [])
app_include_css.extend(
    [
        "/assets/erpnext/css/construcontrol.css",
        "/assets/erpnext/css/construcontrol_finance.css",
    ]
)

if isinstance(app_include_js, str):
    app_include_js = [app_include_js]
else:
    app_include_js = list(app_include_js or [])
app_include_js.extend(
    [
        "/assets/erpnext/js/construcontrol_mobile.js",
        "/assets/erpnext/js/construcontrol_profile_bridge.js",
        "/assets/erpnext/js/construcontrol_finance.js",
        "/assets/erpnext/js/construcontrol_expenses.js",
    ]
)
