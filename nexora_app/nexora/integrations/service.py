from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import audit, correlation, parse_payload
from nexora.integrations.connectivity import check_endpoint_connectivity
from nexora.integrations.core import validate_endpoint
from nexora.permissions import require_action, require_project_access


@frappe.whitelist(methods=["POST"])
def register_integration(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	if data.get("endpoint_url"):
		validate_endpoint(data["endpoint_url"])
	correlation_id = correlation(data)
	with service_write():
		integration = frappe.get_doc(
			{
				"doctype": "NXR Integration",
				"integration_name": data["integration_name"],
				"status": data.get("status", "Inactive"),
				"integration_type": data.get("integration_type", "REST"),
				"endpoint_url": data.get("endpoint_url"),
				"auth_type": data.get("auth_type", "None"),
				"credentials": data.get("credentials"),
				"project": data.get("project"),
				"idempotency_key": data.get("idempotency_key"),
				"payload_hash": data.get("payload_hash"),
				"correlation_id": correlation_id,
			}
		).insert(ignore_permissions=True)
	result = {
		"integration": integration.name,
		"integration_name": integration.integration_name,
		"status": integration.status,
		"integration_type": integration.integration_type,
	}
	# Hallazgo real de auditoría (bloque posterior al 22): `test_connection`, en este
	# mismo archivo, ya audita cada intento de conexión, pero registrar la integración
	# en sí —incluidas sus credenciales— nunca dejó rastro. `after` deliberadamente no
	# incluye `credentials`: el propósito del evento es dejar constancia de que alguien
	# registró la integración, no duplicar el secreto en `NXR Audit Event.after_json`.
	audit(
		"integration_registered",
		"NXR Integration",
		integration.name,
		canonical_payload_hash(result),
		correlation_id,
		result,
	)
	return result


@frappe.whitelist(methods=["POST"])
def test_connection(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Prueba real de conectividad (NXR-INT-0007): antes escribía siempre
	``last_test_result = "Success"`` sin verificar nada. Ahora intenta una solicitud
	HTTP real contra ``endpoint_url`` (ver ``integrations.connectivity``) y registra el
	resultado real, con el detalle en ``NXR Integration Log``. No autentica ni valida
	el contrato de negocio de la integración — solo alcanzabilidad HTTP; ver el
	docstring de ``check_endpoint_connectivity`` para el alcance exacto.
	"""
	data = parse_payload(payload)
	require_action("approve")
	correlation_id = correlation(data)
	integration_name = data["integration"]
	integration = frappe.get_doc("NXR Integration", integration_name)
	if not integration.endpoint_url:
		frappe.throw(
			_("Esta integración no tiene URL de endpoint configurada; no se puede probar la conexión.")
		)
	outcome = check_endpoint_connectivity(integration.endpoint_url)
	result_value = "Success" if outcome["ok"] else "Failure"
	with service_write():
		integration.last_test_at = frappe.utils.now()
		integration.last_test_result = result_value
		integration.append(
			"logs",
			{
				"timestamp": frappe.utils.now(),
				"level": "Info" if outcome["ok"] else "Error",
				"message": outcome["detail"],
			},
		)
		integration.save(ignore_permissions=True)
	result = {
		"integration": integration.name,
		"last_test_result": result_value,
		"detail": outcome["detail"],
		"status_code": outcome["status_code"],
	}
	# Bloque 22: la prueba de conectividad quedaba solo en el log propio de la
	# integración (`NXR Integration Log`), invisible para un auditor que revise
	# la bitácora cruzada del sistema — mismo patrón de auditoría que ya usa
	# cualquier otra acción sensible (crear/probar una credencial de IA o de
	# WhatsApp, ejecutar una operación financiera).
	audit(
		"integration_connection_tested",
		"NXR Integration",
		integration.name,
		canonical_payload_hash({"endpoint_url": integration.endpoint_url, "result": result_value}),
		correlation_id,
		result,
	)
	return result


@frappe.whitelist(methods=["POST"])
def list_integrations(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
	data = parse_payload(payload)
	# NXR-SEC-0001 (Bloque 19): corregido, mismo hallazgo que en `purchases`/
	# `inventory`/`contracts`/`financial`.
	project = str(data.get("project") or "").strip() or None
	require_project_access(project, action="preview")
	filters = {}
	if data.get("status"):
		filters["status"] = data["status"]
	if project:
		filters["project"] = project
	integrations = frappe.get_all(
		"NXR Integration",
		filters=filters,
		fields=[
			"name",
			"integration_name",
			"status",
			"integration_type",
			"endpoint_url",
			"last_test_at",
			"last_test_result",
			"project",
		],
		limit=data.get("limit", 50),
	)
	return list(integrations)
