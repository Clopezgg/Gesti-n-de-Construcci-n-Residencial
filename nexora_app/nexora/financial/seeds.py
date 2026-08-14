from __future__ import annotations

import base64
import json
from typing import Any

import frappe
from frappe import _
from frappe.utils.file_manager import save_file

from nexora.financial.catalog import category_rows, operation_rows

DEMO_PROJECT = "NEXORA 0.1 — Fondo demostrativo"
DEMO_TARGET_PROJECT = "NEXORA 0.1 — Proyecto destino"
DEMO_OPERATION_DATE = "2026-07-23"
DEMO_DUE_DATE = "2026-08-22"
DEMO_DASHBOARD_EVIDENCE_KEY = "nexora-staging-01-dashboard-evidence"
DEMO_DASHBOARD_PROGRESS_KEY = "nexora-staging-01-dashboard-progress"
DEMO_DASHBOARD_BUDGET_KEY = "nexora-staging-01-dashboard-budget"
DEMO_DASHBOARD_COMMITMENT_KEY = "nexora-staging-01-dashboard-commitment"
DEMO_ENTITY_KEY = "nexora-staging-01-entity-supplier"
DEMO_ENTITY_NAME = "Constructora demostrativa NEXORA"
DEMO_ENTITY_LEGAL_NAME = "Constructora Demostrativa NEXORA, S. de R. L."
DEMO_PNG = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
DEMO_USERS = {
	"requester": ("nexora.operator@example.test", "Operador NEXORA", "NEXORA Finance Operator"),
	"approver": ("nexora.manager@example.test", "Aprobador NEXORA", "NEXORA Finance Manager"),
	"responsible": ("nexora.viewer@example.test", "Responsable NEXORA", "NEXORA Project Viewer"),
}
DEMO_REQUIRED_ROLES = (
	"NEXORA Administrator",
	"NEXORA Finance Manager",
	"NEXORA Finance Operator",
	"NEXORA Auditor",
	"NEXORA Project Viewer",
)


def _upsert(doctype: str, code: str, values: dict[str, object]) -> None:
	if frappe.db.exists(doctype, code):
		frappe.db.set_value(doctype, code, values, update_modified=False)
	else:
		frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)


def seed_analytic_catalogs() -> None:
	for row in category_rows():
		values = dict(row)
		label = values.pop("label")
		code = str(values["code"])
		_upsert(
			"NXR Economic Category",
			code,
			{**values, "category_name": label, "active": 1, "system_managed": 1},
		)
	for row in operation_rows():
		values = dict(row)
		label = values.pop("label")
		code = str(values["code"])
		_upsert(
			"NXR Operation Type",
			code,
			{**values, "operation_name": label, "active": 1, "system_managed": 1},
		)


def _require_staging_site() -> None:
	if not bool(frappe.conf.get("nexora_staging")):
		frappe.throw(
			_("La carga demostrativa exige nexora_staging=1 en la configuración del sitio."),
			title=_("Sitio no autorizado para demostración"),
		)


def _ensure_demo_user(email: str, full_name: str, role: str) -> str:
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


def _ensure_demo_project(project_name: str) -> str:
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
		)
		.insert(ignore_permissions=True)
		.name
	)


def _ensure_demo_entity() -> str:
	"""El gasto diario (código 102) exige beneficiario y el campo enlaza a NXR Entity.

	Sin una entidad sembrada, un sitio de staging recién instalado no puede
	registrar un solo gasto: el usuario abre «Registrar gasto» y encuentra un
	campo obligatorio sin ninguna opción. La entidad se deja en «Active» porque
	ese es el estado con el que un proveedor real opera, y por eso llega con
	contactos: `NXR Entity.validate` exige identificador, contacto o usuario
	vinculado para activarla, y un proveedor sin forma de contacto no es un
	proveedor.
	"""
	from nexora.directory.service import create_entity, transition_entity

	entity = create_entity(
		{
			"idempotency_key": DEMO_ENTITY_KEY,
			"entity_type": "Organization",
			"display_name": DEMO_ENTITY_NAME,
			"legal_name": DEMO_ENTITY_LEGAL_NAME,
			"notes": "Proveedor demostrativo NEXORA 0.1 para el flujo de gasto diario.",
			"contacts": [
				{
					"contact_type": "Email",
					"contact_value": "contacto.constructora@example.test",
					"is_primary": 1,
				},
				{"contact_type": "Phone", "contact_value": "+504 2200 0000"},
			],
		}
	)["name"]
	if frappe.db.get_value("NXR Entity", entity, "status") == "Draft":
		transition_entity(entity, "Active", f"{DEMO_ENTITY_KEY}-active")
	return str(entity)


def _demo_source_payload(
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


def _seed_dashboard_records(
	*,
	project: str,
	source: str,
	requester: str,
	approver: str,
	responsible: str,
) -> dict[str, Any]:
	from nexora.budget.service import activate_budget, create_budget
	from nexora.financial.commitments import create_commitment
	from nexora.financial.evidence import register_evidence, review_evidence
	from nexora.progress.service import create_progress_record, transition_progress_record

	budget_name = frappe.db.get_value(
		"NXR Budget",
		{"idempotency_key": DEMO_DASHBOARD_BUDGET_KEY},
		"name",
	)
	if not budget_name:
		budget_name = create_budget(
			{
				"idempotency_key": DEMO_DASHBOARD_BUDGET_KEY,
				"project": project,
				"title": "Presupuesto demostrativo de obra",
				"effective_date": DEMO_OPERATION_DATE,
				"lines": [
					{
						"economic_category": "CONSTRUCTION_MATERIALS",
						"description": "Materiales de construcción",
						"approved_hnl": 60_000,
					},
					{
						"economic_category": "ADVANCE",
						"description": "Anticipos operativos",
						"approved_hnl": 30_000,
					},
					{
						"economic_category": "TRAVEL",
						"description": "Movilidad y logística",
						"approved_hnl": 20_000,
					},
				],
			}
		)["budget"]
	if frappe.db.get_value("NXR Budget", budget_name, "status") == "Draft":
		activate_budget({"budget": budget_name})

	commitment = create_commitment(
		{
			"idempotency_key": DEMO_DASHBOARD_COMMITMENT_KEY,
			"project": project,
			"amount_hnl": 5_000,
			"allocations": [{"source": source, "amount_hnl": 5_000}],
			"economic_category": "CONSTRUCTION_MATERIALS",
			"affects_budget": 1,
			"requester": requester,
			"approved_by": approver,
			"description": "Compra demostrativa pendiente",
			"expiry_date": DEMO_DUE_DATE,
		}
	)

	evidence_name = frappe.db.get_value(
		"NXR Evidence",
		{"idempotency_key": DEMO_DASHBOARD_EVIDENCE_KEY},
		"name",
	)
	if not evidence_name:
		file_doc = save_file(
			"nexora-avance-demostrativo.png",
			DEMO_PNG,
			None,
			None,
			is_private=1,
		)
		evidence_name = register_evidence(
			{
				"project": project,
				"evidence_kind": "Other",
				"channel": "Other",
				"file_url": file_doc.file_url,
				"external_reference": "NEXORA-DEMO-AVANCE",
				"notes": "Fotografía demostrativa para validación visual del dashboard.",
				"idempotency_key": DEMO_DASHBOARD_EVIDENCE_KEY,
			}
		)["evidence"]
	if frappe.db.get_value("NXR Evidence", evidence_name, "status") == "Uploaded":
		review_evidence(
			str(evidence_name),
			"Validated",
			f"{DEMO_DASHBOARD_EVIDENCE_KEY}:review",
			"Evidencia demostrativa validada.",
		)
	evidence_url = frappe.db.get_value("NXR Evidence", evidence_name, "file_url")

	progress_name = frappe.db.get_value(
		"NXR Progress Record",
		{"idempotency_key": DEMO_DASHBOARD_PROGRESS_KEY},
		"name",
	)
	if not progress_name:
		progress_name = create_progress_record(
			{
				"project": project,
				"phase": "Preparación del terreno",
				"description": "Nivelación, compactación y organización inicial completadas.",
				"progress_percent": 42,
				"recorded_date": DEMO_OPERATION_DATE,
				"responsible": responsible,
				"photos": json.dumps([evidence_url]),
				"notes": "Dato demostrativo, no histórico.",
				"idempotency_key": DEMO_DASHBOARD_PROGRESS_KEY,
			}
		)["name"]
	if frappe.db.get_value("NXR Progress Record", progress_name, "status") == "Draft":
		transition_progress_record({"record": progress_name, "target_status": "Submitted"})
	if frappe.db.get_value("NXR Progress Record", progress_name, "status") == "Submitted":
		transition_progress_record({"record": progress_name, "target_status": "Approved"})
	return {
		"budget": budget_name,
		"commitment": commitment["commitment"],
		"evidence": evidence_name,
		"progress": progress_name,
	}


def seed_demo_data() -> dict[str, Any]:
	"""Create idempotent, non-historical data only on an explicitly marked staging site."""
	from nexora.financial.analytics import execute_central_operation
	from nexora.financial.sources import create_fund_source

	_require_staging_site()
	if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Solo un administrador puede cargar datos demostrativos."), frappe.PermissionError)
	seed_analytic_catalogs()
	users = {
		name: _ensure_demo_user(email, full_name, role)
		for name, (email, full_name, role) in DEMO_USERS.items()
	}
	project = _ensure_demo_project(DEMO_PROJECT)
	target_project = _ensure_demo_project(DEMO_TARGET_PROJECT)
	beneficiary = _ensure_demo_entity()
	primary = create_fund_source(
		_demo_source_payload(
			key="nexora-staging-01-source-primary",
			source_name="Remesa demostrativa A",
			project=project,
			amount_hnl=100_000,
			custodian=users["requester"],
		)
	)
	secondary = create_fund_source(
		_demo_source_payload(
			key="nexora-staging-01-source-secondary",
			source_name="Remesa demostrativa B",
			project=project,
			amount_hnl=60_000,
			custodian=users["requester"],
		)
	)
	destination = create_fund_source(
		_demo_source_payload(
			key="nexora-staging-01-source-destination",
			source_name="Fuente demostrativa destino",
			project=target_project,
			amount_hnl=10_000,
			custodian=users["requester"],
		)
	)
	savings = execute_central_operation(
		{
			"idempotency_key": "nexora-staging-01-savings-single-source",
			"operation_code": "MAXIMUM_ACCOUNT",
			"economic_category": "MAXIMUM_ACCOUNT",
			"project": project,
			"amount_hnl": 25_000,
			# Un gasto debita una sola fuente (Bloque 38): esta demostración usaba dos
			# a propósito antes de esa regla; ahora sale completa de `primary`, que
			# tiene disponible de sobra (100,000) para esto más el anticipo de abajo.
			"allocations": [{"source": primary["fund_source"], "amount_hnl": 25_000}],
			"requester": users["requester"],
			"approved_by": users["approver"],
			"description": "Salida demostrativa a Cuenta Máxima",
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
			"operation_date": DEMO_OPERATION_DATE,
			"due_date": DEMO_DUE_DATE,
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
	dashboard = _seed_dashboard_records(
		project=project,
		source=primary["fund_source"],
		requester=users["requester"],
		approver=users["approver"],
		responsible=users["responsible"],
	)
	health = staging_health(project)
	if not health["ok"]:
		frappe.throw(_("La verificación previa al cierre falló: {0}").format(health["checks"]))
	return {
		"project": project,
		"target_project": target_project,
		"beneficiary": beneficiary,
		"sources": [primary["fund_source"], secondary["fund_source"], destination["fund_source"]],
		"operations": [savings["operation"], advance["operation"], transfer["operation"]],
		"dashboard": dashboard,
		"health": health,
	}


def staging_health(project: str | None = None) -> dict[str, Any]:
	"""Return reproducible installation, catalog, workspace, balance and audit evidence."""
	from nexora.dashboard.service import get_dashboard_summary
	from nexora.financial.sources import list_source_balances

	project = project or frappe.db.get_value("Project", {"project_name": DEMO_PROJECT}, "name")
	required_doctypes = (
		"NXR Fund Source",
		"NXR Operation",
		"NXR Operation Effect",
		"NXR Fund Allocation",
		"NXR Audit Event",
		"NXR Idempotency Record",
	)
	operation_count = frappe.db.count("NXR Operation", {"project": project}) if project else 0
	audit_count = (
		frappe.db.count(
			"NXR Audit Event", {"reference_doctype": ["in", ["NXR Fund Source", "NXR Operation"]]}
		)
		if project
		else 0
	)
	checks = {
		"app_installed": "nexora" in frappe.get_installed_apps(),
		"erpnext_installed": "erpnext" in frappe.get_installed_apps(),
		"doctypes": all(frappe.db.exists("DocType", doctype) for doctype in required_doctypes),
		"roles": all(frappe.db.exists("Role", role) for role in DEMO_REQUIRED_ROLES),
		"workspace": bool(frappe.db.exists("Workspace", "NEXORA")),
		"page": bool(frappe.db.exists("Page", "nexora-finance")),
		"operation_catalog": frappe.db.count("NXR Operation Type", {"active": 1}) >= 1,
		"economic_catalog": frappe.db.count("NXR Economic Category", {"active": 1}) >= 1,
		"demo_operations": operation_count >= 3 if project else False,
		"audit": audit_count >= 3 if project else False,
	}
	balances = list_source_balances(str(project)) if project else []
	checks["demo_sources"] = len(balances) >= 2
	dashboard = get_dashboard_summary({"project": project}) if project else {}
	checks.update(
		{
			"dashboard_balance": bool(dashboard.get("finance", {}).get("source_count")),
			"dashboard_budget": bool(dashboard.get("budgets", {}).get("active_budget_count")),
			"dashboard_accounts": bool(dashboard.get("pending_accounts", {}).get("count")),
			"dashboard_progress": bool(dashboard.get("progress", {}).get("physical_percent")),
			"dashboard_evidence": bool(dashboard.get("evidence", {}).get("count")),
		}
	)
	return {
		"ok": all(checks.values()),
		"checks": checks,
		"project": project,
		"balances": balances,
		"dashboard": dashboard,
		"operation_count": operation_count,
		"audit_count": audit_count,
	}


def assert_staging_health() -> dict[str, Any]:
	result = staging_health()
	if not result["ok"]:
		frappe.throw(_("La verificación de staging NEXORA falló: {0}").format(result["checks"]))
	return result
