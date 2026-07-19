from __future__ import annotations

import json
import uuid
from collections import Counter
from pathlib import Path

import frappe
from frappe.utils import cint, today

from erpnext.construcontrol.access import assert_project_access, project_filter
from erpnext.construcontrol.migration.runtime_contract import (
	load_runtime_contract,
	validate_runtime_contract_or_raise,
)
from erpnext.construcontrol.tests.test_runtime_user_context import runtime_user
from erpnext.construcontrol.users import (
	approve_user,
	delete_user,
	get_user_center,
	save_user,
	set_user_enabled,
)
from erpnext.construcontrol.weekly import create_weekly_closing

_REQUIRED_PAGES = (
	"construcontrol-dashboard",
	"construcontrol-profile",
	"construcontrol-project-center",
	"construcontrol-users",
	"construcontrol-integrations",
	"construcontrol-reporting-center",
	"construcontrol-weekly-closing",
	"construcontrol-migration-console",
)

_REQUIRED_DOCTYPES = (
	"CC Funding Source",
	"CC Expense Control",
	"CC Payable Control",
	"CC Construction Phase",
	"CC Labor Contract",
	"CC Material Ledger",
	"CC Inventory Movement",
	"CC Progress Update",
	"CC Weekly Closing",
	"CC Audit Log",
	"CC Financial Institution",
	"CC Integration Registry",
)


def _assert(condition: bool, message: str) -> None:
	if not condition:
		raise AssertionError(message)


def _ensure_test_company(marker: str) -> str:
	if not frappe.db.exists("Warehouse Type", "Transit"):
		frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)

	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		company = frappe.db.get_value("Company", {}, "name")
	if company:
		return str(company)

	document = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": f"ConstruControl CI {marker}",
			"abbr": "CCI",
			"default_currency": "HNL",
			"country": "Honduras",
		}
	).insert(ignore_permissions=True)
	return str(document.name)


def _verify_schema_metadata() -> dict[str, object]:
	runtime_dir = Path(__file__).resolve().parents[1] / "runtime"
	contract = load_runtime_contract(runtime_dir)
	doctypes = sorted(
		str(row.get("name") or "").strip()
		for row in contract["definitions"]
		if str(row.get("name") or "").strip()
	)
	collisions: dict[str, list[str]] = {}
	duplicate_custom_fields: dict[str, list[str]] = {}
	custom_field_count = 0

	for doctype in doctypes:
		standard_fields = {
			str(fieldname)
			for fieldname in frappe.get_all("DocField", filters={"parent": doctype}, pluck="fieldname")
			if fieldname
		}
		custom_names = [
			str(fieldname)
			for fieldname in frappe.get_all("Custom Field", filters={"dt": doctype}, pluck="fieldname")
			if fieldname
		]
		custom_field_count += len(custom_names)
		overlap = sorted(standard_fields.intersection(custom_names))
		if overlap:
			collisions[doctype] = overlap
		duplicates = sorted(name for name, count in Counter(custom_names).items() if count > 1)
		if duplicates:
			duplicate_custom_fields[doctype] = duplicates

	_assert(not collisions, f"DocField/Custom Field collisions detected: {collisions}")
	_assert(
		not duplicate_custom_fields,
		f"Duplicate Custom Field metadata detected: {duplicate_custom_fields}",
	)
	report = validate_runtime_contract_or_raise(runtime_dir)
	recorded_sha = str(frappe.db.get_single_value("ConstruControl Settings", "runtime_contract_sha256") or "")
	_assert(recorded_sha == report["sha256"], "Recorded runtime contract SHA does not match filesystem")
	return {
		"doctypes": len(doctypes),
		"custom_fields": custom_field_count,
		"collisions": 0,
		"duplicate_custom_fields": 0,
		"contract_recorded": True,
	}


def _verify_project_permissions(marker: str, allowed_project: str, company: str) -> int:
	denied_project = frappe.get_doc(
		{
			"doctype": "Project",
			"project_name": f"ConstruControl CI denied {marker}",
			"status": "Open",
			"is_active": "Yes",
			"company": company,
		}
	).insert(ignore_permissions=True)
	user = f"cc-ci-{marker}@example.com"
	frappe.get_doc(
		{
			"doctype": "User",
			"email": user,
			"first_name": "ConstruControl CI Viewer",
			"user_type": "System User",
			"send_welcome_email": 0,
			"roles": [{"role": "ConstruControl Viewer"}],
		}
	).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": "Project",
			"for_value": allowed_project,
			"apply_to_all_doctypes": 1,
			"is_default": 1,
		}
	).insert(ignore_permissions=True)

	with runtime_user(user):
		_assert(assert_project_access(allowed_project) == allowed_project, "Assigned project was denied")
		_assert(
			project_filter() == {"project": ["in", [allowed_project]]},
			"Project filter escaped assigned scope",
		)
		denied = 0
		try:
			assert_project_access(denied_project.name)
		except (frappe.PermissionError, frappe.ValidationError):
			denied = 1
		_assert(denied == 1, "Viewer accessed an unassigned project")
		denied_write = 0
		try:
			assert_project_access(allowed_project, write=True)
		except (frappe.PermissionError, frappe.ValidationError):
			denied_write = 1
		_assert(denied_write == 1, "Viewer executed a write-scoped project operation")
	return denied + denied_write


def _expect_permission_denied(callback, message: str) -> int:
	try:
		callback()
	except (frappe.PermissionError, frappe.ValidationError):
		return 1
	raise AssertionError(message)


def _verify_user_authorization(marker: str, allowed_project: str, company: str) -> dict[str, object]:
	denied_project = frappe.get_doc(
		{
			"doctype": "Project",
			"project_name": f"ConstruControl US01 denied {marker}",
			"status": "Open",
			"is_active": "Yes",
			"company": company,
		}
	).insert(ignore_permissions=True)
	manager = f"cc-manager-{marker}@example.com"
	frappe.get_doc(
		{
			"doctype": "User",
			"email": manager,
			"first_name": "ConstruControl Manager CI",
			"user_type": "System User",
			"send_welcome_email": 0,
			"roles": [{"role": "ConstruControl Manager"}],
		}
	).insert(ignore_permissions=True)

	limited = {
		"OPERATOR": f"cc-operator-{marker}@example.com",
		"AUDITOR": f"cc-auditor-{marker}@example.com",
		"VIEWER": f"cc-viewer-{marker}@example.com",
	}
	for label, email in limited.items():
		save_user(
			email=email,
			first_name=f"ConstruControl {label} CI",
			role=label,
			project=allowed_project,
			enabled=1,
		)

	denials = 0
	for label, email in limited.items():
		with runtime_user(email):
			_assert(
				assert_project_access(allowed_project) == allowed_project,
				f"{label} lost assigned project",
			)
			denials += _expect_permission_denied(
				lambda: assert_project_access(denied_project.name),
				f"{label} accessed an unassigned project",
			)
			if label == "OPERATOR":
				_assert(
					assert_project_access(allowed_project, write=True) == allowed_project,
					"OPERATOR lost write access to assigned project",
				)
			else:
				denials += _expect_permission_denied(
					lambda: assert_project_access(allowed_project, write=True),
					f"{label} executed a write operation",
				)
			denials += _expect_permission_denied(
				lambda: get_user_center(),
				f"{label} accessed the user administration endpoint",
			)

	with runtime_user(manager):
		center = get_user_center()
		_assert(bool(center.get("users")), "MANAGER could not read the user center")
		pending = f"cc-pending-{marker}@example.com"
		save_user(
			email=pending,
			first_name="ConstruControl Pending CI",
			role="VIEWER",
			project=allowed_project,
			enabled=0,
		)
		approve_user(pending)
		_assert(cint(frappe.db.get_value("User", pending, "enabled")) == 1, "MANAGER could not approve user")
		save_user(
			email=pending,
			first_name="ConstruControl Edited CI",
			role="VIEWER",
			project=allowed_project,
			enabled=1,
		)
		denials += _expect_permission_denied(
			lambda: save_user(
				email="cc-admin-attempt@example.com",
				first_name="Unauthorized Admin",
				role="ADMIN",
				enabled=1,
			),
			"MANAGER assigned ADMIN",
		)
		denials += _expect_permission_denied(
			lambda: set_user_enabled("Administrator", 0),
			"MANAGER suspended Administrator",
		)
		denials += _expect_permission_denied(
			lambda: delete_user(pending, reason="unauthorized manager deletion"),
			"MANAGER deleted a user",
		)
	with runtime_user("Administrator"):
		denials += _expect_permission_denied(
			lambda: set_user_enabled("Administrator", 0),
			"Administrator account was suspended",
		)
		delete_user(pending, reason="US01 runtime deletion test")
		_assert(not frappe.db.exists("User", pending), "System Manager deletion did not remove the test user")

	page = frappe.get_doc("Page", "construcontrol-users")
	page_roles = {str(row.role) for row in page.roles}
	_assert(
		page_roles == {"System Manager", "ConstruControl Manager"},
		"Direct users page access roles are not restricted to management",
	)

	audit_rows = frappe.get_all(
		"CC Audit Log",
		filters={"record_type": "User", "record_id": ["like", f"%{marker}%"]},
		fields=["action", "actor_role", "actor_user_id"],
	)
	actions = {str(row.get("action")) for row in audit_rows}
	_assert({"CREATE", "UPDATE", "APPROVE", "DELETE"}.issubset(actions), "US01 audit actions are incomplete")
	_assert(
		all(row.get("actor_role") and row.get("actor_user_id") for row in audit_rows),
		"US01 audit identity is incomplete",
	)
	return {
		"roles_tested": 5,
		"permission_denials": denials,
		"audit_actions": sorted(actions),
		"direct_page_roles": sorted(page_roles),
	}


def run() -> dict[str, object]:
	"""Execute real CRUD, authorization and accounting relations in one rolled-back transaction."""
	marker = uuid.uuid4().hex[:12]
	with runtime_user("Administrator"):
		try:
			for page in _REQUIRED_PAGES:
				_assert(bool(frappe.db.exists("Page", page)), f"Missing runtime page: {page}")
			for doctype in _REQUIRED_DOCTYPES:
				_assert(bool(frappe.db.exists("DocType", doctype)), f"Missing runtime DocType: {doctype}")

			schema_metadata = _verify_schema_metadata()
			company = _ensure_test_company(marker)
			project = frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": f"ConstruControl CI {marker}",
					"status": "Open",
					"is_active": "Yes",
					"company": company,
				}
			).insert(ignore_permissions=True)

			fund = frappe.get_doc(
				{
					"doctype": "CC Funding Source",
					"project": project.name,
					"title": f"Ingreso CI {marker}",
					"income_type": "personal",
					"status": "received",
					"date_received": today(),
					"currency": "HNL",
					"original_amount": 1000,
					"exchange_rate": 1,
					"amount_hnl": 1000,
					"transaction_channel": "cash",
					"financial_institution": "CASH",
					"gross_amount": 1000,
					"fee_amount": 0,
					"original_currency": "HNL",
					"treasury_exchange_rate": 1,
					"reconciliation_status": "verified",
				}
			).insert(ignore_permissions=True)
			_assert(float(fund.net_amount_hnl or 0) == 1000.0, "FI01 net amount was not calculated")

			expense = frappe.get_doc(
				{
					"doctype": "CC Expense Control",
					"project": project.name,
					"title": f"Gasto CI {marker}",
					"posting_date": today(),
					"category": "service",
					"provider_name": "Proveedor CI",
					"amount_hnl": 250,
					"subtotal_hnl": 250,
					"funding_source": fund.name,
					"professional_approval_status": "approved",
					"payment_status": "paid",
					"paid_amount_hnl": 250,
					"payment_reference": f"CI-PAY-{marker}",
				}
			).insert(ignore_permissions=True)
			_assert(float(expense.calculated_total_hnl or 0) == 250.0, "FI02 total was not calculated")
			_assert(float(expense.balance_due_hnl or 0) == 0.0, "FI02 paid balance is inconsistent")

			payable = frappe.db.get_value(
				"CC Payable Control",
				{"source_key": f"expense-payable:{expense.name}"},
				["name", "payable_status", "balance_due_hnl"],
				as_dict=True,
			)
			_assert(bool(payable), "FI03 payable was not synchronized")
			_assert(payable.payable_status == "paid", "FI03 payable status is inconsistent")
			_assert(float(payable.balance_due_hnl or 0) == 0.0, "FI03 balance is inconsistent")

			fund.reload()
			_assert(float(fund.spent_hnl or 0) == 250.0, "FI01 spent balance was not reconciled")
			_assert(float(fund.available_hnl or 0) == 750.0, "FI01 available balance was not reconciled")

			closing = create_weekly_closing(
				week_start=today(),
				week_end=today(),
				project=project.name,
				status="closed",
			)
			snapshot = closing["snapshot"]
			_assert(float(snapshot["income_hnl"]) == 1000.0, "CL01 income snapshot is inconsistent")
			_assert(float(snapshot["expense_hnl"]) == 250.0, "CL01 paid expense snapshot is inconsistent")
			_assert(float(snapshot["final_balance_hnl"]) == 750.0, "CL01 final balance is inconsistent")

			permission_denials = _verify_project_permissions(marker, project.name, company)
			user_security = _verify_user_authorization(marker, project.name, company)

			result = {
				"ok": True,
				"pages": len(_REQUIRED_PAGES),
				"doctypes": len(_REQUIRED_DOCTYPES),
				"funding_net_hnl": float(fund.net_amount_hnl or 0),
				"spent_hnl": float(fund.spent_hnl or 0),
				"available_hnl": float(fund.available_hnl or 0),
				"expense_total_hnl": float(expense.calculated_total_hnl or 0),
				"payable_status": payable.payable_status,
				"weekly_balance_hnl": float(snapshot["final_balance_hnl"]),
				"permission_denials": permission_denials,
				"schema_metadata": schema_metadata,
				"user_security": user_security,
			}
			print(json.dumps(result, ensure_ascii=False, sort_keys=True))
			return result
		finally:
			frappe.db.rollback()


def create_persistence_marker(marker: str = "") -> str:
	with runtime_user("Administrator"):
		marker = str(marker or "").strip() or f"CONSTRUCONTROL-CI-{uuid.uuid4().hex}"
		existing = frappe.get_all("ToDo", filters={"description": marker}, pluck="name")
		for name in existing:
			frappe.delete_doc("ToDo", name, ignore_permissions=True, force=True)
		frappe.get_doc({"doctype": "ToDo", "description": marker, "status": "Open"}).insert(
			ignore_permissions=True
		)
		frappe.db.commit()
		print(marker)
		return marker


def verify_and_cleanup_persistence_marker(marker: str) -> dict[str, object]:
	with runtime_user("Administrator"):
		marker = str(marker or "").strip()
		name = frappe.db.get_value("ToDo", {"description": marker}, "name")
		_assert(bool(name), "Persistence marker disappeared after container restart")
		frappe.delete_doc("ToDo", name, ignore_permissions=True, force=True)
		frappe.db.commit()
		result = {"ok": True, "marker": marker, "persisted": True, "cleaned": True}
		print(json.dumps(result, sort_keys=True))
		return result
