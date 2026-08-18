"""Bloque 72: aplicación real de permisos server-side sobre `intelligence.service`.

Barrido de seguridad (mandato MASTER BLOCK 3, §35): cada dominio con
`require_action`/`require_project_access` debe tener al menos una prueba
negativa (rol incorrecto -> `frappe.PermissionError`) ejecutada de verdad
contra Frappe, no solo un `assertIn` sobre el texto fuente. `intelligence.
service` administra proveedores de IA y, sobre todo, sus credenciales
(`ai_manage_credential` -> solo `ADMINISTRATOR_ONLY_ROLES`) y no tenía
ninguna prueba de este tipo: `test_intelligence_contract.py` solo confirma
que el mapeo `ACTION_ROLES` existe en el código fuente, nunca ejercita la
función como un usuario sin ese rol.

Este archivo no repite lo que `test_intelligence_contract.py` ya cubre
(forma de las funciones, mapeo declarado) ni lo que los tests con stub de
`test_intelligence_live_integration.py` cubren (comportamiento del
gateway/orchestrator con proveedores reales). Cubre exclusivamente la
frontera de autorización: quién puede y quién no puede llamar cada acción,
contra un usuario y roles reales en MariaDB.
"""

from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.intelligence import service


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
	elif not frappe.db.exists("Has Role", {"parent": email, "role": role}):
		user = frappe.get_doc("User", email)
		user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
	return email


def _provider_key() -> str:
	return f"nxr-test-{uuid.uuid4().hex[:12]}"


class TestIntelligencePermissionEnforcementMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:8]
		cls.manager = _ensure_user(f"nxr-ai-manager-{marker}@example.test", "NEXORA Finance Manager")
		cls.operator = _ensure_user(f"nxr-ai-operator-{marker}@example.test", "NEXORA Finance Operator")
		cls.administrator = _ensure_user(f"nxr-ai-admin-{marker}@example.test", "NEXORA Administrator")
		cls.auditor = _ensure_user(f"nxr-ai-auditor-{marker}@example.test", "NEXORA Auditor")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _register(self, provider_key: str) -> None:
		frappe.set_user(self.manager)
		service.register_provider(
			{
				"provider_key": provider_key,
				"display_name": "Proveedor de prueba",
				"capabilities": "text",
			}
		)

	# --- ai_manage_provider (MANAGER_ROLES) ---------------------------------

	def test_operator_cannot_register_a_provider(self) -> None:
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			service.register_provider(
				{"provider_key": _provider_key(), "display_name": "X", "capabilities": "text"}
			)

	def test_manager_can_register_a_provider(self) -> None:
		provider_key = _provider_key()
		self._register(provider_key)
		self.assertTrue(frappe.db.exists("NXR AI Provider", {"provider_key": provider_key}))

	# --- ai_view_provider (REPORT_EXPORT_ROLES) -----------------------------

	def test_operator_cannot_list_providers(self) -> None:
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			service.list_providers({})

	def test_auditor_can_list_providers(self) -> None:
		frappe.set_user(self.auditor)
		# No debe lanzar PermissionError: Auditor está en REPORT_EXPORT_ROLES
		# aunque no esté en MANAGER_ROLES (no puede registrar, sí puede ver).
		result = service.list_providers({})
		self.assertIsInstance(result, list)

	# --- ai_manage_credential (ADMINISTRATOR_ONLY_ROLES) --------------------
	#
	# La comprobación más importante de este archivo: un Gerente Financiero
	# puede administrar proveedores (ai_manage_provider) pero NO puede
	# guardar su credencial — segregación explícita del Capítulo 34/36 que,
	# sin esta prueba, solo estaba documentada en `permissions.py`, nunca
	# demostrada en ejecución.

	def test_finance_manager_cannot_save_a_credential_even_though_they_manage_providers(self) -> None:
		provider_key = _provider_key()
		self._register(provider_key)
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			service.save_credential({"provider_key": provider_key, "secret": f"sk-{uuid.uuid4().hex}"})

	def test_operator_cannot_save_a_credential(self) -> None:
		provider_key = _provider_key()
		self._register(provider_key)
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			service.save_credential({"provider_key": provider_key, "secret": f"sk-{uuid.uuid4().hex}"})

	def test_nexora_administrator_can_save_a_credential(self) -> None:
		provider_key = _provider_key()
		self._register(provider_key)
		frappe.set_user(self.administrator)
		result = service.save_credential({"provider_key": provider_key, "secret": f"sk-{uuid.uuid4().hex}"})
		self.assertEqual("Format Valid", result["validation_state"])

	# --- ai_test_connection (MANAGER_ROLES) ---------------------------------
	#
	# `test_provider_connection` puede alcanzar la red real para un
	# proveedor configurado; para no depender de un servicio externo desde
	# esta prueba, se comprueba solo con una clave inexistente. El propio
	# `require_action` corre antes que cualquier otra cosa en la función, así
	# que el rol equivocado debe fallar con `PermissionError` sin llegar
	# nunca a intentar construir el adaptador ni a tocar la red.

	def test_operator_cannot_test_a_provider_connection(self) -> None:
		frappe.set_user(self.operator)
		with self.assertRaises(frappe.PermissionError):
			service.test_provider_connection({"provider_key": _provider_key()})

	def test_manager_passes_the_permission_gate_for_test_connection(self) -> None:
		frappe.set_user(self.manager)
		# Con rol correcto, el gate de permisos se supera. `test_provider_
		# connection` atrapa internamente el `ProviderNotFoundError` de
		# `build_ready_adapter` para auditar el intento fallido, pero para
		# hacerlo llama a `_require_existing_provider`, que a su vez lanza
		# `frappe.DoesNotExistError` — ese es el error real que sale de la
		# función para una clave inexistente, nunca `PermissionError`. Lo
		# importante para esta prueba no es esa cadena, sino que el rol
		# correcto llegó hasta ahí sin ser rechazado por permisos.
		with self.assertRaises(frappe.DoesNotExistError):
			service.test_provider_connection({"provider_key": _provider_key()})
