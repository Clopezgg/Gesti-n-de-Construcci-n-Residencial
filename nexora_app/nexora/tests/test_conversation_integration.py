"""NXR-CNV-0001: motor conversacional real contra Frappe/MariaDB (Bloque 18).

Requiere bench + MariaDB reales; no se pudo ejecutar en el entorno de esta
sesión (sin bench/Frappe/MariaDB — confirmado por
``ModuleNotFoundError: No module named 'frappe'`` al intentar importarlo aquí).
Cobertura pensada para cubrir exactamente la matriz de pruebas mínima de la
misión (sección 23): consulta normal, consulta sin resultados, ambiguo,
entidad/proyecto inexistente, permisos, confirmación, cancelación, doble
confirmación, reintento, proveedor de IA caído/fallback, y operación
financiera completa. Los casos de "proveedor caído"/"fallback" se simulan con
``unittest.mock.patch`` sobre ``nexora.intelligence.orchestrator.execute`` en
vez de depender de credenciales reales de un proveedor (que este entorno no
tiene) — exactamente lo que ``NIP_BLOQUE_6_CONVERSATIONAL_OS.md`` ya
anticipaba como la única forma honesta de ejercer el mecanismo sin un
proveedor real conectado.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.conversation import dispatch
from nexora.directory.service import create_entity
from nexora.financial.sources import create_fund_source
from nexora.intelligence.core import NoProviderAvailableError, ProviderResponse

test_dependencies = ["Cost Center"]


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


def _ensure_entity(entity_type: str, display_name: str) -> str:
	# `FrappeTestCase` no hace rollback entre métodos de la misma clase (solo al
	# final de la clase): crear esta entidad sin condición en cada `setUp` — como
	# hace `create_entity` directamente, sin verificar existencia — produce un
	# "Electricidad López" real distinto por cada uno de los 13 tests de esta
	# clase. `resolve_entity` (Bloque de resolución de beneficiario) los detecta
	# como ambiguos a partir del segundo, exactamente el error real de CI. Mismo
	# patrón idempotente que `_ensure_user`.
	filters = {"entity_type": entity_type, "display_name": display_name}
	existing = frappe.db.get_value("NXR Entity", filters, "name")
	if existing:
		return existing
	return create_entity(
		{
			"entity_type": entity_type,
			"display_name": display_name,
			"idempotency_key": _key("beneficiary-entity"),
		}
	)["name"]


def _model_response(
	intent: str | None, fields: dict | None = None, question: str | None = None
) -> ProviderResponse:
	payload = {
		"intent": intent,
		"confidence": 0.9,
		"fields": fields or {},
		"clarification_question": question,
	}
	return ProviderResponse(
		provider_key="openai",
		capability="text",
		data={"choices": [{"message": {"content": json.dumps(payload)}}]},
	)


class TestConversationIntegrationMariaDB(FrappeTestCase):
	def setUp(self) -> None:
		self.user = _ensure_user(_key("viewer") + "@example.com", "NEXORA Finance Operator")
		self.project = frappe.get_doc({"doctype": "Project", "project_name": f"Casa {_key('proj')}"}).insert(
			ignore_permissions=True
		)
		self.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		if not self.cost_center:
			raise AssertionError("Cost Center test dependency did not create a leaf cost center")
		self.source = create_fund_source(
			{
				"project": self.project.name,
				"source_name": "Remesa 1",
				"channel": "Remittance",
				"original_amount": "50000",
				"origin_or_sender": "Prueba NXR-CNV-0001",
				"idempotency_key": _key("fund"),
			}
		)["fund_source"]
		# `NXR Operation.beneficiary` es un Dynamic Link a `NXR Entity` real (el mismo
		# campo `Link` que exige el formulario guiado) — un gasto por chat a nombre de
		# "Electricidad López" solo puede ejecutarse si ese proveedor ya existe en el
		# directorio, igual que en producción.
		_ensure_entity("Organization", "Electricidad López")
		frappe.set_user(self.user)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")

	@patch("nexora.conversation.nlu.orchestrator_execute")
	def test_normal_query_returns_a_real_balance(self, mock_execute) -> None:
		mock_execute.return_value = _model_response(
			"query_fund_balance", {"project": self.project.project_name}
		)
		result = dispatch.send_message({"text": f"¿Cuánto dinero tengo en {self.project.project_name}?"})
		self.assertEqual("Executed", result["state"])
		# `list_source_balances` identifica cada fuente por su `name` (serie
		# documental), no por su etiqueta humana — no hay "Remesa 1" que buscar,
		# el saldo real (50,000.00) es lo que la respuesta debe reflejar.
		self.assertIn("50,000.00", result["message"])

	@patch("nexora.conversation.nlu.orchestrator_execute")
	def test_query_with_no_results_says_so_honestly(self, mock_execute) -> None:
		empty_project = frappe.get_doc({"doctype": "Project", "project_name": f"Vacío {_key('p')}"}).insert(
			ignore_permissions=True
		)
		mock_execute.return_value = _model_response(
			"query_fund_balance", {"project": empty_project.project_name}
		)
		result = dispatch.send_message({"text": f"¿Cuánto dinero tengo en {empty_project.project_name}?"})
		self.assertEqual("Executed", result["state"])
		self.assertIn("no tiene fuentes", result["message"])

	@patch("nexora.conversation.nlu.orchestrator_execute")
	def test_ambiguous_project_reference_asks_for_clarification_instead_of_guessing(
		self, mock_execute
	) -> None:
		frappe.get_doc({"doctype": "Project", "project_name": "Casa Gemela"}).insert(ignore_permissions=True)
		frappe.get_doc({"doctype": "Project", "project_name": "Casa Gemela Dos"}).insert(
			ignore_permissions=True
		)
		mock_execute.return_value = _model_response("query_fund_balance", {"project": "Casa Gemela"})
		result = dispatch.send_message({"text": "¿Cuánto tengo en Casa Gemela?"})
		self.assertEqual("Collecting", result["state"])
		self.assertIn("más de una coincidencia", result["message"])

	@patch("nexora.conversation.nlu.orchestrator_execute")
	def test_nonexistent_project_is_reported_not_fabricated(self, mock_execute) -> None:
		mock_execute.return_value = _model_response(
			"query_fund_balance", {"project": "Proyecto Que No Existe"}
		)
		result = dispatch.send_message({"text": "¿Cuánto tengo en Proyecto Que No Existe?"})
		self.assertEqual("Failed", result["state"])
		self.assertIn("No encontré ningún proyecto", result["message"])

	@patch("nexora.conversation.nlu.orchestrator_execute")
	def test_project_viewer_without_explicit_grant_is_rejected_by_the_real_permission_not_a_second_table(
		self, mock_execute
	) -> None:
		viewer = _ensure_user(_key("restricted") + "@example.com", "NEXORA Project Viewer")
		frappe.set_user(viewer)
		mock_execute.return_value = _model_response(
			"query_fund_balance", {"project": self.project.project_name}
		)
		result = dispatch.send_message({"text": f"¿Cuánto tengo en {self.project.project_name}?"})
		self.assertEqual("Failed", result["state"])
		self.assertIn("permiso", result["message"])

	@patch("nexora.conversation.nlu.orchestrator_execute")
	def test_write_intent_requires_preview_and_explicit_confirmation_before_executing(
		self, mock_execute
	) -> None:
		mock_execute.return_value = _model_response(
			"register_expense",
			{
				"project": self.project.project_name,
				"beneficiary": "Electricidad López",
				"amount_hnl": "1500",
				"payment_method": "Cash",
				"economic_category": "CONSTRUCTION_MATERIALS",
				"cost_center": self.cost_center,
				"source": self.source,
			},
		)
		preview = dispatch.send_message({"text": "Quiero pagar 1500 al electricista"})
		self.assertEqual("AwaitingConfirmation", preview["state"], preview.get("message"))
		pending_name = preview["data"]["name"]
		self.assertEqual(
			"AwaitingConfirmation",
			frappe.db.get_value("NXR Conversation Pending Intent", pending_name, "status"),
		)
		confirmed = dispatch.confirm_pending_intent({"pending_intent": pending_name})
		self.assertEqual("Executed", confirmed["state"], confirmed.get("message"))
		self.assertEqual(
			"Executed", frappe.db.get_value("NXR Conversation Pending Intent", pending_name, "status")
		)

	@patch("nexora.conversation.nlu.orchestrator_execute")
	def test_cancellation_leaves_no_side_effect(self, mock_execute) -> None:
		mock_execute.return_value = _model_response(
			"register_expense",
			{
				"project": self.project.project_name,
				"beneficiary": "Electricidad López",
				"amount_hnl": "1500",
				"payment_method": "Cash",
				"economic_category": "CONSTRUCTION_MATERIALS",
				"cost_center": self.cost_center,
				"source": self.source,
			},
		)
		preview = dispatch.send_message({"text": "Quiero pagar 1500 al electricista"})
		pending_name = preview["data"]["name"]
		cancelled = dispatch.cancel_pending_intent({"pending_intent": pending_name})
		self.assertEqual("Cancelled", cancelled["state"])
		with self.assertRaises(frappe.ValidationError):
			dispatch.confirm_pending_intent({"pending_intent": pending_name})

	@patch("nexora.conversation.nlu.orchestrator_execute")
	def test_confirming_twice_is_rejected_not_executed_twice(self, mock_execute) -> None:
		mock_execute.return_value = _model_response(
			"register_expense",
			{
				"project": self.project.project_name,
				"beneficiary": "Electricidad López",
				"amount_hnl": "1500",
				"payment_method": "Cash",
				"economic_category": "CONSTRUCTION_MATERIALS",
				"cost_center": self.cost_center,
				"source": self.source,
			},
		)
		preview = dispatch.send_message({"text": "Quiero pagar 1500 al electricista"})
		pending_name = preview["data"]["name"]
		dispatch.confirm_pending_intent({"pending_intent": pending_name})
		with self.assertRaises(frappe.ValidationError):
			dispatch.confirm_pending_intent({"pending_intent": pending_name})

	@patch("nexora.conversation.nlu.orchestrator_execute")
	def test_typed_confirmar_word_confirms_without_a_button(self, mock_execute) -> None:
		mock_execute.return_value = _model_response(
			"register_expense",
			{
				"project": self.project.project_name,
				"beneficiary": "Electricidad López",
				"amount_hnl": "1500",
				"payment_method": "Cash",
				"economic_category": "CONSTRUCTION_MATERIALS",
				"cost_center": self.cost_center,
				"source": self.source,
			},
		)
		dispatch.send_message({"text": "Quiero pagar 1500 al electricista"})
		result = dispatch.send_message({"text": "confirmar"})
		self.assertEqual("Executed", result["state"], result.get("message"))

	def test_provider_down_never_fabricates_an_intent(self) -> None:
		with patch(
			"nexora.conversation.nlu.orchestrator_execute",
			side_effect=NoProviderAvailableError("sin proveedores"),
		):
			result = dispatch.send_message({"text": "¿Cuánto dinero tengo?"})
		self.assertEqual("Failed", result["state"])
		self.assertIn("no está disponible", result["message"])

	@patch("nexora.conversation.nlu.orchestrator_execute")
	def test_retry_after_failure_starts_a_fresh_pending_intent_never_reopens_the_failed_one(
		self, mock_execute
	) -> None:
		mock_execute.return_value = _model_response(
			"register_expense",
			{
				"project": self.project.project_name,
				"beneficiary": "Electricidad López",
				"amount_hnl": "1500",
				"payment_method": "Cash",
				"economic_category": "CONSTRUCTION_MATERIALS",
				"cost_center": self.cost_center,
				"source": self.source,
			},
		)
		first = dispatch.send_message({"text": "Quiero pagar 1500 al electricista"})
		self.assertEqual("AwaitingConfirmation", first["state"], first.get("message"))
		first_name = first["data"]["name"]
		frappe.db.set_value("NXR Conversation Pending Intent", first_name, "idempotency_key", "")
		# A diferencia del guardia de estado (fuera del `try`, sí lanza — ver
		# `test_cancellation_leaves_no_side_effect`), un `ValidationError` de negocio
		# dentro de `_confirm_intent` nunca escapa: se traduce en estado "Failed".
		failed = dispatch.confirm_pending_intent({"pending_intent": first_name})
		self.assertEqual("Failed", failed["state"], failed.get("message"))
		self.assertEqual(
			"Failed", frappe.db.get_value("NXR Conversation Pending Intent", first_name, "status")
		)
		second = dispatch.send_message({"text": "Quiero pagar 1500 al electricista"})
		self.assertNotEqual(first_name, second["data"]["name"])

	def test_guest_is_rejected_before_any_interpretation(self) -> None:
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			dispatch.send_message({"text": "¿Cuánto dinero tengo?"})

	@patch("nexora.conversation.nlu.orchestrator_execute")
	def test_evidence_registration_end_to_end_with_confirmation(self, mock_execute) -> None:
		file_response = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "factura.txt",
				"is_private": 1,
				"content": b"contenido de prueba",
			}
		).insert(ignore_permissions=True)
		mock_execute.return_value = _model_response(
			"register_evidence",
			{
				"project": self.project.project_name,
				"file_url": file_response.file_url,
				"evidence_kind": "Payment Proof",
				"channel": "Email",
			},
		)
		preview = dispatch.send_message({"text": "Guarda esta evidencia"})
		self.assertEqual("AwaitingConfirmation", preview["state"])
		confirmed = dispatch.confirm_pending_intent({"pending_intent": preview["data"]["name"]})
		self.assertEqual("Executed", confirmed["state"])
