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

	def test_no_component_class_collides_with_the_screens(self) -> None:
		"""El sistema de diseño se carga en todas las pantallas. Cuando su capa de
		componentes usaba `.nxr-card`, `.nxr-btn`, `.nxr-field` y `.nxr-eyebrow` —nombres
		que ya existían en cincuenta y seis sitios—, repintó silenciosamente cada tarjeta,
		botón y campo del producto. El recorrido real lo encontró como tarjetas
		desbordando el ancho de la ventana y una página de treinta y dos mil píxeles de
		alto en el teléfono.

		Una colisión real es que OTRA hoja de estilos defina su propia regla para el mismo
		nombre: dos reglas compitiendo en cascada repintan una a la otra en silencio, que
		fue el defecto original. Que una pantalla *use* la clase en su marcado —el
		propósito mismo de adoptar el sistema de diseño en el Bloque D— no es una
		colisión, es la migración funcionando; por eso solo se examinan hojas de estilos
		aquí, nunca el marcado que las consume. `nexora_login.css`, `nexora_shell.css`,
		`nexora_dashboard_fixes.css` y `nexora_guided_operations.css` quedan fuera del
		barrido: las cuatro son capas deliberadas que extienden un componente ya
		nombrado —un color de marca, un ancho de trazo, un mínimo táctil en móvil, el
		`overflow-x` de `.nxr-ds-table-wrap` dentro de un panel angosto (Bloque 129)—
		sin redefinir su identidad visual, el mismo patrón que uno mismo reconocería en
		la capa de tema oscuro del propio sistema."""
		components = set(re.findall(r"\.(nxr-ds[a-z0-9_-]*)", self.source()))
		self.assertTrue(components, "la capa de componentes debe existir y llevar su prefijo")
		# Nada fuera del prefijo puede pintar. Las variables no cuentan: no son clases.
		painted = set(re.findall(r"\.(nxr-[a-z0-9_-]+)", self.source()))
		self.assertEqual(
			set(),
			painted - components,
			"todo componente del sistema vive bajo `nxr-ds-`",
		)
		other_sheets = [
			path
			for path in CSS.glob("*.css")
			if path.name
			not in {
				"nexora_design_system.css",
				"nexora_login.css",
				"nexora_shell.css",
				"nexora_dashboard_fixes.css",
				"nexora_guided_operations.css",
			}
		]
		defined_elsewhere: set[str] = set()
		for path in other_sheets:
			# Un comentario que explica por qué una tarjeta usa `.nxr-ds-card` no es una
			# regla que compita con ella; solo el CSS de verdad puede colisionar.
			without_comments = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
			defined_elsewhere |= set(re.findall(r"\.(nxr-[a-z0-9_-]+)", without_comments))
		collisions = sorted(components & defined_elsewhere)
		self.assertEqual([], collisions, "otra hoja de estilos define una regla con el mismo nombre")

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

	def test_a_real_table_component_exists_instead_of_bare_bootstrap(self) -> None:
		"""Diecinueve pantallas reales usaban `table table-bordered` de Bootstrap sin
		ningún componente propio detrás — en un producto financiero la tabla es la
		pieza más vista de todas, y esa era la que seguía pareciendo el escritorio del
		marco (Bloque 127)."""
		code = self.source()
		self.assertIn(".nxr-ds-table-wrap", code)
		self.assertIn(".nxr-ds-table thead th", code)
		self.assertIn(".nxr-ds-table tbody td", code)
		self.assertIn(".nxr-ds-table tbody tr:hover td", code)
		self.assertIn('.nxr-ds-table td[data-numeric="true"]', code)
		self.assertIn(".nxr-ds-table__empty", code)
		# Mismo alineamiento tabular que `.nxr-ds-money-row__value`: las cifras
		# de una tabla deben alinear entre filas igual que en cualquier hoja de cálculo.
		self.assertIn("font-variant-numeric: tabular-nums;", code)

	def test_the_table_component_only_uses_semantic_tokens(self) -> None:
		"""Un color fijo dentro del componente lo desconecta del tema oscuro que ya
		existe para todo lo demás — el mismo motivo por el que Bloque 34 prohíbe
		primitivas sueltas en el resto del sistema."""
		code = self.source()
		block = code.split("/* Tablas ", 1)[1].split("/* Accesibilidad", 1)[0]
		hex_colors = re.findall(r"#[0-9a-fA-F]{3,8}\b", block)
		self.assertEqual([], hex_colors, "la tabla debe usar var(--nxr-...), no color fijo")

	def test_money_out_is_not_painted_red(self) -> None:
		"""Pintar de rojo cada gasto legítimo entrena al usuario a ignorar el rojo, y
		entonces el rojo deja de servir para avisar de lo que sí está mal."""
		code = self.source()
		money = code.split("--nxr-money-in:", 1)[1].split("}", 1)[0]
		self.assertIn("--nxr-money-out: var(--nxr-neutral-800);", f"--nxr-money-in:{money}")
		self.assertNotIn("danger", money.split("--nxr-money-out:", 1)[1].split(";", 1)[0])

	def test_the_notice_component_covers_every_tone_including_warning(self) -> None:
		"""`.nxr-ds-notice` traía danger/success/info desde el propio componente pero
		nunca warning — el tono que de verdad usaban los diálogos de corrección, que por
		su falta seguían pintando `alert alert-warning` de Bootstrap (Bloque 148)."""
		code = self.source()
		self.assertIn(".nxr-ds-notice--danger", code)
		self.assertIn(".nxr-ds-notice--success", code)
		self.assertIn(".nxr-ds-notice--info", code)
		self.assertIn(".nxr-ds-notice--warning", code)
		warning = code.split(".nxr-ds-notice--warning {", 1)[1].split("}", 1)[0]
		self.assertIn("var(--nxr-warning", warning)

	def test_no_screen_still_paints_a_bare_bootstrap_alert(self) -> None:
		"""Tres archivos compartidos (`nexora_operational_ui.js`,
		`nexora_quick_flows.js`, `nexora_guided_operations.js`) seguían usando `alert
		alert-*` de Bootstrap en los diálogos de corrección y anulación — el mismo patrón
		de la tabla (Bloque 127): el componente propio ya existía, solo faltaba
		adoptarlo en todas partes."""
		offenders: list[str] = []
		for js in sorted((APP_ROOT / "public/js").glob("*.js")):
			if re.search(r'class=["\']alert alert-', js.read_text(encoding="utf-8")):
				offenders.append(js.name)
		for js in sorted((APP_ROOT / "nexora/page").glob("*/[a-z]*.js")):
			if re.search(r'class=["\']alert alert-', js.read_text(encoding="utf-8")):
				offenders.append(js.name)
		self.assertEqual([], offenders, "el aviso vive en .nxr-ds-notice, no en alert de Bootstrap")

	def test_the_empty_state_lives_in_the_design_system_on_semantic_tokens(self) -> None:
		"""`.nxr-empty` era una regla copiada en `nexora.css` con `var(--text-muted)`
		—la primitiva del marco, no un token `--nxr-*`— repetida sesenta y una veces en
		dieciocho pantallas. Migra el nombre y el color; el resultado visual es
		idéntico a propósito (Bloque 149)."""
		code = self.source()
		self.assertIn(".nxr-ds-empty {", code)
		block = code.split(".nxr-ds-empty {", 1)[1].split("}", 1)[0]
		self.assertIn("var(--nxr-text-secondary)", block)
		self.assertNotIn("var(--text-muted", block)

	def test_no_screen_still_uses_the_legacy_bare_empty_class(self) -> None:
		"""Dieciocho pantallas construían `class="nxr-empty"` a mano, siempre con el
		mismo resultado — el mismo patrón que llevó a construir `.nxr-ds-table` en el
		Bloque 127: un componente real, adoptado en todas partes, no una convención
		repetida."""
		offenders: list[str] = []
		for js in sorted((APP_ROOT / "public/js").glob("*.js")):
			if "nxr-empty" in js.read_text(encoding="utf-8"):
				offenders.append(js.name)
		for js in sorted((APP_ROOT / "nexora/page").glob("*/[a-z]*.js")):
			if "nxr-empty" in js.read_text(encoding="utf-8"):
				offenders.append(js.name)
		self.assertEqual([], offenders, "el estado vacío vive en .nxr-ds-empty")
		legacy_css = (CSS / "nexora.css").read_text(encoding="utf-8")
		self.assertNotIn(".nxr-empty {", legacy_css)


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
