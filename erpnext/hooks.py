"""ERPNext hooks plus the ConstruControl operational extension.

The pinned upstream hook set is preserved in hooks_base.py. Only the five
ConstruControl operational DocTypes are extended here, keeping the ERPNext
vendor hooks intact and auditable.
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

doc_events = dict(doc_events)
doc_events.update(_cc_doc_events)
