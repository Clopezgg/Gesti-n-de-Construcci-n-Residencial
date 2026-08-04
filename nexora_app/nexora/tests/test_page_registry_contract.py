from __future__ import annotations

import json
import pathlib
import re
import unittest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
PAGE_ROOT = PACKAGE / "nexora/page"
WORKSPACE = PACKAGE / "nexora/workspace/nexora/nexora.json"
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

	def test_no_hyphenated_page_asset_remains_on_disk(self) -> None:
		strays = [
			str(path.relative_to(PACKAGE))
			for path in PAGE_ROOT.rglob("*")
			if "-" in path.name and path.name != ".gitkeep"
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
		doctypes = {
			json.loads(definition.read_text(encoding="utf-8"))["name"]
			for definition in (PACKAGE / "nexora/doctype").glob("*/*.json")
			if json.loads(definition.read_text(encoding="utf-8")).get("doctype") == "DocType"
		}
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
