from __future__ import annotations

import uuid
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.integrations.service import register_integration, test_connection


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


class TestIntegrationTestConnectionMariaDB(FrappeTestCase):
	"""NXR-INT-0007: la prueba de conexión debe reflejar un resultado real.

	Requiere bench + MariaDB reales; no se pudo ejecutar en el entorno de esta sesión
	(sin bench/Frappe/MariaDB). El chequeo HTTP en sí (``check_endpoint_connectivity``)
	ya está probado por unidad sin red real en ``test_integrations_connectivity.py``;
	aquí se mockea deliberadamente para aislar lo que sí depende de Frappe: el
	registro, el guardado del resultado y el log de la integración.
	"""

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:8]
		cls.manager = _ensure_user(f"nxr-integration-manager-{marker}@example.test", "NEXORA Finance Manager")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _register(self, *, endpoint_url: str | None) -> str:
		frappe.set_user(self.manager)
		result = register_integration(
			{
				"integration_name": f"_Test Integration {uuid.uuid4().hex[:8]}",
				"endpoint_url": endpoint_url,
				"idempotency_key": _key("integration"),
			}
		)
		return result["integration"]

	def test_without_endpoint_url_is_rejected_and_result_is_untouched(self) -> None:
		integration = self._register(endpoint_url=None)
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.ValidationError):
			test_connection({"integration": integration})
		doc = frappe.get_doc("NXR Integration", integration)
		self.assertEqual("Not Tested", doc.last_test_result)
		self.assertEqual(0, len(doc.logs))

	def test_records_a_real_success_result_and_logs_it(self) -> None:
		integration = self._register(endpoint_url="https://example.invalid/health")
		frappe.set_user(self.manager)
		with mock.patch(
			"nexora.integrations.service.check_endpoint_connectivity",
			return_value={
				"reachable": True,
				"ok": True,
				"status_code": 200,
				"elapsed_ms": 12,
				"detail": "HTTP 200 en 12 ms",
			},
		):
			result = test_connection({"integration": integration})
		self.assertEqual("Success", result["last_test_result"])
		doc = frappe.get_doc("NXR Integration", integration)
		self.assertEqual("Success", doc.last_test_result)
		self.assertIsNotNone(doc.last_test_at)
		self.assertEqual(1, len(doc.logs))
		self.assertEqual("Info", doc.logs[0].level)
		self.assertIn("200", doc.logs[0].message)

	def test_records_a_real_failure_result_and_logs_it(self) -> None:
		integration = self._register(endpoint_url="https://example.invalid/health")
		frappe.set_user(self.manager)
		with mock.patch(
			"nexora.integrations.service.check_endpoint_connectivity",
			return_value={
				"reachable": False,
				"ok": False,
				"status_code": None,
				"elapsed_ms": 10000,
				"detail": "Tiempo de espera agotado tras 10s",
			},
		):
			result = test_connection({"integration": integration})
		self.assertEqual("Failure", result["last_test_result"])
		doc = frappe.get_doc("NXR Integration", integration)
		self.assertEqual("Failure", doc.last_test_result)
		self.assertEqual(1, len(doc.logs))
		self.assertEqual("Error", doc.logs[0].level)
		self.assertIn("agotado", doc.logs[0].message)

	def test_a_4xx_response_is_reachable_but_recorded_as_failure(self) -> None:
		# Regresión directa de NXR-INT-0007: antes de esta corrección, este caso se
		# habría grabado como "Success" sin haber verificado nada.
		integration = self._register(endpoint_url="https://example.invalid/health")
		frappe.set_user(self.manager)
		with mock.patch(
			"nexora.integrations.service.check_endpoint_connectivity",
			return_value={
				"reachable": True,
				"ok": False,
				"status_code": 404,
				"elapsed_ms": 8,
				"detail": "HTTP 404 en 8 ms",
			},
		):
			result = test_connection({"integration": integration})
		self.assertEqual("Failure", result["last_test_result"])
		self.assertEqual(404, result["status_code"])
