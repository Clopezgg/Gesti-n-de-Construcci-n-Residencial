from __future__ import annotations

from typing import Any, Mapping

import frappe
from frappe import _

from nexora.financial.catalog import EconomicCategory, OperationProfile, apply_profile
from nexora.financial.core import FinancialError
from nexora.financial.db import parse_payload
from nexora.financial.evidence import (
	expected_evidence_kind,
	operation_evidence_policy,
	validate_operation_evidence,
)
from nexora.financial.operations import execute, execute_financial_operation
from nexora.financial.reference_rules import validate_segregation
from nexora.financial.references import advance_status, prepare_reference_operation
from nexora.permissions import require_action


def _operation_profile(code: str) -> OperationProfile:
	doc = frappe.get_doc("NXR Operation Type", code)
	if not doc.active:
		frappe.throw(_("El tipo de operación está inactivo."))
	return OperationProfile(
		code=doc.code,
		label=doc.operation_name,
		kernel_type=doc.kernel_type,
		allowed_categories=tuple(
			category for category in str(doc.allowed_categories or "").splitlines() if category
		),
		requires_beneficiary=bool(doc.requires_beneficiary),
		requires_reference=bool(doc.requires_reference),
		requires_destination=bool(doc.requires_destination),
		requires_target_project=bool(doc.requires_target_project),
		requires_evidence=bool(doc.requires_evidence),
		requires_payment_reference=bool(doc.requires_payment_reference),
		requires_due_date=bool(doc.requires_due_date),
		requires_segregation=bool(doc.requires_segregation),
	)


def _economic_category(code: str) -> EconomicCategory:
	doc = frappe.get_doc("NXR Economic Category", code)
	if not doc.active:
		frappe.throw(_("La categoría económica está inactiva."))
	return EconomicCategory(
		code=doc.code,
		label=doc.category_name,
		category_group=doc.category_group,
		cost_factor=int(doc.cost_factor or 0),
		budget_factor=int(doc.budget_factor or 0),
		savings_factor=int(doc.savings_factor or 0),
		investment_factor=int(doc.investment_factor or 0),
		requires_cost_center=bool(doc.requires_cost_center),
	)


def prepare_central_payload(
	payload: str | Mapping[str, Any],
	*,
	lock_reference: bool = False,
) -> dict[str, Any]:
	data = parse_payload(payload)
	code = str(data.get("operation_code") or "").strip()
	category = str(data.get("economic_category") or "").strip()
	if not code or not category:
		frappe.throw(_("Tipo de operación y categoría económica son obligatorios."))
	profile = _operation_profile(code)
	try:
		prepared = apply_profile(data, profile, _economic_category(category))
		policy = operation_evidence_policy(prepared, profile_requires_evidence=profile.requires_evidence)
		prepared["evidence_policy_required"] = int(policy.required)
		prepared["evidence_policy_reason"] = policy.reason
		prepared["evidence"] = validate_operation_evidence(
			prepared.get("evidence"),
			project=str(prepared.get("project") or ""),
			policy=policy,
			expected_kind=expected_evidence_kind(profile.code, policy),
		)
		if profile.requires_segregation:
			validate_segregation(
				prepared.get("requester"),
				prepared.get("approved_by"),
				frappe.session.user,
			)
		prepared = prepare_reference_operation(prepared, lock=lock_reference)
		for row in prepared.get("allocations") or []:
			source_name = str(row.get("source") or row.get("fund_source") or "")
			source_project = frappe.db.get_value("NXR Fund Source", source_name, "project")
			if source_project != prepared.get("project"):
				frappe.throw(_("Cada fuente de origen debe pertenecer al proyecto de la operación."))
		if prepared.get("destination_source"):
			destination_project = frappe.db.get_value(
				"NXR Fund Source", prepared["destination_source"], "project"
			)
			if destination_project != prepared.get("target_project"):
				frappe.throw(_("La fuente de destino debe pertenecer al proyecto de destino."))
		return prepared
	except (FinancialError, ValueError) as exc:
		frappe.throw(_(str(exc)))


@frappe.whitelist(methods=["POST"])
def list_analytic_catalogs() -> dict[str, list[dict[str, Any]]]:
	require_action("preview")
	return {
		"operation_types": frappe.get_all(
			"NXR Operation Type",
			filters={"active": 1},
			fields=[
				"code",
				"operation_name",
				"kernel_type",
				"allowed_categories",
				"requires_beneficiary",
				"requires_reference",
				"requires_destination",
				"requires_target_project",
				"requires_payment_reference",
				"requires_evidence",
				"requires_due_date",
				"requires_segregation",
			],
			order_by="code asc",
		),
		"economic_categories": frappe.get_all(
			"NXR Economic Category",
			filters={"active": 1},
			fields=[
				"code",
				"category_name",
				"category_group",
				"cost_factor",
				"budget_factor",
				"savings_factor",
				"investment_factor",
				"requires_cost_center",
			],
			order_by="code asc",
		),
	}


@frappe.whitelist(methods=["POST"])
def preview_central_operation(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	from nexora.financial.db import preview

	require_action("preview")
	return preview(prepare_central_payload(payload), lock=False)


@frappe.whitelist(methods=["POST"])
def execute_central_operation(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = prepare_central_payload(payload, lock_reference=True)
	if data["operation_type"] in {
		"Commitment Reserve",
		"Commitment Execution",
		"Commitment Release",
	}:
		frappe.throw(_("Use el servicio específico de compromiso para este tipo."))
	if data["operation_type"] in {
		"Outflow",
		"Real Return",
		"Reclassification",
		"Analytic Adjustment",
		"Internal Transfer",
	}:
		action = (
			"return"
			if data["operation_type"] == "Real Return"
			else "reclassify"
			if data["operation_type"] in {"Reclassification", "Analytic Adjustment"}
			else "execute"
		)
		return execute(data, action=action)
	return execute_financial_operation(data)


@frappe.whitelist(methods=["POST"])
def get_advance_status(operation: str) -> dict[str, Any]:
	require_action("preview")
	return advance_status(operation)


@frappe.whitelist(methods=["POST"])
def list_central_operations(project: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
	require_action("preview")
	filters = {"project": project} if project else None
	return frappe.get_all(
		"NXR Operation",
		filters=filters,
		fields=[
			"name",
			"document_number",
			"operation_date",
			"due_date",
			"operation_code",
			"operation_type",
			"project",
			"target_project",
			"amount_hnl",
			"economic_category",
			"cost_center",
			"evidence",
			"reference_name",
			"reference_balance_after_hnl",
			"status",
		],
		order_by="operation_date desc, creation desc",
		limit_page_length=min(max(int(limit or 50), 1), 200),
	)
