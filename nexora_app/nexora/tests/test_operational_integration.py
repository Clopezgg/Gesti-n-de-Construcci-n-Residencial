from __future__ import annotations

import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.context import service_write

test_dependencies = ["Project", "Cost Center"]

from nexora.financial.operational import (
	execute_operational_movement,
	list_financial_accounts,
	list_operational_ledger,
	preview_operational_movement,
)


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
	elif not frappe.db.exists("Has Role", {"parent": email, "role": role}):
		user = frappe.get_doc("User", email)
		user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
	return email


def _ensure_project(name: str) -> str:
	existing = frappe.db.get_value("Project", {"project_name": name}, "name")
	if existing:
		return str(existing)
	return str(
		frappe.get_doc({"doctype": "Project", "project_name": name, "status": "Open"})
		.insert(ignore_permissions=True)
		.name
	)


class TestOperationalConsoleMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project(f"_Test Operational {uuid.uuid4().hex[:8]}")
		cls.operator = _ensure_user("nxr-operational@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-operational-manager@example.test", "NEXORA Finance Manager")
		cls.auditor = _ensure_user("nxr-operational-auditor@example.test", "NEXORA Auditor")
		cls.cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")
		if not cls.cost_center:
			raise AssertionError("Cost Center test dependency did not create a leaf cost center")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _date(self, days: int) -> str:
		return str(frappe.utils.add_days(frappe.utils.today(), days))

	def _income_payload(self, *, date: str, amount: int = 1000) -> dict[str, object]:
		return {
			"movement_code": "101",
			"document_date": date,
			"project": self.project,
			"account_mode": "New",
			"channel": "Remittance",
			"currency": "HNL",
			"original_amount": amount,
			"exchange_rate": 1,
			"origin_or_sender": "Karen Vanessa López González",
			"institution": "Banco Atlántida",
			"account_reference": "2020665852",
			"external_reference": f"REF-{uuid.uuid4().hex[:8]}",
			"save_financial_account": 1,
			"account_name": "Cuenta personal Karen",
		}

	def _ensure_entity(self) -> str:
		"""Un beneficiario como el que ofrece el selector: entidad activa del directorio."""
		from nexora.directory.service import create_entity, transition_entity

		frappe.set_user("Administrator")
		key = _key("op-entity")
		entity = create_entity(
			{
				"idempotency_key": key,
				"entity_type": "Organization",
				"display_name": f"Proveedor operativo {key[-8:]}",
				"contacts": [{"contact_type": "Email", "contact_value": f"{key[-8:]}@example.test"}],
			}
		)["name"]
		transition_entity(entity, "Active", f"{key}-active")
		return str(entity)

	def _execute_income(self, *, date: str, amount: int = 1000) -> dict[str, object]:
		frappe.set_user(self.operator)
		payload = self._income_payload(date=date, amount=amount)
		preview = preview_operational_movement(payload)
		return execute_operational_movement(
			{**payload, "preview_hash": preview["preview_hash"], "idempotency_key": _key("op-income")}
		)

	def _create_saved_account(
		self,
		*,
		project: str | None = None,
		currency: str = "HNL",
		active: int = 1,
	) -> str:
		frappe.set_user("Administrator")
		with service_write():
			account = frappe.get_doc(
				{
					"doctype": "NXR Financial Account",
					"account_name": f"Cuenta de prueba {uuid.uuid4().hex[:8]}",
					"active": active,
					"project": project if project is not None else self.project,
					"direction": "Origin",
					"origin_or_sender": "Karen Vanessa López González",
					"institution": "Banco Atlántida",
					"account_reference": uuid.uuid4().hex[:12],
					"currency": currency,
					"default_channel": "Remittance",
					"account_fingerprint": uuid.uuid4().hex,
				}
			).insert(ignore_permissions=True)
		return str(account.name)

	def test_historical_income_uses_document_date_and_reuses_account(self) -> None:
		document_date = self._date(-30)
		first = self._execute_income(date=document_date)
		self.assertEqual(
			document_date, str(frappe.db.get_value("NXR Fund Source", first["fund_source"], "source_date"))
		)
		self.assertEqual(
			document_date, str(frappe.db.get_value("NXR Operation", first["operation"], "operation_date"))
		)
		self.assertEqual(
			"101",
			frappe.db.get_value("NXR Operation Metadata", {"operation": first["operation"]}, "movement_code"),
		)
		accounts = list_financial_accounts(self.project)
		account = next(row for row in accounts if row["account_name"] == "Cuenta personal Karen")
		self.assertEqual("••••65852", account["masked_account_reference"])
		fingerprint = frappe.db.get_value("NXR Financial Account", account["name"], "account_fingerprint")
		self.assertEqual(1, frappe.db.count("NXR Financial Account", {"account_fingerprint": fingerprint}))

		payload = {
			"movement_code": "101",
			"document_date": self._date(-29),
			"project": self.project,
			"account_mode": "Existing",
			"financial_account": account["name"],
			"original_amount": 250,
			"exchange_rate": 1,
			"external_reference": f"REF-{uuid.uuid4().hex[:8]}",
		}
		preview = preview_operational_movement(payload)
		second = execute_operational_movement(
			{**payload, "preview_hash": preview["preview_hash"], "idempotency_key": _key("op-income-reuse")}
		)
		self.assertEqual(
			"Banco Atlántida", frappe.db.get_value("NXR Fund Source", second["fund_source"], "institution")
		)
		self.assertEqual(1, frappe.db.count("NXR Financial Account", {"account_fingerprint": fingerprint}))

	def test_new_mode_ignores_stale_autocomplete_text_and_creates_account(self) -> None:
		frappe.set_user(self.operator)
		payload = {
			**self._income_payload(date=self._date(-8), amount=725),
			"financial_account": "Cuenta escrita que todavía no existe",
			"account_name": f"Cuenta nueva {uuid.uuid4().hex[:8]}",
		}
		preview = preview_operational_movement(payload)
		result = execute_operational_movement(
			{**payload, "preview_hash": preview["preview_hash"], "idempotency_key": _key("op-new-account")}
		)
		self.assertTrue(result["financial_account"])
		self.assertTrue(frappe.db.exists("NXR Financial Account", result["financial_account"]))
		self.assertEqual("New", result["account_mode"])

	def test_existing_mode_rejects_missing_account_selection(self) -> None:
		frappe.set_user(self.operator)
		payload = {
			**self._income_payload(date=self._date(-7), amount=300),
			"account_mode": "Existing",
			"financial_account": "",
			"save_financial_account": 0,
		}
		with self.assertRaisesRegex(frappe.ValidationError, "Seleccione una cuenta guardada"):
			preview_operational_movement(payload)

	def test_existing_mode_rejects_unknown_account_with_actionable_message(self) -> None:
		frappe.set_user(self.operator)
		payload = {
			**self._income_payload(date=self._date(-7), amount=300),
			"account_mode": "Existing",
			"financial_account": "NXR-ACCOUNT-DOES-NOT-EXIST",
			"save_financial_account": 0,
		}
		with self.assertRaisesRegex(frappe.ValidationError, "La cuenta guardada no existe"):
			preview_operational_movement(payload)

	def test_existing_mode_rejects_account_without_read_permission(self) -> None:
		account = self._create_saved_account()
		frappe.set_user(self.operator)
		payload = {
			**self._income_payload(date=self._date(-7), amount=300),
			"account_mode": "Existing",
			"financial_account": account,
			"save_financial_account": 0,
		}
		with (
			patch("frappe.has_permission", return_value=False),
			self.assertRaisesRegex(frappe.PermissionError, "No tiene permiso para utilizar"),
		):
			preview_operational_movement(payload)

	def test_existing_mode_rejects_account_from_another_project(self) -> None:
		other_project = _ensure_project(f"_Test Other Project {uuid.uuid4().hex[:8]}")
		account = self._create_saved_account(project=other_project)
		frappe.set_user(self.operator)
		payload = {
			**self._income_payload(date=self._date(-7), amount=300),
			"account_mode": "Existing",
			"financial_account": account,
			"save_financial_account": 0,
		}
		with self.assertRaisesRegex(frappe.PermissionError, "no pertenece al proyecto"):
			preview_operational_movement(payload)

	def test_existing_mode_rejects_account_with_incompatible_currency(self) -> None:
		account = self._create_saved_account(currency="USD")
		frappe.set_user(self.operator)
		payload = {
			**self._income_payload(date=self._date(-7), amount=300),
			"account_mode": "Existing",
			"financial_account": account,
			"save_financial_account": 0,
		}
		with self.assertRaisesRegex(frappe.ValidationError, "no es compatible con la moneda"):
			preview_operational_movement(payload)

	def test_future_and_closed_period_dates_are_rejected(self) -> None:
		frappe.set_user(self.operator)
		missing_date = self._income_payload(date=self._date(-1))
		missing_date.pop("document_date")
		with self.assertRaisesRegex(frappe.ValidationError, "obligatoria"):
			preview_operational_movement(missing_date)
		with self.assertRaisesRegex(frappe.ValidationError, "futuro"):
			preview_operational_movement(self._income_payload(date=self._date(1)))

		closed_date = self._date(-65)
		month = frappe.utils.getdate(closed_date).strftime("%Y-%m")
		frappe.set_user("Administrator")
		with service_write():
			frappe.get_doc(
				{
					"doctype": "NXR Monthly Close",
					"status": "Approved",
					"project": self.project,
					"close_month": month,
					"close_date": closed_date,
					"total_inflows_hnl": 0,
					"total_outflows_hnl": 0,
				}
			).insert(ignore_permissions=True)
		frappe.set_user(self.operator)
		with self.assertRaisesRegex(frappe.ValidationError, "cerrado"):
			preview_operational_movement(self._income_payload(date=closed_date))

	def test_guided_expense_102_accepts_the_payload_the_console_really_sends(self) -> None:
		"""La consola guiada envía `beneficiary_doctype: "NXR Entity"`, medio de pago
		en efectivo, modo de cuenta Manual y sin solicitante ni aprobador explícitos
		—esos campos no son obligatorios para el gasto—. Ningún caso cubría esa
		combinación: los existentes usan un `User` como beneficiario y nombran a dos
		actores distintos. El recorrido de navegador falla justo aquí, así que la
		combinación real del usuario tiene que estar probada en runtime."""
		income = self._execute_income(date=self._date(-3), amount=1500)
		beneficiary = self._ensure_entity()
		# `payload()` serializa SIEMPRE todos los campos, incluidos los que el gasto
		# oculta: `channel` conserva el «Remittance» con el que arranca la pantalla y
		# `exchange_rate` su 1. Omitirlos aquí dejaría fuera justo la clase de residuo
		# que rompía el gasto —un `account_mode` oculto en «New»—, que es lo que este
		# caso debe vigilar.
		payload = {
			"movement_code": "102",
			"document_date": self._date(0),
			"project": self.project,
			"account_mode": "Manual",
			"financial_account": "",
			"save_financial_account": 0,
			"account_name": "",
			"channel": "Remittance",
			"currency": "HNL",
			"original_amount": "",
			"exchange_rate": 1,
			"origin_or_sender": "",
			"institution": "",
			"account_reference": "",
			"external_reference": "",
			"economic_category": "CONSTRUCTION_MATERIALS",
			"amount_hnl": 75.25,
			"cost_center": self.cost_center,
			"analytic_splits": [{"cost_center": self.cost_center, "amount_hnl": 75.25}],
			"beneficiary_doctype": "NXR Entity",
			"beneficiary": beneficiary,
			"payment_method": "Cash",
			"reference_name": "",
			"description": "Pago guiado navegador",
			"reason": "Pago guiado navegador",
			"evidence": "",
			"requester": "",
			"approved_by": "",
			"allocations": [{"source": income["fund_source"], "amount_hnl": 75.25}],
		}
		frappe.set_user(self.operator)
		preview = preview_operational_movement(payload)
		self.assertEqual("102", preview["movement_code"])
		self.assertEqual(beneficiary, preview["counterparty"])
		result = execute_operational_movement(
			{
				**payload,
				"preview_hash": preview["preview_hash"],
				"idempotency_key": _key("op-guided-expense"),
			}
		)
		self.assertRegex(str(result["document_number"]), r"^\d{12}$")
		self.assertEqual(
			("NXR Entity", beneficiary),
			tuple(
				frappe.db.get_value(
					"NXR Operation", result["operation"], ["beneficiary_doctype", "beneficiary"]
				)
			),
		)
		# Reintento idéntico: un doble clic, un corte de red o una reconexión del móvil
		# repiten la misma petición. Debe devolver el documento original, no rechazarla.
		# El envoltorio operativo revalidaba la vista previa antes de delegar, y como la
		# propia ejecución ya había movido los saldos el hash nunca volvía a coincidir:
		# todo reintento moría con «la vista previa está vencida», empujando al usuario a
		# capturar el gasto por segunda vez.
		replay = execute_operational_movement(
			{
				**payload,
				"preview_hash": preview["preview_hash"],
				"idempotency_key": _key("op-guided-expense"),
			}
		)
		self.assertEqual(result["document_number"], replay["document_number"])
		self.assertEqual(result["operation"], replay["operation"])
		self.assertEqual("102", replay["movement_code"])
		self.assertEqual(
			1,
			frappe.db.count("NXR Operation", {"document_number": result["document_number"]}),
			"el reintento creó un segundo documento",
		)
		frappe.set_user("Administrator")

	def test_historical_expense_102_uses_selected_date_and_canonical_allocations(self) -> None:
		income = self._execute_income(date=self._date(-12), amount=1500)
		document_date = self._date(-11)
		payload = {
			"movement_code": "102",
			"document_date": document_date,
			"project": self.project,
			"economic_category": "CONSTRUCTION_MATERIALS",
			"amount_hnl": 400,
			"cost_center": self.cost_center,
			"analytic_splits": [
				{
					"cost_center": self.cost_center,
					"amount_hnl": 400,
				}
			],
			"beneficiary_doctype": "User",
			"beneficiary": self.operator,
			"payment_method": "Transfer",
			"external_reference": f"PAY-{uuid.uuid4().hex[:8]}",
			"description": "Pago de materiales registrado con fecha documental histórica",
			"evidence": "/private/files/pago-materiales.pdf",
			"requester": self.operator,
			"approved_by": self.manager,
			"allocations": [{"source": income["fund_source"], "amount_hnl": 400}],
		}
		frappe.set_user(self.operator)
		preview = preview_operational_movement(payload)
		result = execute_operational_movement(
			{**payload, "preview_hash": preview["preview_hash"], "idempotency_key": _key("op-expense")}
		)
		self.assertEqual(
			document_date, str(frappe.db.get_value("NXR Operation", result["operation"], "operation_date"))
		)
		self.assertEqual(
			"102",
			frappe.db.get_value(
				"NXR Operation Metadata", {"operation": result["operation"]}, "movement_code"
			),
		)
		ledger = list_operational_ledger(self.project, 20)
		row = next(item for item in ledger if item["name"] == result["operation"])
		self.assertEqual(("102", "expense", False), (row["movement_code"], row["tone"], row["struck"]))
		self.assertEqual(self.operator, row["counterparty"])

		frappe.set_user("Administrator")
		correction = {
			"movement_code": "303",
			"document_date": document_date,
			"project": self.project,
			"reference_name": result["operation"],
			"description": "Anulación controlada del gasto registrado en integración.",
			"requester": self.operator,
			"approved_by": self.manager,
		}
		correction_preview = preview_operational_movement(correction)
		corrected = execute_operational_movement(
			{
				**correction,
				"preview_hash": correction_preview["preview_hash"],
				"idempotency_key": _key("op-expense-correction"),
			}
		)
		self.assertRegex(str(corrected["document_number"]), r"^\d{12}$")
		self.assertEqual(
			"Compensated Total",
			frappe.db.get_value("NXR Operation", result["operation"], "status"),
		)
		self.assertEqual(
			400,
			frappe.db.get_value("NXR Operation", result["operation"], "amount_hnl"),
		)

	def test_correction_failure_rolls_back_original_status(self) -> None:
		income = self._execute_income(date=self._date(-10), amount=900)
		expense = {
			"movement_code": "102",
			"document_date": self._date(-9),
			"project": self.project,
			"economic_category": "CONSTRUCTION_MATERIALS",
			"amount_hnl": 300,
			"cost_center": self.cost_center,
			"beneficiary_doctype": "User",
			"beneficiary": self.operator,
			"payment_method": "Cash",
			"description": "Gasto para validar rollback de corrección.",
			"requester": self.operator,
			"approved_by": self.manager,
			"allocations": [{"source": income["fund_source"], "amount_hnl": 300}],
		}
		frappe.set_user(self.operator)
		expense_preview = preview_operational_movement(expense)
		created = execute_operational_movement(
			{
				**expense,
				"preview_hash": expense_preview["preview_hash"],
				"idempotency_key": _key("op-expense-rollback"),
			}
		)
		frappe.set_user("Administrator")
		correction = {
			"movement_code": "303",
			"document_date": self._date(-8),
			"project": self.project,
			"reference_name": created["operation"],
			"description": "Corrección que debe revertirse por fallo inyectado.",
			"requester": self.operator,
			"approved_by": self.manager,
		}
		preview = preview_operational_movement(correction)
		before = frappe.db.count("NXR Operation")
		with (
			patch("nexora.financial.operations.audit", side_effect=RuntimeError("fallo inyectado")),
			self.assertRaisesRegex(RuntimeError, "fallo inyectado"),
		):
			execute_operational_movement(
				{
					**correction,
					"preview_hash": preview["preview_hash"],
					"idempotency_key": _key("op-correction-rollback"),
				}
			)
		self.assertEqual("Executed", frappe.db.get_value("NXR Operation", created["operation"], "status"))
		self.assertEqual(before, frappe.db.count("NXR Operation"))

	def test_income_annulment_preserves_original_and_uses_selected_date(self) -> None:
		original_date = self._date(-20)
		income = self._execute_income(date=original_date)
		frappe.set_user(self.manager)
		other_project = _ensure_project(f"_Test Other Operational {uuid.uuid4().hex[:8]}")
		with self.assertRaisesRegex(frappe.ValidationError, "proyecto del documento original"):
			preview_operational_movement(
				{
					"movement_code": "303",
					"document_date": self._date(-19),
					"project": other_project,
					"reference_name": income["operation"],
					"description": "Anulación por referencia incorrecta",
				}
			)
		with self.assertRaisesRegex(frappe.ValidationError, "anterior"):
			preview_operational_movement(
				{
					"movement_code": "303",
					"document_date": self._date(-21),
					"project": self.project,
					"reference_name": income["operation"],
					"description": "Anulación por referencia incorrecta",
				}
			)
		payload = {
			"movement_code": "303",
			"document_date": self._date(-19),
			"project": self.project,
			"reference_name": income["operation"],
			"description": "Anulación por referencia incorrecta",
		}
		preview = preview_operational_movement(payload)
		result = execute_operational_movement(
			{**payload, "preview_hash": preview["preview_hash"], "idempotency_key": _key("op-cancel")}
		)
		self.assertTrue(frappe.db.exists("NXR Operation", income["operation"]))
		self.assertEqual(
			self._date(-19), str(frappe.db.get_value("NXR Operation", result["operation"], "operation_date"))
		)
		self.assertEqual(
			"303",
			frappe.db.get_value(
				"NXR Operation Metadata", {"operation": result["operation"]}, "movement_code"
			),
		)
		ledger = list_operational_ledger(self.project, 20)
		cancelled = next(row for row in ledger if row["name"] == result["operation"])
		self.assertEqual(
			("voided", True, "Contabilizado"), (cancelled["tone"], cancelled["struck"], cancelled["status"])
		)
