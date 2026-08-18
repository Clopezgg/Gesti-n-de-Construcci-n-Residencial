from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import frappe

from nexora.budget.service import activate_budget, create_budget
from nexora.financial.commitments import create_commitment
from nexora.financial.sources import create_fund_source

ECONOMIC_CATEGORY = "CONSTRUCTION_MATERIALS"


def _ensure_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@", 1)[0],
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	return email


def _ensure_project(project_name: str) -> str:
	existing = frappe.db.get_value("Project", {"project_name": project_name}, "name")
	if existing:
		return str(existing)
	return str(
		frappe.get_doc({"doctype": "Project", "project_name": project_name, "status": "Open"})
		.insert(ignore_permissions=True)
		.name
	)


def run() -> dict[str, object]:
	"""`reserve_budget_commitment` bloquea la línea de presupuesto con `FOR UPDATE`
	(`budget/service.py::_lock_and_read_line`) — separado del bloqueo por fuente de
	fondos que ya cubre `concurrency_probe.py`. Dos compromisos concurrentes contra
	la MISMA línea de presupuesto, financiados cada uno desde una fuente de fondos
	DISTINTA (para que el lock de fuente no sea lo que en realidad los serialice),
	prueban específicamente que el lock de línea de presupuesto es real bajo
	concurrencia genuina, no solo bajo ejecución secuencial (como en
	`test_budget_commitment_integration.py`).
	"""
	marker = uuid.uuid4().hex[:12]
	project = _ensure_project(f"_Test Budget Commitment Concurrency {marker}")
	manager = _ensure_user(f"nxr-budgetconc-manager-{marker}@example.test", "NEXORA Finance Manager")
	# El solicitante y el aprobador deben ser personas distintas (segregación de
	# funciones, Constitución Cap. 36 — `NXR Commitment.validate()` rechaza
	# `requester == approved_by`); el manager solo actúa como aprobador aquí.
	requester = _ensure_user(f"nxr-budgetconc-requester-{marker}@example.test", "NEXORA Finance Operator")
	cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
	if not cost_center:
		raise AssertionError("No leaf Cost Center found to run the probe against.")

	frappe.set_user(manager)  # nosemgrep
	budget = create_budget(
		{
			"idempotency_key": f"budgetconc-budget-{marker}",
			"project": project,
			"title": f"Presupuesto concurrencia {marker}",
			"effective_date": frappe.utils.today(),
			"lines": [
				{
					"economic_category": ECONOMIC_CATEGORY,
					"cost_center": cost_center,
					"description": "Línea de concurrencia",
					"approved_hnl": 1000,
				}
			],
		}
	)["budget"]
	activate_budget({"budget": budget})

	sources = []
	for suffix in ("a", "b"):
		sources.append(
			create_fund_source(
				{
					"idempotency_key": f"budgetconc-source-{marker}-{suffix}",
					"source_name": f"Fuente concurrencia presupuesto {marker}-{suffix}",
					"channel": "Remittance",
					"project": project,
					"currency": "HNL",
					"original_amount": 5000,
					"exchange_rate": 1,
					"origin_or_sender": "Probe concurrencia presupuesto",
					"custodian": manager,
				}
			)["fund_source"]
		)
	# Fixture data must be visible to two independent MariaDB worker connections.
	frappe.db.commit()  # nosemgrep
	site = frappe.local.site
	sites_path = frappe.local.sites_path
	barrier = threading.Barrier(2)

	def worker(index: int) -> str:
		frappe.init(site=site, sites_path=sites_path)
		frappe.connect()
		# Test-only identity switch inside an isolated worker connection.
		frappe.set_user(manager)  # nosemgrep
		try:
			barrier.wait(timeout=20)
			create_commitment(
				{
					"idempotency_key": f"budgetconc-commit-{marker}-{index}",
					"project": project,
					"amount_hnl": 700,
					"allocations": [{"source": sources[index], "amount_hnl": 700}],
					"cost_center": cost_center,
					"economic_category": ECONOMIC_CATEGORY,
					"requester": requester,
					"approved_by": manager,
					"description": "Compromiso concurrente de presupuesto",
				}
			)
			# Commit the worker transaction to prove row-lock serialization.
			frappe.db.commit()  # nosemgrep
			return "executed"
		except Exception as exc:  # noqa: BLE001 -- clasifica cualquier resultado real de la carrera
			frappe.db.rollback()
			return (
				"denied_overspend"
				if "Compromiso no permitido" in str(exc)
				else f"unexpected:{type(exc).__name__}:{exc}"
			)
		finally:
			frappe.destroy()

	with ThreadPoolExecutor(max_workers=2) as pool:
		results = sorted(pool.map(worker, (0, 1)))

	# Restore the test actor before permission-checked reads.
	frappe.set_user(manager)  # nosemgrep
	line = frappe.db.get_value(
		"NXR Budget Line",
		{"parent": budget, "cost_center": cost_center},
		["committed_hnl", "available_hnl"],
		as_dict=True,
	)
	if (
		results != ["denied_overspend", "executed"]
		or Decimal(str(line.committed_hnl)) != Decimal("700.00")
		or Decimal(str(line.available_hnl)) != Decimal("300.00")
	):
		raise AssertionError({"results": results, "line": line})
	return {"ok": True, "results": results, "line": dict(line)}
