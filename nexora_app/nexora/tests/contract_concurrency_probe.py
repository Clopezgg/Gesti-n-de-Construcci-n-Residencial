from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import frappe
from frappe.utils.file_manager import save_file

from nexora.contracts.service import (
	create_contract,
	create_contract_estimate,
	create_contractor_profile,
	execute_contract_estimate_payment,
	transition_contract,
	transition_contract_estimate,
	transition_contractor_profile,
)
from nexora.directory.service import create_entity, transition_entity
from nexora.financial.evidence import register_evidence, review_evidence
from nexora.financial.sources import create_fund_source


def _key(prefix: str) -> str:
	return f"{prefix}-{uuid.uuid4().hex}"


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


def run() -> dict[str, object]:
	marker = uuid.uuid4().hex[:10]
	operator = _ensure_user(
		f"nxr-contract-concurrency-operator-{marker}@example.test", "NEXORA Finance Operator"
	)
	manager = _ensure_user(
		f"nxr-contract-concurrency-manager-{marker}@example.test", "NEXORA Finance Manager"
	)
	executor = _ensure_user(
		f"nxr-contract-concurrency-executor-{marker}@example.test", "NEXORA Administrator"
	)
	viewer = _ensure_user(f"nxr-contract-concurrency-viewer-{marker}@example.test", "NEXORA Project Viewer")
	project = frappe.db.get_value("Project", {"project_name": "_Test Contract Concurrency"}, "name")
	if not project:
		project = (
			frappe.get_doc(
				{"doctype": "Project", "project_name": "_Test Contract Concurrency", "status": "Open"}
			)
			.insert(ignore_permissions=True)
			.name
		)
	cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
	if not cost_center:
		raise AssertionError("Missing leaf cost center")
	frappe.set_user(operator)  # nosemgrep
	entity = create_entity(
		{
			"entity_type": "Organization",
			"display_name": f"Concurrent contractor {marker}",
			"idempotency_key": _key("cc-entity"),
		}
	)["name"]
	frappe.set_user(manager)  # nosemgrep
	transition_entity(entity, "Active", _key("cc-entity-active"))
	profile = create_contractor_profile(
		{
			"entity": entity,
			"classification": "Company",
			"valid_from": "2026-01-01",
			"compliance_status": "Valid",
			"idempotency_key": _key("cc-profile"),
		}
	)["profile"]
	transition_contractor_profile(profile, "Active", _key("cc-profile-active"))
	frappe.set_user(operator)  # nosemgrep
	source = create_fund_source(
		{
			"idempotency_key": _key("cc-source"),
			"source_name": f"Concurrent source {marker}",
			"channel": "Cash",
			"project": project,
			"currency": "HNL",
			"original_amount": 5000,
			"exchange_rate": 1,
			"origin_or_sender": "Concurrency test",
			"custodian": operator,
		}
	)["fund_source"]
	file_doc = save_file(
		f"contract-concurrency-{marker}.txt", b"CONTRACT CONCURRENCY", "Project", project, is_private=1
	)
	evidence = register_evidence(
		{
			"project": project,
			"evidence_kind": "Payment Proof",
			"channel": "Cash Receipt",
			"file_url": file_doc.file_url,
			"idempotency_key": _key("cc-evidence"),
		}
	)["evidence"]
	frappe.set_user(manager)  # nosemgrep
	review_evidence(evidence, "Validated", _key("cc-evidence-review"))
	frappe.set_user(operator)  # nosemgrep
	contract = create_contract(
		{
			"contractor": entity,
			"contractor_profile": profile,
			"modality": "Lump Sum",
			"project": project,
			"cost_center": cost_center,
			"fund_source": source,
			"responsible": viewer,
			"scope": "Concurrent contract",
			"currency": "HNL",
			"exchange_rate": 1,
			"start_date": "2026-01-01",
			"end_date": "2026-12-31",
			"signed_on": "2026-01-01",
			"owner_signatory": "Owner",
			"contractor_signatory": "Contractor",
			"lines": [
				{
					"line_code": "LAB-001",
					"description": "Labor",
					"cost_kind": "Labor",
					"cost_center": cost_center,
					"fund_source": source,
					"unit": "Contract",
					"quantity": 1,
					"unit_rate": 1000,
					"amount": 1000,
				}
			],
			"evidence_rows": [
				{"evidence_type": "Contract", "evidence": evidence},
				{"evidence_type": "Signature", "evidence": evidence},
				{"evidence_type": "Approval", "evidence": evidence},
			],
			"idempotency_key": _key("cc-contract"),
		}
	)["contract"]
	frappe.set_user(manager)  # nosemgrep
	for status in ("In Review", "Approved", "Active"):
		transition_contract(contract, status, _key(f"cc-{status}"))
	estimates = []
	for suffix in ("a", "b"):
		frappe.set_user(operator)  # nosemgrep
		estimate = create_contract_estimate(
			{
				"contract": contract,
				"period_start": "2026-01-01",
				"period_end": "2026-01-31",
				"cost_kind": "Labor",
				"lines": [
					{
						"contract_line": "LAB-001",
						"description": f"Concurrent {suffix}",
						"cost_kind": "Labor",
						"quantity": 1,
						"amount": 700,
					}
				],
				"evidence": evidence,
				"requester": operator,
				"idempotency_key": _key(f"cc-estimate-{suffix}"),
			}
		)["estimate"]
		frappe.set_user(manager)  # nosemgrep
		transition_contract_estimate(estimate, "Pending Approval", _key(f"cc-review-{suffix}"))
		transition_contract_estimate(estimate, "Approved", _key(f"cc-approve-{suffix}"))
		estimates.append(estimate)
	frappe.db.commit()  # nosemgrep
	site, sites_path = frappe.local.site, frappe.local.sites_path
	barrier = threading.Barrier(2)

	def worker(pair: tuple[str, str]) -> str:
		suffix, estimate = pair
		frappe.init(site=site, sites_path=sites_path)
		frappe.connect()
		frappe.set_user(executor)  # nosemgrep
		try:
			barrier.wait(timeout=20)
			execute_contract_estimate_payment(
				{
					"estimate": estimate,
					"allocations": [{"source": source, "amount_hnl": 700}],
					"payment_method": "Cash",
					"requester": operator,
					"approved_by": manager,
					"idempotency_key": f"cc-payment-{marker}-{suffix}",
				}
			)
			frappe.db.commit()  # nosemgrep
			return "paid"
		except Exception as exc:
			frappe.db.rollback()
			return "denied_overpay" if "excede" in str(exc) else f"unexpected:{type(exc).__name__}:{exc}"
		finally:
			frappe.destroy()

	with ThreadPoolExecutor(max_workers=2) as pool:
		results = sorted(pool.map(worker, zip(("a", "b"), estimates)))
	paid_count = frappe.db.count("NXR Contract Estimate", {"name": ["in", estimates], "status": "Paid"})
	executed = frappe.db.get_value("NXR Contract", contract, "executed_labor_amount")
	if results != ["denied_overpay", "paid"] or paid_count != 1 or float(executed) != 700:
		raise AssertionError({"results": results, "paid_count": paid_count, "executed": executed})
	return {
		"ok": True,
		"results": results,
		"paid_count": paid_count,
		"executed": executed,
		"contract": contract,
	}
