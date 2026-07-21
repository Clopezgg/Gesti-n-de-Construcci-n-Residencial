from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import timedelta
from pathlib import Path

import frappe
from frappe.utils import cint, get_datetime, now_datetime, today
from frappe.utils.password import passlibctx
from frappe.utils.file_manager import save_file

from erpnext.construcontrol.access import assert_project_access, project_filter
from erpnext.construcontrol.admin_correction_security import (
	get_security_status,
	require_authorization_token,
)
from erpnext.construcontrol.admin_corrections import _token_key, preview_expense_correction
from erpnext.construcontrol.admin_expense_operations import execute_expense_correction
from erpnext.construcontrol.admin_supplier_corrections import (
	execute_supplier_consolidation,
	preview_supplier_consolidation,
)
from erpnext.construcontrol.admin_user_corrections import (
	execute_user_correction,
	preview_user_correction,
)
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
	"construcontrol-closing-center",
	"construcontrol-migration-console",
)

_REQUIRED_DOCTYPES = (
	"CC Project Profile",
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


def _ensure_test_project_profile(project: str, marker: str) -> str:
	existing = frappe.db.get_value(
		"CC Project Profile",
		{"project": project, "is_logically_deleted": 0},
		"name",
	)
	if existing:
		return str(existing)

	project_row = frappe.db.get_value("Project", project, ["project_name", "company"], as_dict=True) or {}
	meta = frappe.get_meta("CC Project Profile")
	candidates = {
		"project": project,
		"project_name": project_row.get("project_name") or project,
		"company": project_row.get("company"),
		"original_budget_hnl": 1000,
		"updated_budget_hnl": 1000,
		"start_date": today(),
		"planned_start_date": today(),
		"is_current": 1,
		"is_logically_deleted": 0,
		"source_key": f"runtime:project-profile:{marker}",
		"source_id": f"RUNTIME-PROFILE-{marker}",
		"payload_json": "{}",
	}
	values = {
		"doctype": "CC Project Profile",
		**{key: value for key, value in candidates.items() if value is not None and meta.has_field(key)},
	}
	for field in meta.fields:
		fieldname = str(field.fieldname or "")
		fieldtype = str(field.fieldtype or "")
		if not field.reqd or not fieldname or fieldname in values:
			continue
		if fieldtype in {"Data", "Small Text", "Text", "Long Text"}:
			values[fieldname] = "ConstruControl CI"
		elif fieldtype in {"Currency", "Float", "Int", "Percent"}:
			values[fieldname] = 0
		elif fieldtype == "Check":
			values[fieldname] = 0
		elif fieldtype == "Date":
			values[fieldname] = today()
		elif fieldtype == "Datetime":
			values[fieldname] = now_datetime()
		elif fieldtype == "Select":
			options = [row.strip() for row in str(field.options or "").splitlines() if row.strip()]
			if options:
				values[fieldname] = options[0]
		elif fieldtype == "Link":
			options = str(field.options or "").strip()
			if options == "Project":
				values[fieldname] = project
			elif options == "Company" and project_row.get("company"):
				values[fieldname] = project_row.get("company")
			elif options == "User":
				values[fieldname] = "Administrator"
			elif options and frappe.db.exists("DocType", options):
				linked = frappe.db.get_value(options, {}, "name")
				if linked:
					values[fieldname] = linked

	document = frappe.get_doc(values)
	document.flags.ignore_construcontrol_audit = True
	document.insert(ignore_permissions=True, ignore_mandatory=True)
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


def _verify_admin_corrections(marker: str, project: str, funding_source: str) -> dict[str, object]:
	"""Exercise critical Administrator corrections against the real site database."""
	group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
	_assert(bool(group), "A leaf Supplier Group is required for correction smoke tests")

	def create_supplier(label: str) -> str:
		doc = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": label,
				"supplier_group": group,
				"supplier_type": "Company",
			}
		).insert(ignore_permissions=True)
		return str(doc.name)

	evidence = save_file(
		f"admin-correction-runtime-{marker}.txt",
		b"Evidencia privada de correccion administrativa en runtime",
		"Project",
		project,
		is_private=1,
	)
	settings = frappe.get_single("ConstruControl Settings")
	pin_updated_at = now_datetime()
	for fieldname, value in {
		"correction_pin_hash": passlibctx.hash("726401"),
		"correction_access_enabled": 1,
		"correction_pin_updated_at": pin_updated_at,
		"correction_failed_attempts": 0,
		"correction_locked_until": None,
	}.items():
		if settings.meta.has_field(fieldname):
			settings.set(fieldname, value)
	settings.flags.ignore_construcontrol_audit = True
	settings.save(ignore_permissions=True)
	settings.reload()
	pin_updated_at = get_datetime(settings.correction_pin_updated_at)

	token = f"runtime-correction-{marker}"
	authorization_id = f"CCA-RUNTIME-{marker.upper()}"
	pin_revision = str(pin_updated_at)
	frappe.cache.set_value(
		_token_key(token),
		{
			"session_id": str(frappe.session.sid or ""),
			"authorization_id": authorization_id,
			"expires_at": now_datetime() + timedelta(minutes=10),
			"pin_revision": pin_revision,
		},
		expires_in_sec=600,
	)

	def expect_token_denied(candidate: str, label: str) -> None:
		denied = 0
		try:
			require_authorization_token(candidate)
		except frappe.PermissionError:
			denied = 1
		_assert(denied == 1, label)

	expired_token = f"runtime-expired-{marker}"
	frappe.cache.set_value(
		_token_key(expired_token),
		{
			"session_id": str(frappe.session.sid or ""),
			"authorization_id": f"CCA-EXPIRED-{marker.upper()}",
			"expires_at": now_datetime() - timedelta(seconds=1),
			"pin_revision": pin_revision,
		},
		expires_in_sec=600,
	)
	expect_token_denied(expired_token, "Expired correction token was accepted")

	foreign_token = f"runtime-foreign-session-{marker}"
	frappe.cache.set_value(
		_token_key(foreign_token),
		{
			"session_id": f"foreign-{marker}",
			"authorization_id": f"CCA-FOREIGN-{marker.upper()}",
			"expires_at": now_datetime() + timedelta(minutes=10),
			"pin_revision": pin_revision,
		},
		expires_in_sec=600,
	)
	expect_token_denied(foreign_token, "Foreign-session correction token was accepted")

	rotated_token = f"runtime-rotated-{marker}"
	frappe.cache.set_value(
		_token_key(rotated_token),
		{
			"session_id": str(frappe.session.sid or ""),
			"authorization_id": f"CCA-ROTATED-{marker.upper()}",
			"expires_at": now_datetime() + timedelta(minutes=10),
			"pin_revision": pin_revision,
		},
		expires_in_sec=600,
	)
	settings.correction_pin_updated_at = pin_updated_at + timedelta(seconds=1)
	settings.flags.ignore_construcontrol_audit = True
	settings.save(ignore_permissions=True)
	settings.reload()
	expect_token_denied(rotated_token, "Token survived correction PIN rotation")
	settings.correction_pin_updated_at = pin_updated_at
	settings.flags.ignore_construcontrol_audit = True
	settings.save(ignore_permissions=True)
	settings.reload()
	_assert(
		require_authorization_token(token).get("authorization_id") == authorization_id,
		"Valid correction token was rejected",
	)
	try:
		historical_supplier = create_supplier(f"Proveedor histórico {marker}")
		historical_expense = frappe.get_doc(
			{
				"doctype": "CC Expense Control",
				"source_id": f"RUNTIME-EXP-{marker}",
				"source_key": f"runtime:admin-expense:{marker}",
				"project": project,
				"title": f"Gasto histórico administrativo {marker}",
				"posting_date": today(),
				"category": "materials",
				"provider_name": frappe.db.get_value("Supplier", historical_supplier, "supplier_name"),
				"supplier": historical_supplier,
				"funding_source": funding_source,
				"subtotal_hnl": 125,
				"amount_hnl": 125,
				"paid_amount_hnl": 125,
				"payment_status": "paid",
				"professional_approval_status": "approved",
				"payment_reference": f"ADMIN-RUNTIME-{marker}",
				"payment_evidence": evidence.file_url,
			}
		).insert(ignore_permissions=True)

		blocked = 0
		normal_edit = frappe.get_doc("CC Expense Control", historical_expense.name)
		normal_edit.paid_amount_hnl = 0
		normal_edit.payment_status = "cancelled"
		try:
			normal_edit.save(ignore_permissions=True)
		except frappe.ValidationError:
			blocked = 1
		_assert(blocked == 1, "Normal editing bypassed paid historical expense protections")

		expense_args = {
			"expense_name": historical_expense.name,
			"operation": "reverse_imported_payment",
			"changes": {"paid_amount_hnl": 0, "payment_status": "cancelled"},
			"reason": "El sistema anterior marcó este gasto como pagado por error.",
			"evidence": str(evidence.file_url),
			"authorization_token": token,
		}
		preview = preview_expense_correction(**expense_args)
		expense_result = execute_expense_correction(
			**expense_args,
			preview_hash=preview["preview_hash"],
		)
		audit_filters = {
			"record_type": "CC Expense Control",
			"record_id": historical_expense.name,
			"origin": "ADMIN_CORRECTION",
			"correlation_id": authorization_id,
		}
		audit_count = frappe.db.count("CC Audit Log", audit_filters)
		repeated_expense_result = execute_expense_correction(
			**expense_args,
			preview_hash=preview["preview_hash"],
		)
		historical_expense.reload()
		_assert(float(historical_expense.paid_amount_hnl or 0) == 0.0, "Imported payment was not reversed")
		_assert(historical_expense.payment_status == "cancelled", "Expense payment status was not cancelled")
		_assert(
			historical_expense.financial_status == "cancelled", "Expense financial status was not cancelled"
		)
		_assert(historical_expense.status == "cancelled", "Expense operational status was not cancelled")
		_assert(
			historical_expense.last_admin_correction_id == authorization_id,
			"Expense correction authorization was not recorded",
		)
		_assert(
			expense_result["authorization_id"] == authorization_id,
			"Expense result lost the authorization identifier",
		)
		_assert(bool(repeated_expense_result.get("idempotent")), "Repeated correction was not idempotent")
		_assert(
			repeated_expense_result.get("operation_result") == "ALREADY_APPLIED",
			"Repeated correction did not return the durable receipt",
		)
		_assert(
			frappe.db.count("CC Audit Log", audit_filters) == audit_count,
			"Repeated correction created a duplicate audit event",
		)

		canonical = create_supplier(f"Proveedor oficial {marker}")
		duplicate = create_supplier(f"Proveedor oficial Santa Cruz {marker}")
		duplicate_expense = frappe.get_doc(
			{
				"doctype": "CC Expense Control",
				"source_id": f"RUNTIME-SUPPLIER-EXP-{marker}",
				"source_key": f"runtime:supplier-expense:{marker}",
				"project": project,
				"title": f"Gasto de proveedor duplicado {marker}",
				"posting_date": today(),
				"category": "materials",
				"provider_name": frappe.db.get_value("Supplier", duplicate, "supplier_name"),
				"supplier": duplicate,
				"funding_source": funding_source,
				"subtotal_hnl": 75,
				"amount_hnl": 75,
				"paid_amount_hnl": 75,
				"payment_status": "paid",
				"professional_approval_status": "approved",
				"payment_reference": f"SUPPLIER-RUNTIME-{marker}",
				"payment_evidence": evidence.file_url,
			}
		).insert(ignore_permissions=True)
		supplier_args = {
			"canonical_supplier": canonical,
			"duplicate_suppliers": [duplicate],
			"reason": "La migración creó dos proveedores para la misma entidad comercial.",
			"evidence": str(evidence.file_url),
			"authorization_token": token,
		}
		supplier_preview = preview_supplier_consolidation(**supplier_args)
		_assert(not supplier_preview["blocked"], "Supported supplier consolidation was blocked")
		execute_supplier_consolidation(
			**supplier_args,
			preview_hash=supplier_preview["preview_hash"],
		)
		_assert(bool(frappe.db.exists("Supplier", duplicate)), "Duplicate supplier was physically deleted")
		_assert(
			cint(frappe.db.get_value("Supplier", duplicate, "disabled")) == 1,
			"Duplicate supplier remains active",
		)
		_assert(
			frappe.db.get_value("Supplier", duplicate, "cc_merged_into") == canonical,
			"Duplicate supplier was not linked to the canonical supplier",
		)
		_assert(
			frappe.db.get_value("CC Expense Control", duplicate_expense.name, "supplier") == canonical,
			"Expense was not reassigned to the canonical supplier",
		)

		source_user = f"admin-source-{marker}@example.com"
		target_user = f"admin-target-{marker}@example.com"
		for email, first_name in ((source_user, "Origen"), (target_user, "Destino")):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": first_name,
					"enabled": 1,
					"user_type": "System User",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": source_user,
				"allow": "Project",
				"for_value": project,
				"is_default": 1,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)
		user_args = {
			"user": source_user,
			"operation": "consolidate",
			"replacement_user": target_user,
			"reason": "La cuenta origen está duplicada y debe conservarse solo como historia.",
			"authorization_token": token,
		}
		user_preview = preview_user_correction(**user_args)
		execute_user_correction(**user_args, preview_hash=user_preview["preview_hash"])
		_assert(bool(frappe.db.exists("User", source_user)), "Source user was physically deleted")
		_assert(cint(frappe.db.get_value("User", source_user, "enabled")) == 0, "Source user remains enabled")
		_assert(
			frappe.db.get_value("User", source_user, "cc_replacement_user") == target_user,
			"Source user was not linked to the replacement account",
		)
		_assert(
			bool(
				frappe.db.exists(
					"User Permission",
					{"user": target_user, "allow": "Project", "for_value": project},
				)
			),
			"Replacement user did not receive the project permission",
		)
		_assert(
			not frappe.db.exists(
				"User Permission",
				{"user": source_user, "allow": "Project", "for_value": project},
			),
			"Archived user retained active project permissions",
		)

		denied_user = f"admin-denied-{marker}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": denied_user,
				"first_name": "Sin acceso crítico",
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		denied = 0
		with runtime_user(denied_user):
			try:
				get_security_status()
			except frappe.PermissionError:
				denied = 1
		_assert(denied == 1, "A non-Administrator read critical correction security")
		return {
			"normal_paid_edit_blocked": True,
			"expense_reversed": True,
			"supplier_archived": True,
			"user_archived": True,
			"non_administrator_denied": True,
			"authorization_id": authorization_id,
		}
	finally:
		frappe.cache.delete_value(_token_key(token))
		if frappe.db.exists("File", evidence.name):
			frappe.delete_doc("File", evidence.name, ignore_permissions=True, force=True)


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
			_ensure_test_project_profile(project.name, marker)

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
					"payment_evidence": f"/private/files/CI-PAY-{marker}.txt",
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
			admin_corrections = _verify_admin_corrections(marker, project.name, fund.name)

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
				"admin_corrections": admin_corrections,
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
