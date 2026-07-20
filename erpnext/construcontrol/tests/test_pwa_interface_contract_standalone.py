from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "erpnext" / "public" / "construcontrol" / "manifest.webmanifest"
DEPLOY_VERSION = ROOT / "erpnext" / "public" / "construcontrol" / "deploy-version.json"
SERVICE_WORKER = ROOT / "erpnext" / "www" / "construcontrol-service-worker.js"
PWA = ROOT / "erpnext" / "public" / "js" / "construcontrol_pwa.js"
MOBILE = ROOT / "erpnext" / "public" / "js" / "construcontrol_mobile.js"
UX = ROOT / "erpnext" / "public" / "js" / "construcontrol_ux.js"
CSS = ROOT / "erpnext" / "public" / "css" / "construcontrol_canonical.css"
HOOKS = ROOT / "erpnext" / "hooks.py"


class PWAInterfaceContractTest(unittest.TestCase):
    def test_manifest_is_installable_and_scoped_to_construcontrol_app(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertTrue(manifest["start_url"].startswith(manifest["scope"]))
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["lang"], "es-HN")
        sizes = {row["sizes"] for row in manifest["icons"]}
        self.assertTrue({"192x192", "512x512"}.issubset(sizes))
        self.assertTrue(all("maskable" in row["purpose"] for row in manifest["icons"]))
        self.assertEqual(len(manifest["shortcuts"]), 3)

    def test_deploy_version_matches_worker_and_client(self) -> None:
        deploy = json.loads(DEPLOY_VERSION.read_text(encoding="utf-8"))["version"]
        worker = SERVICE_WORKER.read_text(encoding="utf-8")
        client = PWA.read_text(encoding="utf-8")
        self.assertIn(f'VERSION = "{deploy}"', worker)
        self.assertIn(f'VERSION = "{deploy}"', client)
        self.assertIn("deploy-version.json", client)
        self.assertIn('cache: "no-store"', client)

    def test_service_worker_never_caches_business_or_private_data(self) -> None:
        source = SERVICE_WORKER.read_text(encoding="utf-8")
        for path in ("/api/", "/private/", "/files/", "/app/"):
            self.assertIn(f'startsWith("{path}")', source)
        self.assertIn("CACHE_PREFIX", source)
        self.assertIn("caches.delete", source)
        self.assertIn("self.skipWaiting()", source)
        self.assertIn("self.clients.claim()", source)
        self.assertIn('cache: "no-cache"', source)

    def test_client_registers_root_worker_only_inside_construcontrol(self) -> None:
        source = PWA.read_text(encoding="utf-8")
        self.assertIn('WORKER_URL = "/construcontrol-service-worker.js"', source)
        self.assertIn('scope: "/"', source)
        self.assertIn("isConstruControlRoute()", source)
        self.assertIn("updatefound", source)
        self.assertIn("controllerchange", source)
        self.assertIn("sessionStorage", source)
        self.assertIn("CLEAR_OLD_CACHES", source)

    def test_interactions_cover_navigation_forms_modals_and_duplicate_guard(
        self,
    ) -> None:
        mobile = MOBILE.read_text(encoding="utf-8")
        ux = UX.read_text(encoding="utf-8")
        pwa = PWA.read_text(encoding="utf-8")
        for command in ("close", "cancel", "save", "save-new"):
            self.assertIn(f'data-cc-command="{command}"', ux)
        self.assertIn("goBackFromCurrent", ux)
        self.assertIn("ensureModalCloseButtons", ux)
        self.assertIn("ensureMissingPageRecovery", ux)
        self.assertIn("ACTION_LOCK_MS", pwa)
        self.assertIn("stopImmediatePropagation", pwa)
        self.assertIn("cc-mobile-nav", mobile)
        self.assertIn("cc-desktop-sidebar", mobile)
        self.assertIn("cc-app-topbar", mobile)

    def test_shell_covers_dashboard_profile_and_role_scoped_navigation(self) -> None:
        source = MOBILE.read_text(encoding="utf-8")
        for marker in (
            "construcontrol-dashboard",
            "construcontrol-profile",
            "construcontrol-reporting-center",
            "CC Audit Log",
            "isCC(current)",
            "cc-more-sheet",
        ):
            self.assertIn(marker, source)
        self.assertIn("roleSet", source)
        self.assertIn("frappe.set_route", source)

    def test_camera_gallery_dirty_reload_and_offline_states_are_explicit(self) -> None:
        source = PWA.read_text(encoding="utf-8")
        self.assertIn('input[type="file"]', source)
        self.assertIn('input.accept = "image/*,application/pdf"', source)
        self.assertIn('removeAttribute("capture")', source)
        self.assertIn("beforeunload", source)
        self.assertIn("cc-offline-banner", source)
        self.assertIn('window.addEventListener("online"', source)
        self.assertIn('window.addEventListener("offline"', source)

    def test_styles_are_scoped_and_mobile_safe(self) -> None:
        source = CSS.read_text(encoding="utf-8")
        self.assertIn("body.cc-construcontrol-route", source)
        self.assertIn("@media (max-width:767px)", source)
        self.assertIn("env(safe-area-inset-bottom)", source)
        self.assertIn("overflow-x:auto", source)
        unscoped_resets = re.findall(r"(?m)^\s*(?:body|html|\*)\s*\{", source)
        self.assertEqual(unscoped_resets, [])

    def test_pwa_client_is_loaded_after_shell_and_ux(self) -> None:
        source = HOOKS.read_text(encoding="utf-8")
        mobile = source.index("construcontrol_mobile.js")
        ux = source.index("construcontrol_ux.js")
        pwa = source.index("construcontrol_pwa.js")
        self.assertLess(mobile, ux)
        self.assertLess(ux, pwa)


if __name__ == "__main__":
    unittest.main()
