from __future__ import annotations

import json
import pathlib
import re
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
MANIFEST = APP_ROOT / "public/manifest.json"
CLIENT = APP_ROOT / "public/js/nexora.js"
WORKER = APP_ROOT / "www/nexora-service-worker.js"
CSS = APP_ROOT / "public/css/nexora.css"
HOOKS = APP_ROOT / "hooks.py"


class TestPWAContract(unittest.TestCase):
	def test_manifest_is_installable_and_uses_real_icons(self) -> None:
		manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
		self.assertEqual("/app/nexora-dashboard", manifest["id"])
		self.assertTrue(manifest["start_url"].startswith(manifest["scope"]))
		self.assertEqual("standalone", manifest["display"])
		self.assertEqual("es-HN", manifest["lang"])
		self.assertEqual({"192x192", "512x512"}, {row["sizes"] for row in manifest["icons"]})
		for icon in manifest["icons"]:
			self.assertIn("maskable", icon["purpose"])
			path = APP_ROOT / "public" / icon["src"].removeprefix("/assets/nexora/")
			self.assertTrue(path.is_file(), path)

	def test_brand_mark_declares_explicit_svg_dimensions(self) -> None:
		"""An `<svg>` with only `viewBox` (no `width`/`height` attributes) can render
		at a 0x0 box when placed in a plain `<img>` inside a flex layout that doesn't
		otherwise establish a cross-axis size — confirmed for real with
		`getBoundingClientRect()` in Frappe's own Desk navbar (Bloque 162): the image
		loaded successfully (`complete: true`, `naturalWidth/Height: 150`) but its
		rendered box was `{width: 0, height: 0}`. ERPNext's and Frappe's own navbar
		logos (`erpnext-logo.svg`/`frappe-framework-logo.svg`) both declare explicit
		`width="100" height="100"` — this is what actually made theirs render and
		NEXORA's not."""
		source = (APP_ROOT / "public/images/nexora.svg").read_text(encoding="utf-8")
		root_tag = source[: source.index(">") + 1]
		self.assertRegex(root_tag, r'width="\d')
		self.assertRegex(root_tag, r'height="\d')

	def test_hooks_does_not_declare_app_logo_url(self) -> None:
		"""`get_app_logo()` (Frappe core, `navbar_settings.py`) only consults the
		`app_logo_url` hook list from every installed app when both
		`Website Settings.app_logo` and `Navbar Settings.app_logo` are empty — and
		then only takes `logos[1]` when the list has EXACTLY two entries, else
		`logos[0]`. With frappe + erpnext + nexora all declaring the hook that
		list has three entries, so declaring it here silently picks Frappe's own
		default logo instead of NEXORA's — confirmed with a real CI screenshot
		(Bloque 160, first attempt). The reliable fix is a database value, set by
		`install.py::_ensure_navbar_logo()`, which `get_app_logo()` checks first
		regardless of how many apps are installed."""
		source = HOOKS.read_text(encoding="utf-8")
		self.assertIsNone(
			re.search(r"^app_logo_url\s*=", source, re.MULTILINE),
			"hooks.py must not declare app_logo_url — see the comment left in its place",
		)

	def test_install_points_the_desk_navbar_at_the_real_nexora_mark(self) -> None:
		install_source = (APP_ROOT / "install.py").read_text(encoding="utf-8")
		asset_match = re.search(r'NAVBAR_LOGO_ASSET\s*=\s*"([^"]+)"', install_source)
		self.assertIsNotNone(asset_match, "install.py must declare NAVBAR_LOGO_ASSET")
		favicon_match = re.search(
			r'^favicon\s*=\s*"([^"]+)"', HOOKS.read_text(encoding="utf-8"), re.MULTILINE
		)
		self.assertIsNotNone(favicon_match, "hooks.py must declare a real favicon")
		self.assertEqual(asset_match.group(1), favicon_match.group(1))
		asset_path = APP_ROOT / "public" / asset_match.group(1).removeprefix("/assets/nexora/")
		self.assertTrue(asset_path.is_file(), asset_path)
		self.assertIn('frappe.db.set_single_value("Website Settings", "app_logo"', install_source)
		self.assertIn(
			"_ensure_navbar_logo()", install_source.split("def after_install()")[1].split("def ")[0]
		)
		self.assertIn(
			"_ensure_navbar_logo()", install_source.split("def after_migrate()")[1].split("def ")[0]
		)

	def test_website_context_favicon_overrides_erpnexts_own_dict_hook(self) -> None:
		"""Confirmed against the real live runtime (curl to /login): the rendered
		<link rel="shortcut icon"> served ERPNext's own favicon
		(/assets/erpnext/images/erpnext-favicon.svg), even though the scalar
		`favicon` hook above already points at NEXORA. Root cause: ERPNext's own
		`erpnext.hooks_base` declares a dict hook `website_context = {"favicon":
		..., "splash_image": ...}`, which is what actually feeds the Jinja
		`{{ favicon }}` used by `www` page templates (login, 404, print) — a
		completely different mechanism from the scalar `favicon` hook, which only
		reaches the Desk/PWA. Without nexora declaring its own `website_context`,
		ERPNext's was the only value and always won."""
		source = HOOKS.read_text(encoding="utf-8")
		context_match = re.search(r"^website_context\s*=\s*\{([^}]*)\}", source, re.DOTALL | re.MULTILINE)
		self.assertIsNotNone(context_match, "hooks.py must declare a website_context dict")
		block = context_match.group(1)
		self.assertRegex(block, r'"favicon"\s*:\s*"/assets/nexora/')
		self.assertRegex(block, r'"splash_image"\s*:\s*"/assets/nexora/')
		self.assertNotIn("erpnext", block.lower())

	def test_website_footer_never_advertises_erpnext(self) -> None:
		"""Confirmed against the real live runtime (curl to a 404 page — a generic
		`www` page, unlike the login page's own custom template): the rendered
		footer read 'Desarrollado por ERPNext' linking to
		https://frappe.io/erpnext?source=website_footer. Root cause: ERPNext ships
		`erpnext/templates/includes/footer/footer_powered.html` and nothing in
		nexora ever provided its own file at that same relative path, so
		ERPNext's was the only one Frappe's app-order template loader could find.
		Same override mechanism already relied on elsewhere in this app (later-
		installed app wins) — nexora installs after erpnext."""
		footer = APP_ROOT / "templates/includes/footer/footer_powered.html"
		self.assertTrue(footer.is_file(), footer)
		content = footer.read_text(encoding="utf-8")
		self.assertIn("NEXORA", content)
		self.assertNotIn("erpnext", content.lower())
		self.assertNotIn("frappe.io", content.lower())

	def test_manifest_shortcuts_open_nexora_flows(self) -> None:
		manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
		urls = {row["url"] for row in manifest["shortcuts"]}
		self.assertIn("/app/nexora-operations?movement_code=101", urls)
		self.assertIn("/app/nexora-operations?movement_code=102", urls)
		self.assertIn("/app/nexora-evidence", urls)

	def test_worker_never_caches_business_or_private_data(self) -> None:
		source = WORKER.read_text(encoding="utf-8")
		for prefix in ("/api/", "/private/", "/files/", "/app/"):
			self.assertIn(f'startsWith("{prefix}")', source)
		self.assertIn('url.pathname.startsWith("/assets/nexora/")', source)
		self.assertIn('cache: "no-cache"', source)
		self.assertIn("caches.delete", source)
		self.assertFalse((APP_ROOT / "public/service-worker.js").exists())

	def test_client_registers_worker_manifest_and_offline_state(self) -> None:
		source = CLIENT.read_text(encoding="utf-8")
		self.assertIn('WORKER_URL = "/nexora-service-worker.js"', source)
		self.assertIn('scope: "/app/"', source)
		self.assertIn('link.rel = "manifest"', source)
		self.assertIn("isNexoraLocation(currentLocation())", source)
		self.assertIn("nxr-offline-banner", source)
		self.assertIn('window.addEventListener("online"', source)
		self.assertIn('window.addEventListener("offline"', source)

	def test_offline_shell_precaches_every_site_wide_bundle(self) -> None:
		"""hooks.py registers app_include_js/app_include_css site-wide. The fetch
		handler still serves any of them online (network-first, cached opportunistically
		on a hit), but SHELL_ASSETS is what a genuinely offline first load gets — a
		bundle missing from it (e.g. the one that defines window.nexora.context, or the
		guided-operations wizard) means an offline install boots with a shell that's
		missing the context system or the wizard entirely."""
		hooks_source = HOOKS.read_text(encoding="utf-8")
		worker_source = WORKER.read_text(encoding="utf-8")
		shell_assets = re.findall(
			r'"(/assets/nexora/[^"]+)"', worker_source.split("SHELL_ASSETS = [", 1)[1].split("];", 1)[0]
		)

		js_block = hooks_source.split("app_include_js = [", 1)[1].split("]", 1)[0]
		css_block = hooks_source.split("app_include_css = [", 1)[1].split("]", 1)[0]
		registered = re.findall(r'"(/assets/nexora/[^"]+)"', js_block) + re.findall(
			r'"(/assets/nexora/[^"]+)"', css_block
		)

		self.assertTrue(registered, "hooks.py did not yield any registered bundle to compare against")
		self.assertEqual(
			set(),
			set(registered) - set(shell_assets),
			"a site-wide bundle is missing from the offline shell precache list",
		)

	def test_mobile_styles_include_safe_area_and_touch_targets(self) -> None:
		source = CSS.read_text(encoding="utf-8")
		self.assertIn("env(safe-area-inset-bottom)", source)
		self.assertIn("@media (max-width: 767px)", source)
		self.assertIn("min-height: 44px", source)


if __name__ == "__main__":
	unittest.main()
