from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from nexora.financial.analytics import execute_central_operation
from nexora.financial.seeds import seed_analytic_catalogs
from nexora.financial.sources import create_fund_source, list_source_balances
from nexora.install import BASE_ROLES

DEMO_PROJECT = "NEXORA 0.1 — Fondo demostrativo"
DEMO_TARGET_PROJECT = "NEXORA 0.1 — Proyecto destino"
DEMO_USERS = {
	"requester": ("nexora.operator@example.test", "Operador NEXORA", "NEXORA Finance Operator"),
	"approver": ("nexora.manager@example.test", "Aprobador NEXORA", "NEXORA Finance Manager"),
	"responsible": ("nexora.viewer@example.test", "Responsable NEXORA", "NEXORA Project Viewer"),
}


def _require_staging_site() -> None:
	if not bool(frappe.conf.get("nexora_staging")):
		frappe.throw(
			_("La carga demostrativa exige nexora_staging=1 en la configuración del sitio."),
			title=_("Sitio no autorizado para demostración"),
		)


def _ensure_user(email: str, full_name: str, role: str) -> str:
	first_name, _, last_name = full_name.partition(" ")
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": last_name,
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	elif not frappe.db.exists("Has Role", {"parent": email, "role": role}):
		user = frappe.get_doc("User", email)
		user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
	return email


def _ensure_project(project_name: str) -> str:
	existing = frappe.db.get_value("Project", {"project_name": project_name}, "name")
	if existing:
		return str(existing)
	return str(
		frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": project_name,
				"status": "Open",
			}
		).insert(ignore_permissions=True).name
	)


def _source_payload(
	*, key: str, source_name: str, project: str, amount_hnl: int, custodian: str
) -> dict[str, Any]:
	return {
		"idempotency_key": key,
		"source_name": source_name,
		"channel": "Cash",
		"project": project,
		"currency": "HNL",
		"original_amount": amount_hnl,
		"exchange_rate": 1,
		"origin_or_sender": "Datos demostrativos NEXORA 0.1",
		"custodian": custodian,
	}


def seed_demo_data() -> dict[str, Any]:
	"""Create a small, idempotent and clearly non-historical staging dataset."""
	_require_staging_site()
	previous_user = frappe.session.user
	frappe.set_user("Administrator")
	try:
		seed_analytic_catalogs()
		users = {
			name: _ensure_user(email, full_name, role)
			for name, (email, full_name, role) in DEMO_USERS.items()
		}
		project = _ensure_project(DEMO_PROJECT)
		target_project = _ensure_project(DEMO_TARGET_PROJECT)
		primary = create_fund_source(
			_source_payload(
				key="nexora-staging-01-source-primary",
				source_name="Remesa demostrativa A",
				project=project,
				amount_hnl=100_000,
				custodian=users["requester"],
			)
		)
		secondary = create_fund_source(
			_source_payload(
				key="nexora-staging-01-source-secondary",
				source_name="Remesa demostrativa B",
				project=project,
				amount_hnl=60_000,
				custodian=users["requester"],
			)
		)
		destination = create_fund_source(
			_source_payload(
				key="nexora-staging-01-source-destination",
				source_name="Fuente demostrativa destino",
				project=target_project,
				amount_hnl=10_000,
				custodian=users["requester"],
			)
		)
		savings = execute_central_operation(
			{
				"idempotency_key": "nexora-staging-01-savings-multisource",
				"operation_code": "MAXIMUM_ACCOUNT",
				"economic_category": "MAXIMUM_ACCOUNT",
				"project": project,
				"amount_hnl": 25_000,
				"allocations": [
					{"source": primary["fund_source"], "amount_hnl": 15_000},
					{"source": secondary["fund_source"], "amount_hnl": 10_000},
				],
				"requester": users["requester"],
				"approved_by": users["approver"],
				"description": "Salida demostrativa multifuente a Cuenta Máxima",
			}
		)
		advance = execute_central_operation(
			{
				"idempotency_key": "nexora-staging-01-advance",
				"operation_code": "ADVANCE_DISBURSEMENT",
				"economic_category": "ADVANCE",
				"project": project,
				"amount_hnl": 12_000,
				"allocations": [{"source": primary["fund_source"], "amount_hnl": 12_000}],
				"beneficiary_doctype": "User",
				"beneficiary": users["responsible"],
				"operation_date": frappe.utils.today(),
				"due_date": frappe.utils.add_days(frappe.utils.today(), 30),
				"requester": users["requester"],
				"approved_by": users["approver"],
				"description": "Anticipo demostrativo pendiente de liquidación",
			}
		)
		transfer = execute_central_operation(
			{
				"idempotency_key": "nexora-staging-01-internal-transfer",
				"operation_code": "INTERNAL_TRANSFER",
				"economic_category": "INTERNAL_TRANSFER",
				"project": project,
				"target_project": target_project,
				"destination_source": destination["fund_source"],
				"amount_hnl": 8_000,
				"allocations": [{"source": secondary["fund_source"], "amount_hnl": 8_000}],
				"requester": users["requester"],
				"approved_by": users["approver"],
				"description": "Transferencia interna demostrativa",
			}
		)
		frappe.db.commit()
		return {
			"project": project,
			"target_project": target_project,
			"sources": [primary["fund_source"], secondary["fund_source"], destination["fund_source"]],
			"operations": [savings["operation"], advance["operation"], transfer["operation"]],
			"health": staging_health(project),
		}
	finally:
		frappe.set_user(previous_user)


def staging_health(project: str | None = None) -> dict[str, Any]:
	"""Return reproducible evidence for installation, catalogs, workspace and demo balances."""
	project = project or frappe.db.get_value("Project", {"project_name": DEMO_PROJECT}, "name")
	required_doctypes = (
		"NXR Fund Source",
		"NXR Operation",
		"NXR Operation Effect",
		"NXR Fund Allocation",
		"NXR Audit Event",
		"NXR Idempotency Record",
	)
	checks = {
		"app_installed": "nexora" in frappe.get_installed_apps(),
		"erpnext_installed": "erpnext" in frappe.get_installed_apps(),
		"doctypes": all(frappe.db.exists("DocType", doctype) for doctype in required_doctypes),
		"roles": all(frappe.db.exists("Role", role) for role in BASE_ROLES),
		"workspace": bool(frappe.db.exists("Workspace", "NEXORA")),
		"page": bool(frappe.db.exists("Page", "nexora-finance")),
		"operation_catalog": frappe.db.count("NXR Operation Type", {"active": 1}) >= 1,
		"economic_catalog": frappe.db.count("NXR Economic Category", {"active": 1}) >= 1,
	}
	balances = list_source_balances(str(project)) if project else []
	checks["demo_sources"] = len(balances) >= 2 if project else True
	return {
		"ok": all(checks.values()),
		"checks": checks,
		"project": project,
		"balances": balances,
		"operation_count": frappe.db.count("NXR Operation", {"project": project}) if project else 0,
	}


def assert_staging_health() -> dict[str, Any]:
	result = staging_health()
	if not result["ok"]:
		frappe.throw(_("La verificación de staging NEXORA falló: {0}").format(result["checks"]))
	return result
