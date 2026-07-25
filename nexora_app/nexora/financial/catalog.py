from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from nexora.financial.core import FinancialError, money
from nexora.financial.reference_rules import validate_advance_dates


@dataclass(frozen=True)
class EconomicCategory:
	code: str
	label: str
	category_group: str
	cost_factor: int = 0
	budget_factor: int = 0
	savings_factor: int = 0
	investment_factor: int = 0
	requires_cost_center: bool = False


@dataclass(frozen=True)
class OperationProfile:
	code: str
	label: str
	kernel_type: str
	allowed_categories: tuple[str, ...]
	requires_beneficiary: bool = False
	requires_reference: bool = False
	requires_destination: bool = False
	requires_target_project: bool = False
	requires_evidence: bool = False
	requires_payment_reference: bool = False
	requires_due_date: bool = False
	requires_segregation: bool = False


ECONOMIC_CATEGORIES: dict[str, EconomicCategory] = {
	"CONSTRUCTION_MATERIALS": EconomicCategory(
		"CONSTRUCTION_MATERIALS",
		"Materiales de construcción",
		"Construcción",
		1,
		1,
		requires_cost_center=True,
	),
	"CONSTRUCTION_LABOR": EconomicCategory(
		"CONSTRUCTION_LABOR",
		"Mano de obra",
		"Construcción",
		1,
		1,
		requires_cost_center=True,
	),
	"SAVINGS": EconomicCategory("SAVINGS", "Ahorro identificado", "Ahorro", savings_factor=1),
	"MAXIMUM_ACCOUNT": EconomicCategory("MAXIMUM_ACCOUNT", "Cuenta Máxima", "Ahorro", savings_factor=1),
	"INTERNAL_TRANSFER": EconomicCategory("INTERNAL_TRANSFER", "Transferencia interna", "Transferencia"),
	"OTHER_PROJECT": EconomicCategory(
		"OTHER_PROJECT",
		"Aplicación a otro proyecto",
		"Inversión patrimonial",
		investment_factor=1,
	),
	"LAND": EconomicCategory(
		"LAND",
		"Compra de terreno",
		"Inversión patrimonial",
		investment_factor=1,
		requires_cost_center=True,
	),
	"OWNER_DEPOSIT": EconomicCategory("OWNER_DEPOSIT", "Depósito a la propietaria", "Salida no constructiva"),
	"GIFT": EconomicCategory("GIFT", "Regalo", "Salida especial", budget_factor=1, requires_cost_center=True),
	"DONATION": EconomicCategory(
		"DONATION", "Donación", "Salida especial", budget_factor=1, requires_cost_center=True
	),
	"CONTRIBUTION": EconomicCategory(
		"CONTRIBUTION",
		"Contribución",
		"Salida especial",
		budget_factor=1,
		requires_cost_center=True,
	),
	"TAX": EconomicCategory("TAX", "Impuesto", "Administración", budget_factor=1, requires_cost_center=True),
	"LEGAL": EconomicCategory(
		"LEGAL", "Pago legal", "Administración", budget_factor=1, requires_cost_center=True
	),
	"TRAVEL": EconomicCategory(
		"TRAVEL", "Viaje", "Administración", budget_factor=1, requires_cost_center=True
	),
	"SPECIAL": EconomicCategory(
		"SPECIAL",
		"Pago especial",
		"Salida especial",
		budget_factor=1,
		requires_cost_center=True,
	),
	"ADVANCE": EconomicCategory("ADVANCE", "Anticipo pendiente de liquidación", "Anticipo", budget_factor=1),
	"ADVANCE_SETTLEMENT": EconomicCategory(
		"ADVANCE_SETTLEMENT",
		"Liquidación de anticipo",
		"Construcción",
		cost_factor=1,
		requires_cost_center=True,
	),
	"RECLASSIFICATION": EconomicCategory("RECLASSIFICATION", "Reclasificación analítica", "Corrección"),
	"RETURN": EconomicCategory("RETURN", "Devolución real", "Corrección"),
	"REVERSAL": EconomicCategory("REVERSAL", "Reversión sin devolución de efectivo", "Corrección"),
	"DOCUMENTARY": EconomicCategory("DOCUMENTARY", "Sustitución documental", "Corrección"),
}

RECLASSIFIABLE_CATEGORIES = (
	"CONSTRUCTION_MATERIALS",
	"CONSTRUCTION_LABOR",
	"SAVINGS",
	"MAXIMUM_ACCOUNT",
	"OTHER_PROJECT",
	"LAND",
	"OWNER_DEPOSIT",
	"GIFT",
	"DONATION",
	"CONTRIBUTION",
	"TAX",
	"LEGAL",
	"TRAVEL",
	"SPECIAL",
	"ADVANCE",
	"ADVANCE_SETTLEMENT",
)
ADVANCE_SETTLEMENT_CATEGORIES = (
	"CONSTRUCTION_MATERIALS",
	"CONSTRUCTION_LABOR",
	"LAND",
	"TAX",
	"LEGAL",
	"TRAVEL",
	"SPECIAL",
	"ADVANCE_SETTLEMENT",
)

OPERATION_PROFILES: dict[str, OperationProfile] = {
	"CONSTRUCTION_PAYMENT": OperationProfile(
		"CONSTRUCTION_PAYMENT",
		"Pago de construcción",
		"Outflow",
		("CONSTRUCTION_MATERIALS", "CONSTRUCTION_LABOR"),
		requires_beneficiary=True,
	),
	"SAVINGS_APPLICATION": OperationProfile(
		"SAVINGS_APPLICATION", "Aplicación a ahorro", "Outflow", ("SAVINGS",)
	),
	"MAXIMUM_ACCOUNT": OperationProfile(
		"MAXIMUM_ACCOUNT", "Aplicación a Cuenta Máxima", "Outflow", ("MAXIMUM_ACCOUNT",)
	),
	"INTERNAL_TRANSFER": OperationProfile(
		"INTERNAL_TRANSFER",
		"Transferencia interna",
		"Internal Transfer",
		("INTERNAL_TRANSFER",),
		requires_destination=True,
		requires_target_project=True,
		requires_segregation=True,
	),
	"OTHER_PROJECT": OperationProfile(
		"OTHER_PROJECT",
		"Aplicación a otro proyecto",
		"Outflow",
		("OTHER_PROJECT",),
		requires_reference=True,
		requires_target_project=True,
	),
	"LAND_PURCHASE": OperationProfile(
		"LAND_PURCHASE", "Compra de terreno", "Outflow", ("LAND",), requires_beneficiary=True
	),
	"OWNER_DEPOSIT": OperationProfile(
		"OWNER_DEPOSIT",
		"Depósito a la propietaria",
		"Outflow",
		("OWNER_DEPOSIT",),
		requires_beneficiary=True,
	),
	"GIFT_PAYMENT": OperationProfile(
		"GIFT_PAYMENT",
		"Regalo",
		"Outflow",
		("GIFT",),
		requires_beneficiary=True,
		requires_evidence=True,
		requires_payment_reference=True,
	),
	"DONATION_PAYMENT": OperationProfile(
		"DONATION_PAYMENT",
		"Donación",
		"Outflow",
		("DONATION",),
		requires_beneficiary=True,
		requires_evidence=True,
		requires_payment_reference=True,
	),
	"CONTRIBUTION_PAYMENT": OperationProfile(
		"CONTRIBUTION_PAYMENT",
		"Contribución",
		"Outflow",
		("CONTRIBUTION",),
		requires_beneficiary=True,
		requires_evidence=True,
		requires_payment_reference=True,
	),
	"TAX_PAYMENT": OperationProfile(
		"TAX_PAYMENT", "Pago de impuesto", "Outflow", ("TAX",), requires_beneficiary=True
	),
	"LEGAL_PAYMENT": OperationProfile(
		"LEGAL_PAYMENT", "Pago legal", "Outflow", ("LEGAL",), requires_beneficiary=True
	),
	"TRAVEL_PAYMENT": OperationProfile(
		"TRAVEL_PAYMENT", "Pago de viaje", "Outflow", ("TRAVEL",), requires_beneficiary=True
	),
	"SPECIAL_PAYMENT": OperationProfile(
		"SPECIAL_PAYMENT",
		"Pago especial",
		"Outflow",
		("SPECIAL",),
		requires_beneficiary=True,
		requires_evidence=True,
		requires_payment_reference=True,
	),
	"ADVANCE_DISBURSEMENT": OperationProfile(
		"ADVANCE_DISBURSEMENT",
		"Desembolso de anticipo",
		"Outflow",
		("ADVANCE",),
		requires_beneficiary=True,
		requires_due_date=True,
		requires_segregation=True,
	),
	"ADVANCE_SETTLEMENT": OperationProfile(
		"ADVANCE_SETTLEMENT",
		"Liquidación de anticipo",
		"Analytic Adjustment",
		ADVANCE_SETTLEMENT_CATEGORIES,
		requires_reference=True,
		requires_segregation=True,
	),
	"RECLASSIFICATION": OperationProfile(
		"RECLASSIFICATION",
		"Reclasificación",
		"Reclassification",
		RECLASSIFIABLE_CATEGORIES,
		requires_reference=True,
		requires_segregation=True,
	),
	"REAL_RETURN": OperationProfile(
		"REAL_RETURN",
		"Devolución real",
		"Real Return",
		("RETURN",),
		requires_reference=True,
		requires_evidence=True,
		requires_segregation=True,
	),
	"REVERSAL_NO_CASH": OperationProfile(
		"REVERSAL_NO_CASH",
		"Reversión sin devolución de efectivo",
		"Analytic Adjustment",
		("REVERSAL",),
		requires_reference=True,
		requires_segregation=True,
	),
	"DOCUMENT_SUBSTITUTION": OperationProfile(
		"DOCUMENT_SUBSTITUTION",
		"Sustitución documental",
		"Reclassification",
		("DOCUMENTARY",),
		requires_reference=True,
		requires_evidence=True,
		requires_segregation=True,
	),
	"COMMITMENT_RESERVE": OperationProfile(
		"COMMITMENT_RESERVE",
		"Reserva de compromiso",
		"Commitment Reserve",
		(
			"CONSTRUCTION_MATERIALS",
			"CONSTRUCTION_LABOR",
			"TAX",
			"LEGAL",
			"TRAVEL",
			"SPECIAL",
			"ADVANCE",
		),
	),
	"COMMITMENT_EXECUTION": OperationProfile(
		"COMMITMENT_EXECUTION",
		"Ejecución de compromiso",
		"Commitment Execution",
		(
			"CONSTRUCTION_MATERIALS",
			"CONSTRUCTION_LABOR",
			"TAX",
			"LEGAL",
			"TRAVEL",
			"SPECIAL",
			"ADVANCE",
		),
	),
	"COMMITMENT_RELEASE": OperationProfile(
		"COMMITMENT_RELEASE",
		"Liberación de compromiso",
		"Commitment Release",
		(
			"CONSTRUCTION_MATERIALS",
			"CONSTRUCTION_LABOR",
			"TAX",
			"LEGAL",
			"TRAVEL",
			"SPECIAL",
			"ADVANCE",
		),
	),
}


def category_rows() -> list[dict[str, Any]]:
	return [asdict(ECONOMIC_CATEGORIES[key]) for key in sorted(ECONOMIC_CATEGORIES)]


def operation_rows() -> list[dict[str, Any]]:
	rows = []
	for key in sorted(OPERATION_PROFILES):
		row = asdict(OPERATION_PROFILES[key])
		row["allowed_categories"] = "\n".join(row["allowed_categories"])
		rows.append(row)
	return rows


def _required(value: object, message: str) -> None:
	if not str(value or "").strip():
		raise FinancialError(message)


def normalize_analytic_splits(
	payload: Mapping[str, Any], amount: Decimal, required: bool
) -> list[dict[str, str]]:
	rows = payload.get("analytic_splits") or []
	if not rows and payload.get("cost_center") and amount > 0:
		rows = [
			{
				"cost_center": payload["cost_center"],
				"amount_hnl": amount,
				"project": (
					payload.get("target_project")
					if payload.get("economic_category") == "OTHER_PROJECT"
					else payload.get("project")
				),
			}
		]
	if not rows and amount > 0 and payload.get("economic_category") == "OTHER_PROJECT":
		rows = [
			{
				"cost_center": "",
				"amount_hnl": amount,
				"project": payload.get("target_project"),
			}
		]
	if required and not rows:
		raise FinancialError("La clasificación exige centro de costo o divisiones analíticas.")
	if not rows:
		return []
	seen: set[tuple[str, str]] = set()
	normalized: list[dict[str, str]] = []
	for row in rows:
		cost_center = str(row.get("cost_center") or "").strip()
		project = str(row.get("project") or payload.get("project") or "").strip()
		row_amount = money(row.get("amount_hnl", row.get("amount")))
		if required and not cost_center:
			raise FinancialError("Cada división analítica requiere centro de costo.")
		if row_amount <= 0 or not project:
			raise FinancialError("Cada división analítica requiere proyecto e importe positivo.")
		key = (project, cost_center)
		if key in seen:
			raise FinancialError(
				f"El centro de costo {cost_center or '(sin centro)'} está repetido en el proyecto {project}."
			)
		seen.add(key)
		normalized.append(
			{
				"cost_center": cost_center,
				"amount_hnl": f"{row_amount:.2f}",
				"project": project,
			}
		)
	if money(sum((money(row["amount_hnl"]) for row in normalized), Decimal(0))) != amount:
		raise FinancialError("Las divisiones entre centros deben sumar el importe analítico completo.")
	return normalized


def apply_profile(
	payload: Mapping[str, Any], profile: OperationProfile, category: EconomicCategory
) -> dict[str, Any]:
	if category.code not in profile.allowed_categories:
		raise FinancialError(f"La categoría {category.code} no está permitida para el tipo {profile.code}.")
	data = dict(payload)
	data["operation_code"] = profile.code
	data["operation_type"] = profile.kernel_type
	data["economic_category"] = category.code
	data["requires_segregation"] = int(profile.requires_segregation)
	amount = money(data.get("amount_hnl", data.get("amount")))
	if profile.code == "DOCUMENT_SUBSTITUTION":
		if amount != 0:
			raise FinancialError("Una sustitución documental debe tener importe cero.")
	elif amount < 0:
		raise FinancialError("El importe no puede ser negativo.")
	elif amount == 0 and profile.code not in {
		"RECLASSIFICATION",
		"REVERSAL_NO_CASH",
	}:
		raise FinancialError("El importe debe ser mayor que cero.")
	if profile.requires_beneficiary:
		_required(data.get("beneficiary"), "El tipo de operación requiere beneficiario o responsable.")
	if profile.requires_reference:
		_required(data.get("reference_name"), "El tipo de operación requiere documento de referencia.")
	if profile.requires_destination:
		_required(data.get("destination_source"), "La transferencia interna requiere fuente de destino.")
	if profile.requires_target_project:
		_required(data.get("target_project"), "El tipo de operación requiere proyecto de destino.")
	if profile.requires_evidence:
		_required(data.get("evidence"), "El tipo de operación requiere evidencia.")
	if profile.requires_payment_reference:
		_required(data.get("approved_by"), "La operación especial requiere autorizador.")
		_required(data.get("operation_date"), "La operación especial requiere fecha.")
		_required(data.get("payment_method"), "La operación especial requiere medio de pago.")
		_required(data.get("external_reference"), "La operación especial requiere referencia.")
	if profile.requires_due_date:
		_required(data.get("operation_date"), "El anticipo requiere fecha.")
		_required(data.get("due_date"), "El anticipo requiere vencimiento.")
		validate_advance_dates(data.get("operation_date"), data.get("due_date"))
	if profile.code == "REVERSAL_NO_CASH":
		data["reference_doctype"] = "NXR Operation"
		data["reversal_of"] = data.get("reversal_of") or data.get("reference_name")
	if profile.code == "DOCUMENT_SUBSTITUTION":
		data["reference_doctype"] = "NXR Operation"
		data["substitutes_operation"] = data.get("substitutes_operation") or data.get("reference_name")

	if profile.code in {
		"RECLASSIFICATION",
		"REAL_RETURN",
		"REVERSAL_NO_CASH",
		"DOCUMENT_SUBSTITUTION",
	}:
		data["analytic_factors"] = {dimension: 0 for dimension in ("Cost", "Budget", "Savings", "Investment")}
		data["analytic_splits"] = []
		data["affects_cost"] = 0
		data["affects_budget"] = 0
		return data

	factors = {
		"Cost": category.cost_factor,
		"Budget": 0 if profile.code == "ADVANCE_SETTLEMENT" else category.budget_factor,
		"Savings": 0 if profile.code == "ADVANCE_SETTLEMENT" else category.savings_factor,
		"Investment": category.investment_factor,
	}
	data["analytic_factors"] = factors
	data["affects_cost"] = int(bool(factors["Cost"]))
	data["affects_budget"] = int(bool(factors["Budget"]))
	requires_splits = category.requires_cost_center and any(factors.values())
	data["analytic_splits"] = normalize_analytic_splits(data, amount, requires_splits)
	return data
