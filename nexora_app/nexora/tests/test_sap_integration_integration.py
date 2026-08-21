"""Adaptador SAP contra Frappe/MariaDB real.

Requiere bench + MariaDB reales; no se pudo ejecutar en el entorno de esta
sesión (sin bench/Frappe/MariaDB — confirmado por
``ModuleNotFoundError: No module named 'frappe'`` al intentar importarlo
aquí). Las llamadas HTTP reales contra SAP se simulan con
``unittest.mock.patch`` sobre ``nexora.integrations.sap._open_sap_request``
— el único punto real de transporte del módulo — nunca sobre la lógica de
autenticación, idempotencia o auditoría, que se ejerce de verdad contra
Frappe/MariaDB real igual que el resto del código de esta prueba.

Cobertura pensada para la matriz mínima honesta de una integración externa:
permisos positivos y negativos (Administrador vs. Gerente vs. Operador),
guardar una conexión nunca llama a SAP, probarla sí hace una llamada real
(simulada) y registra el resultado real, un envío de documento exitoso deja
auditoría y bitácora, un envío fallido nunca se enmascara como éxito, y la
misma clave de idempotencia con el mismo payload no reenvía el documento una
segunda vez.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.integrations import sap


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


class SapIntegrationTestBase(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:8]
		cls.admin = _ensure_user(f"nxr-sap-admin-{marker}@example.test", "NEXORA Administrator")
		cls.manager = _ensure_user(f"nxr-sap-manager-{marker}@example.test", "NEXORA Finance Manager")
		cls.operator = _ensure_user(f"nxr-sap-operator-{marker}@example.test", "NEXORA Finance Operator")
		cls.auditor = _ensure_user(f"nxr-sap-auditor-{marker}@example.test", "NEXORA Auditor")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _connect(self, **overrides) -> str:
		frappe.set_user(self.admin)
		payload = {
			"connection_name": f"_Test SAP {uuid.uuid4().hex[:8]}",
			"base_url": "https://sap.example.invalid",
			"auth_type": "Basic",
			"username": "nexora_svc",
			"password": "s3cr3t",
			"idempotency_key": _key("sap-connect"),
			**overrides,
		}
		return sap.connect_connection(payload)["connection"]


class TestConnectConnectionPermissions(SapIntegrationTestBase):
	def test_administrator_can_save_a_connection(self) -> None:
		connection = self._connect()
		self.assertTrue(frappe.db.exists("NXR SAP Connection", connection))

	def test_finance_manager_cannot_manage_a_connection(self) -> None:
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			sap.connect_connection(
				{
					"connection_name": f"_Test SAP {uuid.uuid4().hex[:8]}",
					"base_url": "https://sap.example.invalid",
					"auth_type": "Basic",
					"username": "u",
					"password": "p",
					"idempotency_key": _key("sap-connect"),
				}
			)

	def test_finance_operator_cannot_manage_a_connection(self) -> None:
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			sap.connect_connection(
				{
					"connection_name": f"_Test SAP {uuid.uuid4().hex[:8]}",
					"base_url": "https://sap.example.invalid",
					"auth_type": "Basic",
					"username": "u",
					"password": "p",
					"idempotency_key": _key("sap-connect"),
				}
			)

	def test_connect_connection_never_calls_sap(self) -> None:
		with patch("nexora.integrations.sap._open_sap_request") as mocked:
			self._connect()
		mocked.assert_not_called()

	def test_secrets_are_stored_encrypted_and_never_returned_in_plain_text(self) -> None:
		connection = self._connect()
		result = frappe.db.get_value("NXR SAP Connection", connection, "password")
		self.assertNotEqual("s3cr3t", result)
		doc = frappe.get_doc("NXR SAP Connection", connection)
		self.assertEqual("s3cr3t", doc.get_password("password"))


class TestConnectionTestRecordsARealResult(SapIntegrationTestBase):
	def test_a_successful_probe_activates_the_connection_and_logs_it(self) -> None:
		connection = self._connect()
		with patch("nexora.integrations.sap._open_sap_request", return_value=(200, {"status": "ok"})):
			result = sap.test_sap_connection({"connection": connection})
		self.assertEqual("Success", result["last_test_result"])
		doc = frappe.get_doc("NXR SAP Connection", connection)
		self.assertEqual("Active", doc.status)
		self.assertEqual("Success", doc.last_test_result)
		self.assertEqual(1, len(doc.logs))
		self.assertEqual("Info", doc.logs[0].level)
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "sap_connection_tested",
					"reference_doctype": "NXR SAP Connection",
					"reference_name": connection,
				},
			)
		)

	def test_a_failed_probe_never_records_a_fabricated_success(self) -> None:
		connection = self._connect()
		with patch(
			"nexora.integrations.sap._open_sap_request",
			side_effect=sap.SapIntegrationError(
				"SAP respondió HTTP 401 al probar la conexión: no autorizado"
			),
		):
			result = sap.test_sap_connection({"connection": connection})
		self.assertEqual("Failure", result["last_test_result"])
		doc = frappe.get_doc("NXR SAP Connection", connection)
		self.assertNotEqual("Active", doc.status)
		self.assertEqual("Failure", doc.last_test_result)
		self.assertEqual(1, len(doc.logs))
		self.assertEqual("Error", doc.logs[0].level)
		self.assertIn("401", doc.logs[0].message)

	def test_a_non_retryable_client_error_is_never_retried(self) -> None:
		"""GP-13: `test_a_failed_probe_never_records_a_fabricated_success`
		mockea `_open_sap_request` en sí — el envoltorio de reintento —, así
		que nunca ejerce su propia decisión de no reintentar. Esta prueba
		mockea un nivel más abajo (`urllib.request.urlopen`, mismo patrón que
		`test_outbound_graph_call_never_retries_a_non_transient_client_error`
		de WhatsApp) para demostrar que un 401 real detiene el intento en la
		primera llamada, sin gastar una segunda llamada real contra SAP que
		fallaría exactamente igual."""
		import io
		import urllib.error

		connection = self._connect()
		auth_error = urllib.error.HTTPError(
			url="https://sap.example.invalid/",
			code=401,
			msg="Unauthorized",
			hdrs=None,
			fp=io.BytesIO(b'{"error": "invalid credentials"}'),
		)
		with patch("nexora.integrations.sap.urllib.request.urlopen", side_effect=auth_error) as mock_urlopen:
			result = sap.test_sap_connection({"connection": connection})
		self.assertEqual(1, mock_urlopen.call_count)
		self.assertEqual("Failure", result["last_test_result"])
		doc = frappe.get_doc("NXR SAP Connection", connection)
		self.assertNotEqual("Active", doc.status)
		self.assertIn("401", doc.logs[0].message)

	def test_a_timeout_is_retried_once_then_reported_as_a_real_failure(self) -> None:
		"""GP-13: un timeout real (envuelto por `urllib` como `URLError`, no
		`HTTPError` — nunca llega un código HTTP porque no hubo respuesta) sí
		es transitorio y debe reintentarse exactamente una vez antes de
		rendirse — nunca fabricar un éxito, y nunca reintentar indefinidamente."""
		import urllib.error

		connection = self._connect()
		with patch(
			"nexora.integrations.sap.urllib.request.urlopen",
			# `urlopen()` real envuelve cualquier `OSError` del socket (incluido un
			# timeout) en `URLError` dentro de `do_open()` antes de que llegue a
			# quien la llama (`urllib/request.py`, `except OSError as err: raise
			# URLError(err)`) — mockear `urlopen` en sí se salta esa envoltura
			# interna, así que hay que reproducir el mismo tipo que un llamador
			# real observaría, no el `socket.timeout` crudo.
			side_effect=urllib.error.URLError(TimeoutError("timed out")),
		) as mock_urlopen:
			result = sap.test_sap_connection({"connection": connection})
		self.assertEqual(2, mock_urlopen.call_count, "Un timeout debe reintentarse exactamente una vez.")
		self.assertEqual("Failure", result["last_test_result"])
		doc = frappe.get_doc("NXR SAP Connection", connection)
		self.assertNotEqual("Active", doc.status)
		self.assertEqual(1, len(doc.logs))
		self.assertEqual("Error", doc.logs[0].level)

	def test_only_administrator_may_test_a_connection(self) -> None:
		connection = self._connect()
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			sap.test_sap_connection({"connection": connection})


class TestSubmitDocumentPermissions(SapIntegrationTestBase):
	def _active_connection(self) -> str:
		connection = self._connect()
		with patch("nexora.integrations.sap._open_sap_request", return_value=(200, {"status": "ok"})):
			sap.test_sap_connection({"connection": connection})
		return connection

	def test_finance_manager_can_submit_a_document(self) -> None:
		connection = self._active_connection()
		frappe.set_user(self.manager)
		with patch(
			"nexora.integrations.sap._open_sap_request", return_value=(201, {"sap_document": "4500001"})
		) as mocked:
			result = sap.submit_document(
				{
					"connection": connection,
					"document_type": "PurchaseOrder",
					"endpoint_path": "api/purchase-orders",
					"document_payload": {"amount": 100},
					"idempotency_key": _key("sap-submit"),
				}
			)
		mocked.assert_called_once()
		self.assertEqual(201, result["sap_status_code"])
		self.assertEqual({"sap_document": "4500001"}, result["sap_response"])

	def test_finance_operator_cannot_submit_a_document(self) -> None:
		connection = self._active_connection()
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			sap.submit_document(
				{
					"connection": connection,
					"document_type": "PurchaseOrder",
					"endpoint_path": "api/purchase-orders",
					"document_payload": {"amount": 100},
					"idempotency_key": _key("sap-submit"),
				}
			)

	def test_submitting_to_an_inactive_connection_is_rejected(self) -> None:
		connection = self._connect()
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.ValidationError):
			sap.submit_document(
				{
					"connection": connection,
					"document_type": "PurchaseOrder",
					"endpoint_path": "api/purchase-orders",
					"document_payload": {"amount": 100},
					"idempotency_key": _key("sap-submit"),
				}
			)


class TestSubmitDocumentIdempotencyAndFailure(SapIntegrationTestBase):
	def _active_connection(self) -> str:
		connection = self._connect()
		with patch("nexora.integrations.sap._open_sap_request", return_value=(200, {"status": "ok"})):
			sap.test_sap_connection({"connection": connection})
		return connection

	def test_the_same_idempotency_key_and_payload_never_calls_sap_twice(self) -> None:
		connection = self._active_connection()
		frappe.set_user(self.manager)
		key = _key("sap-submit")
		payload = {
			"connection": connection,
			"document_type": "PurchaseOrder",
			"endpoint_path": "api/purchase-orders",
			"document_payload": {"amount": 100},
			"idempotency_key": key,
		}
		with patch(
			"nexora.integrations.sap._open_sap_request", return_value=(201, {"sap_document": "4500001"})
		) as mocked:
			first = sap.submit_document(dict(payload))
			second = sap.submit_document(dict(payload))
		mocked.assert_called_once()
		self.assertEqual(first, second)

	def test_a_failed_submission_is_audited_and_returned_as_a_completed_failure(self) -> None:
		"""No lanza: un rechazo de SAP se completa con ``ok: False`` en vez de
		una excepción, para que la clave de idempotencia no quede en
		``Processing`` para siempre (ver docstring de ``submit_document``)."""
		connection = self._active_connection()
		frappe.set_user(self.manager)
		with patch(
			"nexora.integrations.sap._open_sap_request",
			side_effect=sap.SapIntegrationError(
				"SAP respondió HTTP 422 al enviar el documento: dato inválido"
			),
		):
			result = sap.submit_document(
				{
					"connection": connection,
					"document_type": "PurchaseOrder",
					"endpoint_path": "api/purchase-orders",
					"document_payload": {"amount": -1},
					"idempotency_key": _key("sap-submit"),
				}
			)
		self.assertFalse(result["ok"])
		self.assertIn("422", result["error"])
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "sap_document_submission_failed",
					"reference_doctype": "NXR SAP Connection",
					"reference_name": connection,
				},
			)
		)
		doc = frappe.get_doc("NXR SAP Connection", connection)
		self.assertEqual("Error", doc.logs[-1].level)

	def test_retrying_the_same_key_after_a_failure_returns_the_cached_failure_not_stuck_processing(
		self,
	) -> None:
		"""Regresión directa del defecto real encontrado y corregido en este
		mismo módulo: antes, un rechazo de SAP lanzaba sin completar el
		registro de idempotencia, y todo reintento con la misma clave quedaba
		atrapado para siempre en "La misma solicitud ya está en
		procesamiento", sin que ninguna solicitud siguiera en curso."""
		connection = self._active_connection()
		frappe.set_user(self.manager)
		key = _key("sap-submit")
		payload = {
			"connection": connection,
			"document_type": "PurchaseOrder",
			"endpoint_path": "api/purchase-orders",
			"document_payload": {"amount": -1},
			"idempotency_key": key,
		}
		with patch(
			"nexora.integrations.sap._open_sap_request",
			side_effect=sap.SapIntegrationError("SAP respondió HTTP 422: dato inválido"),
		) as mocked:
			first = sap.submit_document(dict(payload))
			second = sap.submit_document(dict(payload))
		mocked.assert_called_once()
		self.assertFalse(first["ok"])
		self.assertEqual(first, second)


class TestListConnections(SapIntegrationTestBase):
	def test_auditor_can_list_connections_without_seeing_secrets(self) -> None:
		connection = self._connect()
		frappe.set_user(self.auditor)
		rows = sap.list_connections({})
		names = {row["name"] for row in rows}
		self.assertIn(connection, names)
		for row in rows:
			self.assertNotIn("password", row)
			self.assertNotIn("client_secret", row)
			self.assertNotIn("static_token", row)

	def test_finance_operator_cannot_list_connections(self) -> None:
		self._connect()
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			sap.list_connections({})


class TestGetSapSummary(SapIntegrationTestBase):
	"""Bloque de cierre de producción, Paso 2: la pestaña «Resumen» de la
	superficie SAP no puede inventar cifras — se comparan deltas antes/después
	de la propia acción real, no un conteo absoluto, porque la suite comparte
	base de datos con el resto de las pruebas de este archivo."""

	def _active_connection(self) -> str:
		connection = self._connect()
		with patch("nexora.integrations.sap._open_sap_request", return_value=(200, {"status": "ok"})):
			sap.test_sap_connection({"connection": connection})
		return connection

	def test_administrator_sees_real_counts_move_by_exactly_what_happened(self) -> None:
		before = sap.get_sap_summary()
		connection = self._active_connection()
		frappe.set_user(self.manager)
		with patch(
			"nexora.integrations.sap._open_sap_request", return_value=(201, {"sap_document": "4500001"})
		):
			sap.submit_document(
				{
					"connection": connection,
					"document_type": "PurchaseOrder",
					"endpoint_path": "api/purchase-orders",
					"document_payload": {"amount": 100},
					"idempotency_key": _key("sap-submit"),
				}
			)
		with patch(
			"nexora.integrations.sap._open_sap_request",
			side_effect=sap.SapIntegrationError("SAP respondió HTTP 422: dato inválido"),
		):
			sap.submit_document(
				{
					"connection": connection,
					"document_type": "PurchaseOrder",
					"endpoint_path": "api/purchase-orders",
					"document_payload": {"amount": -1},
					"idempotency_key": _key("sap-submit"),
				}
			)
		frappe.set_user(self.admin)
		after = sap.get_sap_summary()
		self.assertEqual(before["total_connections"] + 1, after["total_connections"])
		self.assertEqual(before["documents_submitted"] + 1, after["documents_submitted"])
		self.assertEqual(before["documents_failed"] + 1, after["documents_failed"])
		self.assertIsNotNone(after["last_tested_at"])
		self.assertIsNotNone(after["last_document_event_at"])

	def test_finance_operator_cannot_view_the_summary(self) -> None:
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			sap.get_sap_summary()


class TestListSapEvents(SapIntegrationTestBase):
	"""Bloque de cierre de producción, Paso 2: las pestañas «Documentos»,
	«Errores» y «Auditoría» comparten esta misma lectura real de
	``NXR Audit Event`` — nunca un evento inventado."""

	def _active_connection(self) -> str:
		connection = self._connect()
		with patch("nexora.integrations.sap._open_sap_request", return_value=(200, {"status": "ok"})):
			sap.test_sap_connection({"connection": connection})
		return connection

	def test_administrator_sees_the_real_connection_saved_event(self) -> None:
		connection = self._connect()
		frappe.set_user(self.admin)
		events = sap.list_sap_events({"event_types": ["sap_connection_saved"]})
		matches = [e for e in events if e["connection"] == connection]
		self.assertEqual(1, len(matches))
		self.assertEqual("sap_connection_saved", matches[0]["event_type"])

	def test_a_failed_submission_appears_as_a_real_error_event_with_the_real_detail(self) -> None:
		connection = self._active_connection()
		frappe.set_user(self.manager)
		with patch(
			"nexora.integrations.sap._open_sap_request",
			side_effect=sap.SapIntegrationError("SAP respondió HTTP 422: dato inválido"),
		):
			sap.submit_document(
				{
					"connection": connection,
					"document_type": "PurchaseOrder",
					"endpoint_path": "api/purchase-orders",
					"document_payload": {"amount": -1},
					"idempotency_key": _key("sap-submit"),
				}
			)
		frappe.set_user(self.auditor)
		events = sap.list_sap_events({"event_types": ["sap_document_submission_failed"]})
		matches = [e for e in events if e["connection"] == connection]
		self.assertEqual(1, len(matches))
		self.assertIn("422", matches[0]["detail"].get("error", ""))

	def test_an_unrecognized_event_type_is_dropped_not_treated_as_a_wildcard(self) -> None:
		self._connect()
		frappe.set_user(self.admin)
		events = sap.list_sap_events({"event_types": ["not_a_real_event"]})
		self.assertEqual([], events)

	def test_finance_operator_cannot_list_events(self) -> None:
		self._connect()
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			sap.list_sap_events({})


class TestFieldMapping(SapIntegrationTestBase):
	"""Catálogo real de mapeos de campo (pestaña «Mapeos»): guardar/editar un
	mapeo es configuración pura — nunca llama a SAP — y desactivarlo nunca lo
	borra, para conservar el historial real de qué se mapeó."""

	def _mapping_payload(self, connection: str, **overrides) -> dict:
		return {
			"connection": connection,
			"nexora_object": "NXR Operation",
			"sap_object": "BAPI_ACC_DOCUMENT_POST",
			"source_field": "amount",
			"target_field": "WRBTR",
			"idempotency_key": _key("sap-mapping"),
			**overrides,
		}

	def test_administrator_can_create_a_mapping(self) -> None:
		connection = self._connect()
		mapping = sap.create_field_mapping(self._mapping_payload(connection))
		self.assertTrue(frappe.db.exists("NXR SAP Field Mapping", mapping["mapping"]))
		self.assertEqual(1, mapping["version"])
		self.assertTrue(mapping["active"])
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "sap_mapping_saved",
					"reference_doctype": "NXR SAP Field Mapping",
					"reference_name": mapping["mapping"],
				},
			)
		)

	def test_finance_manager_cannot_create_a_mapping(self) -> None:
		connection = self._connect()
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			sap.create_field_mapping(self._mapping_payload(connection))

	def test_finance_operator_cannot_create_a_mapping(self) -> None:
		connection = self._connect()
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			sap.create_field_mapping(self._mapping_payload(connection))

	def test_create_mapping_never_calls_sap(self) -> None:
		connection = self._connect()
		with patch("nexora.integrations.sap._open_sap_request") as mocked:
			sap.create_field_mapping(self._mapping_payload(connection))
		mocked.assert_not_called()

	def test_mapping_requires_an_existing_connection(self) -> None:
		with self.assertRaises(frappe.ValidationError):
			sap.create_field_mapping(self._mapping_payload("_Test SAP Connection Not Real"))

	def test_updating_a_substantive_field_increments_the_version(self) -> None:
		connection = self._connect()
		mapping = sap.create_field_mapping(self._mapping_payload(connection))
		updated = sap.update_field_mapping(
			{"mapping": mapping["mapping"], "target_field": "DMBTR", "idempotency_key": _key("sap-mapping")}
		)
		self.assertEqual(2, updated["version"])
		self.assertEqual("DMBTR", updated["target_field"])
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "sap_mapping_saved",
					"reference_doctype": "NXR SAP Field Mapping",
					"reference_name": mapping["mapping"],
				},
			)
		)

	def test_updating_with_no_real_change_does_not_bump_the_version(self) -> None:
		connection = self._connect()
		mapping = sap.create_field_mapping(self._mapping_payload(connection))
		updated = sap.update_field_mapping(
			{
				"mapping": mapping["mapping"],
				"target_field": mapping["target_field"],
				"idempotency_key": _key("sap-mapping"),
			}
		)
		self.assertEqual(1, updated["version"])

	def test_finance_manager_cannot_update_a_mapping(self) -> None:
		connection = self._connect()
		mapping = sap.create_field_mapping(self._mapping_payload(connection))
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			sap.update_field_mapping({"mapping": mapping["mapping"], "target_field": "DMBTR"})

	def test_deactivating_a_mapping_sets_active_false_and_is_never_a_delete(self) -> None:
		connection = self._connect()
		mapping = sap.create_field_mapping(self._mapping_payload(connection))
		result = sap.deactivate_field_mapping({"mapping": mapping["mapping"]})
		self.assertFalse(result["active"])
		self.assertTrue(frappe.db.exists("NXR SAP Field Mapping", mapping["mapping"]))
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("NXR SAP Field Mapping", mapping["mapping"], ignore_permissions=True)
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{
					"event_type": "sap_mapping_deactivated",
					"reference_doctype": "NXR SAP Field Mapping",
					"reference_name": mapping["mapping"],
				},
			)
		)

	def test_finance_operator_cannot_deactivate_a_mapping(self) -> None:
		connection = self._connect()
		mapping = sap.create_field_mapping(self._mapping_payload(connection))
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			sap.deactivate_field_mapping({"mapping": mapping["mapping"]})

	def test_auditor_can_list_mappings_and_filter_by_connection_and_active(self) -> None:
		connection_a = self._connect()
		connection_b = self._connect()
		mapping_a = sap.create_field_mapping(self._mapping_payload(connection_a))
		mapping_b = sap.create_field_mapping(self._mapping_payload(connection_b))
		sap.deactivate_field_mapping({"mapping": mapping_b["mapping"]})

		frappe.set_user(self.auditor)
		by_connection = sap.list_field_mappings({"connection": connection_a})
		names = {row["name"] for row in by_connection}
		self.assertIn(mapping_a["mapping"], names)
		self.assertNotIn(mapping_b["mapping"], names)

		active_only = sap.list_field_mappings({"active": True})
		active_names = {row["name"] for row in active_only}
		self.assertIn(mapping_a["mapping"], active_names)
		self.assertNotIn(mapping_b["mapping"], active_names)

	def test_finance_operator_cannot_list_mappings(self) -> None:
		connection = self._connect()
		sap.create_field_mapping(self._mapping_payload(connection))
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			sap.list_field_mappings({})
