from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.context360.service import get_project_overview
from nexora.context360.timeline import get_project_timeline
from nexora.financial.commitments import create_commitment, release_commitment
from nexora.financial.operations import execute_financial_operation
from nexora.financial.sources import create_fund_source


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


class TestContext360IntegrationMariaDB(FrappeTestCase):
	"""NXR-UX-0010 / NXR-UX-0011: contexto 360° y timeline reales contra Frappe/MariaDB.

	Requiere bench + MariaDB reales; no se pudo ejecutar en el entorno de esta sesión
	(sin bench/Frappe/MariaDB). Cobertura deliberadamente acotada: contratos, órdenes
	de compra, avance y evidencia ya están cubiertos por unidad en
	`test_context360_core.py` (normalización de eventos, incluidas excepciones) y por
	contrato estático en `test_context360_contract.py`; aquí se ejercita el camino
	real de extremo a extremo con fondos/operaciones/compromisos (las mismas
	funciones ya usadas y probadas en `test_budget_commitment_integration.py`), que
	es donde vive la parte financiera — la más sensible de las dos funciones nuevas.
	"""

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		marker = uuid.uuid4().hex[:8]
		cls.project = str(
			frappe.get_doc(
				{"doctype": "Project", "project_name": f"_Test Context360 {marker}", "status": "Open"}
			)
			.insert(ignore_permissions=True)
			.name
		)
		cls.other_project = str(
			frappe.get_doc(
				{"doctype": "Project", "project_name": f"_Test Context360 Other {marker}", "status": "Open"}
			)
			.insert(ignore_permissions=True)
			.name
		)
		cls.manager = _ensure_user(f"nxr-ctx360-manager-{marker}@example.test", "NEXORA Finance Manager")
		cls.requester = _ensure_user(f"nxr-ctx360-requester-{marker}@example.test", "NEXORA Finance Operator")
		cls.viewer = _ensure_user(f"nxr-ctx360-viewer-{marker}@example.test", "NEXORA Project Viewer")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _source(self, project: str, amount: int) -> str:
		frappe.set_user(self.manager)
		return create_fund_source(
			{
				"idempotency_key": _key("ctx360-source"),
				"source_name": "Fuente contexto 360",
				"channel": "Remittance",
				"project": project,
				"source_date": frappe.utils.today(),
				"currency": "HNL",
				"original_amount": amount,
				"exchange_rate": 1,
				"origin_or_sender": "Prueba NXR-UX-0010",
				"custodian": self.manager,
			}
		)["fund_source"]

	# --- Permisos: no debe poder descubrirse información restringida ---------------

	def test_project_viewer_without_a_grant_cannot_see_the_overview_or_timeline(self) -> None:
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			get_project_overview({"project": self.project})
		with self.assertRaises(frappe.PermissionError):
			get_project_timeline({"project": self.project})

	def test_project_viewer_with_an_explicit_grant_can_see_only_that_project(self) -> None:
		frappe.set_user("Administrator")
		frappe.get_doc(
			{"doctype": "User Permission", "user": self.viewer, "allow": "Project", "for_value": self.project}
		).insert(ignore_permissions=True)
		frappe.set_user(self.viewer)
		overview = get_project_overview({"project": self.project})
		self.assertEqual(self.project, overview["project"]["name"])
		# El mismo usuario sigue sin poder ver un proyecto para el que nunca se le
		# concedió acceso — el permiso es por proyecto, no global.
		with self.assertRaises(frappe.PermissionError):
			get_project_overview({"project": self.other_project})
		with self.assertRaises(frappe.PermissionError):
			get_project_timeline({"project": self.other_project})

	def test_a_nonexistent_project_is_rejected_before_any_query_runs(self) -> None:
		frappe.set_user(self.manager)
		with self.assertRaises(frappe.ValidationError):
			get_project_overview({"project": "PROJECT-DOES-NOT-EXIST"})

	def test_missing_project_is_rejected_with_a_clear_message_not_a_traceback(self) -> None:
		frappe.set_user(self.manager)
		with self.assertRaisesRegex(frappe.ValidationError, "Seleccione un proyecto"):
			get_project_overview({})
		with self.assertRaisesRegex(frappe.ValidationError, "Seleccione un proyecto"):
			get_project_timeline({})

	# --- Proyecto sin datos ---------------------------------------------------------

	def test_a_project_with_no_data_returns_empty_structures_not_errors(self) -> None:
		frappe.set_user(self.manager)
		overview = get_project_overview({"project": self.other_project})
		self.assertEqual(0, overview["finance"]["source_count"])
		self.assertEqual(0, overview["open_purchases"]["count"])
		self.assertEqual([], overview["participants"])
		timeline = get_project_timeline({"project": self.other_project})
		self.assertEqual([], timeline["events"])
		self.assertEqual(0, timeline["count"])
		self.assertFalse(timeline["has_more"])

	# --- Proyecto con datos reales: fondos, operaciones, compromisos ---------------

	def test_overview_reflects_real_fund_and_operation_data(self) -> None:
		source = self._source(self.project, 5000)
		frappe.set_user(self.manager)
		execute_financial_operation(
			{
				"idempotency_key": _key("ctx360-outflow"),
				"operation_type": "Outflow",
				"project": self.project,
				"amount_hnl": 800,
				"allocations": [{"source": source, "amount_hnl": 800}],
				"economic_category": "CONSTRUCTION_MATERIALS",
				"requester": self.requester,
				"approved_by": self.manager,
			}
		)
		overview = get_project_overview({"project": self.project})
		self.assertEqual(1, overview["finance"]["source_count"])
		# 5000 originales - 800 de la salida ya ejecutada = 4200 disponibles.
		self.assertEqual(4200.0, overview["finance"]["total_balance_hnl"])

	def test_timeline_lists_operations_and_commitments_in_chronological_order(self) -> None:
		source = self._source(self.project, 5000)
		frappe.set_user(self.manager)
		execute_financial_operation(
			{
				"idempotency_key": _key("ctx360-tl-outflow"),
				"operation_type": "Outflow",
				"operation_date": frappe.utils.add_days(frappe.utils.today(), -2),
				"project": self.project,
				"amount_hnl": 300,
				"allocations": [{"source": source, "amount_hnl": 300}],
				"economic_category": "CONSTRUCTION_MATERIALS",
				"requester": self.requester,
				"approved_by": self.manager,
			}
		)
		commitment = create_commitment(
			{
				"idempotency_key": _key("ctx360-tl-commit"),
				"project": self.project,
				"commitment_date": frappe.utils.today(),
				"amount_hnl": 400,
				"allocations": [{"source": source, "amount_hnl": 400}],
				"requester": self.requester,
				"approved_by": self.manager,
				"description": "Compromiso para la timeline",
			}
		)
		timeline = get_project_timeline({"project": self.project, "categories": "financiero"})
		self.assertGreaterEqual(len(timeline["events"]), 2)
		dates = [event["date"] for event in timeline["events"]]
		self.assertEqual(sorted(dates, reverse=True), dates, "más reciente primero")
		commitment_events = [e for e in timeline["events"] if e["doctype"] == "NXR Commitment"]
		self.assertEqual(1, len(commitment_events))
		self.assertEqual(commitment["commitment"], commitment_events[0]["name"])
		self.assertFalse(commitment_events[0]["is_exception"])

	def test_timeline_category_filter_excludes_other_categories(self) -> None:
		self._source(self.project, 1000)
		frappe.set_user(self.manager)
		timeline = get_project_timeline({"project": self.project, "categories": ["compras"]})
		self.assertEqual(["compras"], timeline["categories"])
		for event in timeline["events"]:
			self.assertEqual("compras", event["category"])

	def test_timeline_flags_a_rejected_commitment_as_an_exception(self) -> None:
		source = self._source(self.project, 2000)
		frappe.set_user(self.manager)
		commitment = create_commitment(
			{
				"idempotency_key": _key("ctx360-tl-reject-setup"),
				"project": self.project,
				"commitment_date": frappe.utils.today(),
				"amount_hnl": 100,
				"allocations": [{"source": source, "amount_hnl": 100}],
				"requester": self.requester,
				"approved_by": self.manager,
				"description": "Compromiso que se libera por completo",
			}
		)
		release_commitment(
			{
				"idempotency_key": _key("ctx360-tl-release"),
				"commitment": commitment["commitment"],
				"amount_hnl": 100,
				"allocations": [{"source": source, "amount_hnl": 100}],
				"requester": self.requester,
				"approved_by": self.manager,
			}
		)
		timeline = get_project_timeline({"project": self.project, "categories": "financiero"})
		released = next(e for e in timeline["events"] if e["name"] == commitment["commitment"])
		# Liberado por completo es el ciclo de vida normal de un compromiso, no una
		# excepción — a diferencia de cancelarlo o rechazarlo (probado por unidad en
		# test_context360_core.py, que sí cubre el caso "Cancelled").
		self.assertEqual("Released", released["status"])
		self.assertFalse(released["is_exception"])
