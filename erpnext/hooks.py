"""ERPNext hooks plus the canonical ConstruControl extension.

The pinned upstream hook set remains in hooks_base.py. ConstruControl adds only
validated business rules, one application shell, specialized form controllers,
and a filtered audit hook. ERPNext vendor hooks are not rewritten.
"""

from erpnext.hooks_base import *

_PROJECT_ACCESS_HANDLER = "erpnext.construcontrol.access.validate_document_project_access"
_PROJECT_SCOPED_DOCTYPES = (
	"CC Approval Request",
	"CC Change Order",
	"CC Construction Phase",
	"CC Crew Attendance",
	"CC Daily Site Log",
	"CC Equipment Control",
	"CC Evidence",
	"CC Generated Report",
	"CC Notification Log",
	"CC Payable Control",
	"CC Procurement Request",
	"CC Progress Update",
	"CC Project Profile",
	"CC Safety Incident",
	"CC Tool Loan",
	"CC Weekly Closing",
)

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
		"validate": "erpnext.construcontrol.inventory.validate_material_ledger",
		"on_trash": "erpnext.construcontrol.inventory.protect_material_delete",
	},
	"CC Inventory Movement": {
		"validate": "erpnext.construcontrol.inventory.validate_inventory_movement",
		"on_update": "erpnext.construcontrol.inventory.update_inventory_relations",
		"on_trash": "erpnext.construcontrol.inventory.remove_inventory_relations",
	},
	"CC Procurement Request": {
		"validate": "erpnext.construcontrol.inventory.validate_procurement_request",
	},
	"CC Progress Update": {
		"validate": "erpnext.construcontrol.quality.validate_progress_update",
		"on_update": "erpnext.construcontrol.quality.update_progress_relations",
		"on_trash": "erpnext.construcontrol.quality.remove_progress_relations",
	},
	"CC Evidence": {
		"validate": "erpnext.construcontrol.quality.validate_evidence",
		"on_update": "erpnext.construcontrol.quality.update_evidence_relations",
		"on_trash": "erpnext.construcontrol.quality.protect_evidence_delete",
	},
	"CC Financial Institution": {
		"on_trash": "erpnext.construcontrol.finance.protect_financial_institution_delete",
	},
}
for _doctype in _PROJECT_SCOPED_DOCTYPES:
	_events = _cc_doc_events.setdefault(_doctype, {})
	_existing_validate = _events.get("validate")
	if not _existing_validate:
		_events["validate"] = _PROJECT_ACCESS_HANDLER
	elif isinstance(_existing_validate, list | tuple):
		_events["validate"] = (
			[_PROJECT_ACCESS_HANDLER, *_existing_validate]
			if _PROJECT_ACCESS_HANDLER not in _existing_validate
			else list(_existing_validate)
		)
	elif _existing_validate != _PROJECT_ACCESS_HANDLER:
		_events["validate"] = [_PROJECT_ACCESS_HANDLER, _existing_validate]


doc_events = {key: dict(value) for key, value in doc_events.items()}
doc_events.update(_cc_doc_events)

_global_events = dict(doc_events.get("*", {}))
for _event in ("after_insert", "on_update", "on_submit", "on_cancel", "on_trash"):
	_handler = "erpnext.construcontrol.audit.record_event"
	_existing = _global_events.get(_event)
	if not _existing:
		_global_events[_event] = _handler
	elif isinstance(_existing, list | tuple):
		_global_events[_event] = [*_existing, _handler] if _handler not in _existing else list(_existing)
	elif _existing != _handler:
		_global_events[_event] = [_existing, _handler]
doc_events["*"] = _global_events

_cc_migrate_handlers = (
	"erpnext.construcontrol.inventory.ensure_inventory_schema",
	"erpnext.construcontrol.quality.ensure_quality_schema",
	"erpnext.construcontrol.quality_migration.backfill_quality_metadata",
)
if "after_migrate" not in globals():
	after_migrate = []
elif isinstance(after_migrate, str):
	after_migrate = [after_migrate]
else:
	after_migrate = list(after_migrate or [])
for _migrate_handler in _cc_migrate_handlers:
	if _migrate_handler not in after_migrate:
		after_migrate.append(_migrate_handler)

if isinstance(app_include_css, str):
	app_include_css = [app_include_css]
else:
	app_include_css = list(app_include_css or [])
app_include_css.extend(
	[
		"/assets/erpnext/css/construcontrol_canonical.css",
		"/assets/erpnext/css/construcontrol_finance.css",
		"/assets/erpnext/css/construcontrol_expenses.css",
		"/assets/erpnext/css/construcontrol_ux.css",
	]
)

if isinstance(app_include_js, str):
	app_include_js = [app_include_js]
else:
	app_include_js = list(app_include_js or [])
app_include_js.extend(
	[
		"/assets/erpnext/js/construcontrol_mobile.js",
		"/assets/erpnext/js/construcontrol_finance.js",
		"/assets/erpnext/js/construcontrol_expenses.js",
		"/assets/erpnext/js/construcontrol_ux.js",
	]
)
