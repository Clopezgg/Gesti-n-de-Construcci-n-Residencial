from __future__ import annotations

import json
import pathlib
import unittest

APP = pathlib.Path(__file__).resolve().parents[2]
DOCTYPE_ROOT = APP / "nexora/nexora/doctype"
REMITTANCE_JSON = DOCTYPE_ROOT / "nxr_remittance/nxr_remittance.json"
DESTINATION_JSON = DOCTYPE_ROOT / "nxr_remittance_destination/nxr_remittance_destination.json"
REMITTANCE_PY = DOCTYPE_ROOT / "nxr_remittance/nxr_remittance.py"
FUND_SOURCE_JSON = DOCTYPE_ROOT / "nxr_fund_source/nxr_fund_source.json"
FUND_SOURCE_PY = DOCTYPE_ROOT / "nxr_fund_source/nxr_fund_source.py"
SERVICE_PY = APP / "nexora/financial/remittances.py"
SOURCES_PY = APP / "nexora/financial/sources.py"
STABLE_API_PY = APP / "nexora/financial/service.py"


class TestRemittanceContract(unittest.TestCase):
	"""Bloque 39: una remesa reparte un solo importe recibido entre varios
	`NXR Fund Source` nuevos, agrupados bajo un documento padre. Contrato de
	código, sin Frappe — la conducta real la prueba
	test_remittances_integration.py contra MariaDB real."""

	def test_both_doctypes_exist_in_the_nexora_module(self) -> None:
		remittance = json.loads(REMITTANCE_JSON.read_text(encoding="utf-8"))
		destination = json.loads(DESTINATION_JSON.read_text(encoding="utf-8"))
		self.assertEqual("NXR Remittance", remittance["name"])
		self.assertEqual("NEXORA", remittance["module"])
		self.assertEqual("NXR Remittance Destination", destination["name"])
		self.assertEqual("NEXORA", destination["module"])

	def test_destination_is_a_real_child_table_of_the_remittance(self) -> None:
		destination = json.loads(DESTINATION_JSON.read_text(encoding="utf-8"))
		self.assertEqual(1, destination["istable"])
		remittance = json.loads(REMITTANCE_JSON.read_text(encoding="utf-8"))
		table_field = next(field for field in remittance["fields"] if field["fieldname"] == "destinations")
		self.assertEqual("Table", table_field["fieldtype"])
		self.assertEqual("NXR Remittance Destination", table_field["options"])

	def test_remittance_starts_with_no_interactive_write_debt(self) -> None:
		"""A diferencia de NXR Fund Source (fuga documentada en known_debt de
		test_app_contract.py), este doctype nuevo nace sin ese permiso — no hay
		motivo para repetir la deuda en código nuevo."""
		remittance = json.loads(REMITTANCE_JSON.read_text(encoding="utf-8"))
		for permission in remittance["permissions"]:
			with self.subTest(role=permission["role"]):
				self.assertEqual(0, permission["create"], permission["role"])
				self.assertEqual(0, permission["write"], permission["role"])

	def test_fund_source_carries_a_link_back_to_its_remittance(self) -> None:
		fund_source = json.loads(FUND_SOURCE_JSON.read_text(encoding="utf-8"))
		field = next(f for f in fund_source["fields"] if f["fieldname"] == "remittance")
		self.assertEqual("Link", field["fieldtype"])
		self.assertEqual("NXR Remittance", field["options"])
		self.assertIn("remittance", fund_source["field_order"])
		controller = FUND_SOURCE_PY.read_text(encoding="utf-8")
		immutable_block = controller.split("IMMUTABLE_SOURCE_FIELDS = (", 1)[1].split(")", 1)[0]
		self.assertIn('"remittance"', immutable_block)

	def test_remittance_controller_requires_service_write_and_blocks_deletion(self) -> None:
		controller = REMITTANCE_PY.read_text(encoding="utf-8")
		self.assertIn("def before_insert(self) -> None:", controller)
		self.assertIn("require_service_write()", controller)
		self.assertIn("def on_trash(self) -> None:", controller)
		on_trash = controller.split("def on_trash(self) -> None:", 1)[1]
		self.assertIn("frappe.throw(", on_trash)

	def test_remittance_controller_is_the_single_place_that_checks_the_sum(self) -> None:
		"""La suma de destinos contra el total se valida una sola vez, en el
		controlador — el servicio no repite la regla (Capítulo 34)."""
		controller = REMITTANCE_PY.read_text(encoding="utf-8")
		self.assertIn("allocated != self.total_amount_hnl", controller)
		service = SERVICE_PY.read_text(encoding="utf-8")
		self.assertNotIn("allocated", service)

	def test_service_reuses_open_fund_source_and_cancel_fund_source(self) -> None:
		"""No hay una segunda implementación de "crear un fondo" ni de "anular un
		fondo" — create_remittance/cancel_remittance llaman a las funciones que
		create_fund_source/cancel_fund_source ya usan."""
		service = SERVICE_PY.read_text(encoding="utf-8")
		self.assertIn("from nexora.financial.sources import cancel_fund_source, open_fund_source", service)
		self.assertIn("open_fund_source(source_data, correlation_id)", service)
		self.assertIn("cancel_fund_source(", service)
		sources = SOURCES_PY.read_text(encoding="utf-8")
		self.assertIn("def open_fund_source(", sources)
		# create_fund_source ahora delega en open_fund_source: una sola
		# implementación real de "crear un fondo + su operación 101".
		create_fn = sources.split("def create_fund_source(", 1)[1].split("\n\n\n", 1)[0]
		self.assertIn("open_fund_source(data, correlation_id, fingerprint=fingerprint)", create_fn)

	def test_remittance_is_central_not_project_owned(self) -> None:
		remittance = json.loads(REMITTANCE_JSON.read_text(encoding="utf-8"))
		project = next(f for f in remittance["fields"] if f["fieldname"] == "project")
		self.assertEqual(0, project.get("reqd", 0))
		fund_source = json.loads(FUND_SOURCE_JSON.read_text(encoding="utf-8"))
		project = next(f for f in fund_source["fields"] if f["fieldname"] == "project")
		self.assertEqual(0, project.get("reqd", 0))
		service = SERVICE_PY.read_text(encoding="utf-8")
		self.assertIn("Caja Central", service)

	def test_service_is_post_only_permission_guarded_and_transactional(self) -> None:
		service = SERVICE_PY.read_text(encoding="utf-8")
		self.assertEqual(2, service.count('@frappe.whitelist(methods=["POST"])'))
		self.assertIn('require_action("create_source")', service)
		self.assertIn('require_action("cancel_source")', service)
		self.assertIn("savepoint()", service)
		self.assertIn("rollback(point)", service)
		self.assertIn("with service_write():", service)
		self.assertNotIn("frappe.db.commit()", service)

	def test_stable_api_exposes_both_new_functions(self) -> None:
		stable_api = STABLE_API_PY.read_text(encoding="utf-8")
		self.assertIn("cancel_remittance", stable_api)
		self.assertIn("create_remittance", stable_api)
		self.assertIn("from nexora.financial.remittances import", stable_api)

	def test_cancellation_is_all_or_nothing_not_per_destination(self) -> None:
		service = SERVICE_PY.read_text(encoding="utf-8")
		cancel_fn = service.split("def cancel_remittance(", 1)[1]
		self.assertIn("for row in doc.destinations", cancel_fn)
		self.assertIn('doc.status == "Cancelled"', cancel_fn)


if __name__ == "__main__":
	unittest.main()
