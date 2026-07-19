from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / "erpnext" / "public" / "construcontrol"
MANIFEST = PUBLIC / "manifest.webmanifest"
SHELL = ROOT / "erpnext" / "public" / "js" / "construcontrol_mobile.js"
CSS = ROOT / "erpnext" / "public" / "css" / "construcontrol.css"


class PwaContractTest(unittest.TestCase):
    def test_manifest_is_installable_and_uses_png_icons(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["scope"], "/app/")
        self.assertTrue(manifest["start_url"].startswith("/app/construcontrol-dashboard"))
        sizes = {icon["sizes"] for icon in manifest["icons"]}
        self.assertEqual(sizes, {"192x192", "512x512"})
        self.assertTrue(all(icon["type"] == "image/png" for icon in manifest["icons"]))

    def test_iphone_and_android_icons_exist(self) -> None:
        for name in (
            "favicon-32.png",
            "apple-touch-icon-180.png",
            "icon-192.png",
            "icon-512.png",
        ):
            path = PUBLIC / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 100, name)

    def test_mobile_shell_uses_native_icon_and_safe_area(self) -> None:
        shell = SHELL.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("apple-touch-icon-180.png", shell)
        self.assertIn("apple-mobile-web-app-capable", shell)
        self.assertIn("safe-area-inset-bottom", css)
        self.assertIn("100dvh", css)


if __name__ == "__main__":
    unittest.main()
