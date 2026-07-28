from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
MANIFEST = APP_ROOT / "public/manifest.json"
CLIENT = APP_ROOT / "public/js/nexora.js"
WORKER = APP_ROOT / "www/nexora-service-worker.js"
CSS = APP_ROOT / "public/css/nexora.css"


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

	def test_mobile_styles_include_safe_area_and_touch_targets(self) -> None:
		source = CSS.read_text(encoding="utf-8")
		self.assertIn("env(safe-area-inset-bottom)", source)
		self.assertIn("@media (max-width: 767px)", source)
		self.assertIn("min-height: 44px", source)


if __name__ == "__main__":
	unittest.main()
