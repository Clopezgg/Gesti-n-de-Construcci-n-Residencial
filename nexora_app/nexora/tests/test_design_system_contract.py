from __future__ import annotations

import pathlib
import re
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
REPO_ROOT = APP_ROOT.parents[1]
CSS = APP_ROOT / "public/css"
DESIGN_SYSTEM = CSS / "nexora_design_system.css"
LOGIN_CSS = CSS / "nexora_login.css"
LOGIN_HTML = APP_ROOT / "www/login.html"
LOGIN_PY = APP_ROOT / "www/login.py"
HOOKS = APP_ROOT / "hooks.py"


class TestDesignSystemContract(unittest.TestCase):
	"""Capítulo 34: un único componente reutilizable, nunca varias variantes.

	Antes de esto había cinco hojas, siete variables entre todas y un archivo llamado
	`nexora_dashboard_fixes.css`. El nombre confesaba el método: cada pantalla resolvía su
	aspecto por su cuenta y el resultado era la interfaz del marco con retoques.
	"""

	def source(self) -> str:
		return DESIGN_SYSTEM.read_text(encoding="utf-8")

	def test_the_design_system_loads_before_every_other_sheet(self) -> None:
		"""Define las variables que consumen las demás: cargarlo después las dejaría
		resolviendo tokens que todavía no existen."""
		self.assertTrue(DESIGN_SYSTEM.is_file())
		hooks = HOOKS.read_text(encoding="utf-8")
		includes = hooks.split("app_include_css = [", 1)[1].split("]", 1)[0]
		sheets = re.findall(r'"/assets/nexora/css/([a-z_]+\.css)"', includes)
		self.assertEqual(
			"nexora_design_system.css",
			sheets[0],
			"el sistema de diseño debe ser la primera hoja del escritorio",
		)

	def test_the_scales_exist_instead_of_isolated_values(self) -> None:
		"""Un radio único aplicado igual a una tarjeta y a un chip hace que todo parezca
		del mismo tamaño; un tamaño de letra sin su interlineado obliga a inventarlo en
		cada pantalla, y ahí es donde nacen las diez variantes."""
		code = self.source()
		for token, minimum in (
			("--nxr-neutral-", 10),
			("--nxr-brand-", 10),
			("--nxr-space-", 10),
			("--nxr-radius-", 6),
			("--nxr-text-", 9),
			("--nxr-elevation-", 4),
		):
			with self.subTest(scale=token):
				declared = len(re.findall(rf"{re.escape(token)}[a-z0-9]+:", code))
				self.assertGreaterEqual(declared, minimum, f"{token} no es una escala")
		# Cada paso tipográfico lleva su interlineado declarado al lado.
		for step in ("2xs", "xs", "sm", "base", "md", "lg", "xl", "2xl", "3xl", "display"):
			with self.subTest(step=step):
				self.assertIn(f"--nxr-text-{step}:", code)
				self.assertIn(f"--nxr-text-{step}-lh:", code)

	def test_the_product_no_longer_borrows_googles_palette(self) -> None:
		"""`#1a73e8`, `#34a853`, `#fbbc04` y `#ea4335` son los colores de Google. Una
		identidad prestada no es una identidad."""
		borrowed = ("#1a73e8", "#34a853", "#fbbc04", "#ea4335")
		offenders: list[str] = []
		for sheet in sorted(CSS.glob("*.css")):
			lowered = sheet.read_text(encoding="utf-8").lower()
			for color in borrowed:
				if color in lowered:
					offenders.append(f"{sheet.name}:{color}")
		self.assertEqual([], offenders, "la paleta prestada sigue viva")

	def test_the_shared_sheet_never_touches_a_bare_element(self) -> None:
		"""Se carga en todo el escritorio de Frappe. Una regla sobre `button` o `table`
		repintaría pantallas que no son nuestras."""
		code = re.sub(r"/\*.*?\*/", "", self.source(), flags=re.DOTALL)
		offenders: list[str] = []
		for selector in re.findall(r"(?:^|[};])\s*([^{};@]+?)\s*\{", code, flags=re.MULTILINE):
			for part in selector.split(","):
				part = part.strip()
				# Pasos de `@keyframes`: no son selectores.
				if not part or part in {"to", "from"} or part.endswith("%"):
					continue
				# Lo peligroso es un selector que caiga sobre cualquier elemento del
				# escritorio. `.nxr-field__control input` no lo es: está anclado a una
				# clase nuestra y solo alcanza lo que hay dentro de ella.
				# `:root` es donde viven las variables: no pinta nada.
				if part.startswith(":") or "." in part or "#" in part or "[" in part:
					continue
				offenders.append(part)
		self.assertEqual([], offenders, "solo variables y clases `nxr-`")

	def test_dark_theme_only_reassigns_semantic_tokens(self) -> None:
		"""Si el tema oscuro tocara primitivas, el claro y el oscuro dejarían de ser la
		misma paleta con distinta asignación y empezarían a divergir."""
		code = self.source()
		dark = code.split('[data-nxr-theme="dark"]', 1)[1].split("\n}", 1)[0]
		primitives = re.findall(r"--nxr-(?:neutral|brand|success-\d|warning-\d|danger-\d)[a-z0-9-]*:", dark)
		self.assertEqual([], primitives, "el tema oscuro reasigna semántica, no primitivas")
		for token in ("--nxr-canvas", "--nxr-surface", "--nxr-text-primary", "--nxr-border"):
			with self.subTest(token=token):
				self.assertIn(f"{token}:", dark)

	def test_money_out_is_not_painted_red(self) -> None:
		"""Pintar de rojo cada gasto legítimo entrena al usuario a ignorar el rojo, y
		entonces el rojo deja de servir para avisar de lo que sí está mal."""
		code = self.source()
		money = code.split("--nxr-money-in:", 1)[1].split("}", 1)[0]
		self.assertIn("--nxr-money-out: var(--nxr-neutral-800);", f"--nxr-money-in:{money}")
		self.assertNotIn("danger", money.split("--nxr-money-out:", 1)[1].split(";", 1)[0])


class TestLoginSurfaceContract(unittest.TestCase):
	"""La primera pantalla del producto era la del marco."""

	def test_the_login_page_overrides_the_frameworks_own(self) -> None:
		self.assertTrue(LOGIN_HTML.is_file())
		self.assertTrue(LOGIN_PY.is_file())
		html = LOGIN_HTML.read_text(encoding="utf-8")
		self.assertIn('{% extends "templates/web.html" %}', html)
		for block in ("head_include", "page_content", "script"):
			with self.subTest(block=block):
				self.assertIn(f"{{% block {block} %}}", html)
		for sheet in ("nexora_design_system.css", "nexora_login.css"):
			with self.subTest(sheet=sheet):
				self.assertIn(sheet, html)

	def test_the_authentication_rules_stay_in_the_framework(self) -> None:
		"""Reimplementarlas habría significado mantener una copia de las reglas de acceso
		del marco en la superficie donde un error no se paga con una pantalla fea sino con
		una puerta abierta."""
		code = LOGIN_PY.read_text(encoding="utf-8")
		self.assertIn("from frappe.www import login as frappe_login", code)
		self.assertIn("frappe_login.get_context(context)", code)
		self.assertIn("no_cache = 1", code)
		# Las tres garantías las declara el servidor, no la plantilla: cambiar el texto
		# obliga a pasar por el módulo que las nombra.
		self.assertIn("ASSURANCES", code)
		html = LOGIN_HTML.read_text(encoding="utf-8")
		self.assertIn("nexora_assurances", html)

	def test_the_login_refuses_to_redirect_outside_the_site(self) -> None:
		"""Un `redirect-to` hacia otro dominio convierte la pantalla de acceso en un
		trampolín para llevarse la sesión. `//otro.sitio` es absoluta aunque empiece por
		barra."""
		html = LOGIN_HTML.read_text(encoding="utf-8")
		guard = html.split("function safeRedirect()", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('target.charAt(0) !== "/"', guard)
		self.assertIn('target.charAt(1) === "/"', guard)
		self.assertIn('target.charAt(1) === "\\\\"', guard)

	def test_the_login_keeps_the_capabilities_it_replaces(self) -> None:
		"""Sustituir la pantalla no puede quitarle al usuario lo que sí podía hacer."""
		html = LOGIN_HTML.read_text(encoding="utf-8")
		for capability in (
			"frappe.core.doctype.user.user.reset_password",
			"frappe.www.login.send_login_link",
			"provider_logins",
			"disable_user_pass_login",
		):
			with self.subTest(capability=capability):
				self.assertIn(capability, html)

	def test_the_walk_checks_the_login_it_is_about_to_use(self) -> None:
		"""Comprobar que `/login` devuelve 200 no distingue nuestra pantalla de la del
		marco: la nuestra podría desaparecer sin que nadie se entere."""
		support = (REPO_ROOT / "scripts/nexora_browser_support.mjs").read_text(encoding="utf-8")
		self.assertIn("export async function validateLoginSurface(page, profile)", support)
		body = support.split("export async function validateLoginSurface(page, profile) {", 1)[1]
		body = body.split("\n}", 1)[0]
		for marker in (".nxr-login", ".nxr-login__assurances li", "#nxr-usr", "#nxr-submit"):
			with self.subTest(marker=marker):
				self.assertIn(marker, body)
		# Y se llama de verdad al autenticar, no solo se define.
		authenticate = support.split("export async function authenticate(page, context, profile) {", 1)[1]
		self.assertIn("await validateLoginSurface(page, profile);", authenticate.split("\n}", 1)[0])


if __name__ == "__main__":
	unittest.main()
