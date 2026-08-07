from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestCommandCenterZonesContract(unittest.TestCase):
	"""Bloque C, segundo incremento: las tres zonas nuevas que el responsable definió
	-actividad del equipo, cumplimiento y vencimientos, accesos recientes-. Ninguna
	sustituye la autorización que ya protege el resto del resumen ejecutivo, y ninguna
	inventa una segunda fuente de verdad para un texto que ya vive en otro sitio.
	"""

	def test_team_activity_never_skips_project_authorization(self) -> None:
		code = (APP_ROOT / "dashboard/activity_query.py").read_text(encoding="utf-8")
		self.assertIn("require_project_access", code)
		body = code.split("def team_activity(", 1)[1].split("\ndef ", 1)[0]
		self.assertIn("require_project_access(project, action=", body)
		# La comprobación se hace antes de tocar la base de datos: al revés dejaría
		# escapar una consulta sin autorizar si la comprobación fallara más tarde.
		self.assertLess(
			body.index("require_project_access("),
			body.index("_get_all("),
			"la autorización se comprueba antes de consultar, no después",
		)

	def test_team_activity_excludes_the_viewer_and_reuses_the_screens_status_labels(self) -> None:
		"""«Actividad del equipo» responde qué hizo el resto del equipo, no un historial
		personal; y el texto de cada estado ya vive en `nexora_dashboard.js`
		(`statusLabels`) desde antes de esta zona -duplicarlo en Python lo dejaría
		divergiendo la primera vez que alguien retocara un solo lado."""
		code = (APP_ROOT / "dashboard/activity_query.py").read_text(encoding="utf-8")
		self.assertIn('"modified_by": ["!=", actor]', code)
		self.assertNotIn("STATUS_LABELS", code)
		self.assertNotIn('"Aprobó"', code)
		dashboard = (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(
			encoding="utf-8"
		)
		self.assertIn("function renderTeamActivity(", dashboard)
		self.assertIn("statusLabels[row.status]", dashboard.split("function renderTeamActivity(", 1)[1][:400])

	def test_compliance_urgency_is_computed_from_the_date_not_the_hand_set_status(self) -> None:
		"""`NXR Entity Compliance.status` lo transiciona una persona
		(`transition_entity_compliance`) y puede quedar desactualizado si nadie lo
		revisó. Una alerta de vencimiento que confiara en ese campo callaría un
		documento vencido cuyo estado nadie cambió todavía."""
		code = (APP_ROOT / "dashboard/compliance_query.py").read_text(encoding="utf-8")
		self.assertIn("require_project_access", code)
		self.assertIn("valid_until<%(today)s", code)
		self.assertIn("valid_until<=DATE_ADD(%(today)s, INTERVAL %(window)s DAY)", code)
		# La condición de urgencia lee la fecha; no hay ninguna rama que decida el
		# estado leyendo comp.status (solo se usa para excluir la excepción aprobada).
		self.assertEqual(1, code.count("comp.status"))
		self.assertIn("comp.status!='Approved Exception'", code)

	def test_compliance_is_scoped_to_entities_with_an_active_role_on_the_project(self) -> None:
		"""Sin este filtro, el resumen mostraría el cumplimiento de cualquier entidad de
		la base -incluidas las que nunca trabajaron en el proyecto consultado-, la misma
		fuga de alcance que `require_project_access` existe para evitar en el resto del
		panel."""
		code = (APP_ROOT / "dashboard/compliance_query.py").read_text(encoding="utf-8")
		self.assertIn("tabNXR Entity Role", code)
		self.assertIn("role.project=%(project)s", code)
		self.assertIn("role.status='Active'", code)

	def test_the_snapshot_wires_both_new_zones(self) -> None:
		code = (APP_ROOT / "dashboard/snapshot_query.py").read_text(encoding="utf-8")
		self.assertIn("from nexora.dashboard.activity_query import team_activity", code)
		self.assertIn("from nexora.dashboard.compliance_query import compliance_alerts", code)
		self.assertIn('snapshot["team_activity"] = team_activity(project)', code)
		self.assertIn('snapshot["compliance_alerts"] = compliance_alerts(project)', code)

	def test_the_dashboard_renders_all_three_new_zones(self) -> None:
		dashboard = (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(
			encoding="utf-8"
		)
		for marker in (
			"nxr-team-activity-list",
			"nxr-compliance-list",
			"nxr-recent-routes-list",
			"renderTeamActivity(data.team_activity?.items",
			"renderCompliance(data.compliance_alerts?.items",
			"renderRecentRoutes()",
		):
			with self.subTest(marker=marker):
				self.assertIn(marker, dashboard)

	def test_recent_routes_are_scoped_per_user_and_only_track_nexora_screens(self) -> None:
		"""Un equipo con un navegador compartido no debe mezclar el historial de dos
		personas; y esta carcasa no es dueña de las pantallas del marco fuera de
		NEXORA -las mismas dos reglas que ya rigen el resto de la carcasa."""
		code = (APP_ROOT / "public/js/nexora_recent_routes.js").read_text(encoding="utf-8")
		self.assertIn("frappe.session?.user", code)
		self.assertIn('route.startsWith("nexora-")', code)
		self.assertIn("window.nexora.recentRoutes", code)
		# La lista visible nunca incluye la pantalla en la que ya se está: no es un
		# atajo hacia donde el usuario ya está parado.
		function_body = code.split("function list() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("entry.route !== current", function_body)

	def test_recent_routes_module_is_registered_site_wide_and_offline(self) -> None:
		"""Un módulo que se registra en `app_include_js` pero no en el precache del
		`service worker` funciona en línea y desaparece exactamente cuando el recorrido
		real necesita comprobar que NEXORA arranca sin conexión (Capítulo alcanzado por
		`test_offline_shell_precaches_every_site_wide_bundle`)."""
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('"/assets/nexora/js/nexora_recent_routes.js"', hooks)
		worker = (APP_ROOT / "www/nexora-service-worker.js").read_text(encoding="utf-8")
		self.assertIn('"/assets/nexora/js/nexora_recent_routes.js"', worker)

	def test_recent_routes_labels_come_from_the_shells_own_destination_list(self) -> None:
		"""La carcasa (`nexora_shell.js`) ya nombra cada destino una vez
		(`window.nexora.shell.sections`); repetir esos nombres en un segundo diccionario
		aquí los dejaría divergiendo la primera vez que alguien renombrara un destino."""
		code = (APP_ROOT / "public/js/nexora_recent_routes.js").read_text(encoding="utf-8")
		self.assertIn("window.nexora.shell?.sections", code)
		self.assertNotIn("nexora-dashboard", code)


if __name__ == "__main__":
	unittest.main()
