from __future__ import annotations

import json
import pathlib
import re
import unittest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
PAGE_ROOT = PACKAGE / "nexora/page"
WORKSPACE = PACKAGE / "nexora/workspace/nexora/nexora.json"
TOP_NAV = PACKAGE / "public/js/nexora.js"
ROLE_FIXTURES = PACKAGE / "fixtures/role.json"
NEXORA_ROLES = {row["name"] for row in json.loads(ROLE_FIXTURES.read_text(encoding="utf-8"))}


def scrub(name: str) -> str:
	"""Mirror of frappe.scrub, used by Frappe to resolve Page assets on disk."""
	return name.replace(" ", "_").replace("-", "_").lower()


def page_definitions() -> dict[str, dict]:
	pages: dict[str, dict] = {}
	for folder in sorted(path for path in PAGE_ROOT.iterdir() if path.is_dir()):
		definition = folder / f"{folder.name}.json"
		if not definition.is_file():
			continue
		pages[folder.name] = json.loads(definition.read_text(encoding="utf-8"))
	return pages


class TestPageRegistryContract(unittest.TestCase):
	"""Guards the wiring between Page records, their assets and the workspace.

	Frappe resolves a Page's script with ``frappe.scrub(page.name)``, so a page named
	``nexora-dashboard`` is only ever loaded from ``page/nexora_dashboard/nexora_dashboard.js``.
	A hyphenated folder is imported into the Page table but silently loads an empty
	script, which renders a blank screen instead of failing.
	"""

	def test_every_page_folder_matches_the_scrubbed_page_name(self) -> None:
		pages = page_definitions()
		self.assertTrue(pages, "no NEXORA pages were discovered")
		for folder, payload in pages.items():
			with self.subTest(page=folder):
				self.assertEqual("Page", payload["doctype"])
				self.assertEqual(scrub(payload["name"]), folder)
				self.assertEqual(payload["name"], payload["page_name"])
				self.assertEqual("NEXORA", payload["module"])
				self.assertEqual("Yes", payload["standard"])
				self.assertTrue(payload.get("title"), "a page without a title renders unlabelled")

	def test_every_page_restricts_access_to_nexora_roles(self) -> None:
		"""An empty roles table makes Page.has_permission return True for every user."""
		for folder, payload in page_definitions().items():
			with self.subTest(page=folder):
				roles = {row["role"] for row in payload.get("roles", [])}
				self.assertTrue(roles, "the page is reachable by any authenticated user")
				self.assertTrue(
					roles.issubset(NEXORA_ROLES),
					f"unexpected roles on {folder}: {sorted(roles - NEXORA_ROLES)}",
				)

	def test_every_page_ships_a_loadable_script_and_python_package(self) -> None:
		for folder, payload in page_definitions().items():
			with self.subTest(page=folder):
				script = PAGE_ROOT / folder / f"{folder}.js"
				self.assertTrue(script.is_file(), f"missing {script.name}")
				self.assertIn(
					f'frappe.pages["{payload["name"]}"]',
					script.read_text(encoding="utf-8"),
					"the script must register itself under the Page record name",
				)
				self.assertTrue((PAGE_ROOT / folder / "__init__.py").is_file())

	def test_no_build_step_relocates_page_assets(self) -> None:
		"""La imagen copiaba las cuatro páginas rotas a carpetas con guion bajo al
		construirse, tapando en el contenedor un defecto del árbol. Con las páginas ya
		en su sitio, cualquier reaparición de ese parche indica que el árbol volvió a
		romperse."""
		for name in ("Dockerfile.nexora", "Dockerfile"):
			recipe = PACKAGE.parents[1] / name
			if not recipe.is_file():
				continue
			with self.subTest(dockerfile=name):
				self.assertNotRegex(
					recipe.read_text(encoding="utf-8"),
					r"page/nexora-[a-z]+",
					"la imagen no debe reubicar assets de página al construirse",
				)

	def test_no_hyphenated_page_asset_remains_on_disk(self) -> None:
		# El bytecode compilado lleva guion en su nombre (`cpython-311.pyc`) y no es un
		# asset de página: contarlo haría fallar el contrato en cualquier árbol donde ya
		# se haya ejecutado Python.
		strays = [
			str(path.relative_to(PACKAGE))
			for path in PAGE_ROOT.rglob("*")
			if "-" in path.name and path.name != ".gitkeep" and "__pycache__" not in path.parts
		]
		self.assertEqual([], strays)

	def test_every_page_is_reachable_from_the_workspace(self) -> None:
		workspace = json.loads(WORKSPACE.read_text(encoding="utf-8"))
		linked = {row["link_to"] for row in workspace["shortcuts"] if row["type"] == "Page"}
		declared = {payload["name"] for payload in page_definitions().values()}
		self.assertEqual(
			set(),
			declared - linked,
			"every NEXORA page needs a workspace shortcut or users cannot reach it",
		)

	def test_every_page_is_reachable_from_the_persistent_top_nav(self) -> None:
		"""nexora.js renders a top navigation bar on every NEXORA screen
		(``isNexoraLocation``), independent of the workspace. A page missing from its
		``destinations`` array is only reachable via the workspace or a deep link —
		the persistent nav and the workspace must agree on what counts as
		reachable, or a page effectively hides itself from normal navigation."""
		script = TOP_NAV.read_text(encoding="utf-8")
		body = script.split("const destinations = [", 1)[1].split("];", 1)[0]
		linked = set(re.findall(r'href:\s*"/app/(nexora-[a-z-]+)"', body))
		declared = {payload["name"] for payload in page_definitions().values()}
		self.assertEqual(
			set(),
			declared - linked,
			"every NEXORA page needs a top-nav entry or it is invisible outside the workspace",
		)
		self.assertEqual(set(), linked - declared, "the top nav links to a page that does not exist")

	def test_every_workspace_shortcut_is_rendered_and_resolvable(self) -> None:
		workspace = json.loads(WORKSPACE.read_text(encoding="utf-8"))
		shortcuts = {row["label"]: row for row in workspace["shortcuts"]}
		rendered = {
			block["data"]["shortcut_name"]
			for block in json.loads(workspace["content"])
			if block["type"] == "shortcut"
		}
		self.assertEqual(
			set(),
			set(shortcuts) - rendered,
			"a shortcut absent from the workspace content is invisible to the user",
		)
		self.assertEqual(set(), rendered - set(shortcuts), "workspace content renders unknown shortcuts")

		pages = {payload["name"] for payload in page_definitions().values()}
		doctype_payloads = (
			json.loads(definition.read_text(encoding="utf-8"))
			for definition in (PACKAGE / "nexora/doctype").glob("*/*.json")
		)
		doctypes = {payload["name"] for payload in doctype_payloads if payload.get("doctype") == "DocType"}
		for label, row in shortcuts.items():
			with self.subTest(shortcut=label):
				if row["type"] == "Page":
					self.assertIn(row["link_to"], pages)
				elif row["type"] == "DocType" and row["link_to"].startswith("NXR "):
					self.assertIn(row["link_to"], doctypes)

	def test_client_navigation_targets_point_at_existing_pages(self) -> None:
		pages = {payload["name"] for payload in page_definitions().values()}
		pattern = re.compile(r'(?:data-route="|set_route\("|href: "/app/)(nexora-[a-z-]+)')
		offenders: list[str] = []
		for script in sorted(PACKAGE.rglob("*.js")):
			for match in pattern.finditer(script.read_text(encoding="utf-8")):
				if match.group(1) not in pages:
					offenders.append(f"{script.relative_to(PACKAGE)} -> {match.group(1)}")
		self.assertEqual([], offenders, "the UI routes to pages that do not exist")


if __name__ == "__main__":
	unittest.main()
