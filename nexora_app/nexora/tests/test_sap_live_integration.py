"""Cierre definitivo del bloque SAP: llamada real y viva contra el SAP
Business Accelerator Hub Sandbox, ejercida a través del propio camino real
de NEXORA — nunca un script externo al margen del adaptador.

Requiere bench + MariaDB reales, más la credencial real del usuario
(``SAP_SANDBOX_API_KEY``) — la misma API Key que el Bloque 188 ya probó de
forma manual con un script de un solo uso, ahora fijada como secreto de
GitHub Actions. Sin esa variable, la clase completa se salta — mismo
principio que ``test_intelligence_live_integration.py`` con
``OPENAI_API_KEY``: ninguna otra prueba de este repositorio hace una llamada
de red real contra SAP, así que esta es deliberadamente la única.

Recorre el flujo completo exigido por el cierre del bloque SAP dentro del
propio código de producción (``nexora.integrations.sap``), sin ningún doble
de prueba de red: ``connect_connection`` (Configuración → guardada como
Inactive) → ``test_sap_connection`` (Probar conexión → llamada HTTP real,
GET real contra ``API_BUSINESS_PARTNER``, la misma API y el mismo método que
el Bloque 188 confirmó con evidencia real: HTTP 200 con cuerpo JSON real) →
estado Active real → ``list_connections``/``get_sap_summary`` (Conexiones/
Salud/Resumen reales) → ``list_sap_events`` (Auditoría real).
"""

from __future__ import annotations

import os
import unittest
import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.integrations import sap

_SAP_SANDBOX_API_KEY = os.getenv("SAP_SANDBOX_API_KEY", "").strip()
_HAS_LIVE_CREDENTIAL = bool(_SAP_SANDBOX_API_KEY)

# Misma API real (Business Partner, A2X) y la misma URL real que el Bloque 188
# confirmó con evidencia HTTP real: GET -> HTTP 200 con cuerpo JSON real de SAP.
_SAP_SANDBOX_BASE_URL = "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_BUSINESS_PARTNER"


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


@unittest.skipUnless(
	_HAS_LIVE_CREDENTIAL,
	"SAP_SANDBOX_API_KEY no está configurada en este entorno — sin credencial real, esta clase no "
	"puede ejercer el cierre definitivo del bloque SAP contra el SAP Business Accelerator Hub "
	"Sandbox vivo.",
)
class TestSapLiveSandboxIntegration(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:8]
		cls.admin = _ensure_user(f"nxr-sap-live-admin-{marker}@example.test", "NEXORA Administrator")
		cls.connection_name = f"E2E SAP Sandbox Live {marker}"

	def setUp(self) -> None:
		frappe.set_user(self.admin)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def test_the_full_configuration_to_audit_flow_is_real_end_to_end(self) -> None:
		"""Configuración -> Inactive -> Probar conexión (HTTP real) -> Active ->
		Resumen/Salud/Auditoría reales, todo a través del adaptador real, sin
		ningún doble de prueba de red."""
		saved = sap.connect_connection(
			{
				"connection_name": self.connection_name,
				"base_url": _SAP_SANDBOX_BASE_URL,
				"auth_type": "API Key",
				"api_key": _SAP_SANDBOX_API_KEY,
				"environment": "Sandbox",
			}
		)
		connection = saved["connection"]
		self.assertEqual("Inactive", saved["status"])
		self.assertEqual("Sandbox", saved["environment"])

		# Configuración/Conexiones: la API Key nunca vuelve en list_connections.
		listed = {row["name"]: row for row in sap.list_connections({})}
		self.assertIn(connection, listed)
		self.assertNotIn("api_key", listed[connection])

		# Probar conexión: llamada HTTP REAL contra el SAP Sandbox real.
		tested = sap.test_sap_connection({"connection": connection})
		self.assertEqual("Success", tested["last_test_result"])

		doc = frappe.get_doc("NXR SAP Connection", connection)
		self.assertEqual("Active", doc.status)
		self.assertIsNotNone(doc.last_test_at)

		# Salud: la misma tabla real de conexiones ya refleja el estado probado.
		listed_after = {row["name"]: row for row in sap.list_connections({})}
		self.assertEqual("Active", listed_after[connection]["status"])
		self.assertEqual("Success", listed_after[connection]["last_test_result"])

		# Resumen: agregados reales reflejan la conexión recién probada.
		summary = sap.get_sap_summary()
		self.assertGreaterEqual(summary["connections_by_status"].get("Active", 0), 1)
		active = summary["active_connection"]
		self.assertIsNotNone(active)
		self.assertEqual(connection, active["name"])

		# Auditoría: connect_connection y test_sap_connection dejaron eventos
		# reales en NXR Audit Event -- ninguno inventado por esta prueba.
		events = sap.list_sap_events({"event_types": ["sap_connection_saved", "sap_connection_tested"]})
		event_types = {event["event_type"] for event in events if event["connection"] == connection}
		self.assertEqual({"sap_connection_saved", "sap_connection_tested"}, event_types)

	def test_a_wrong_api_key_is_a_real_rejection_never_a_silent_success(self) -> None:
		"""Prueba negativa real: una API Key incorrecta debe recibir un rechazo
		real de SAP (nunca un éxito simulado ni un estado Active falso)."""
		wrong_connection_name = f"{self.connection_name} (wrong key)"
		saved = sap.connect_connection(
			{
				"connection_name": wrong_connection_name,
				"base_url": _SAP_SANDBOX_BASE_URL,
				"auth_type": "API Key",
				"api_key": f"wrong-{uuid.uuid4().hex}",
				"environment": "Sandbox",
			}
		)
		connection = saved["connection"]
		tested = sap.test_sap_connection({"connection": connection})
		self.assertEqual("Failure", tested["last_test_result"])

		doc = frappe.get_doc("NXR SAP Connection", connection)
		self.assertEqual("Inactive", doc.status)
		self.assertEqual("Failure", doc.last_test_result)


if __name__ == "__main__":
	unittest.main()
