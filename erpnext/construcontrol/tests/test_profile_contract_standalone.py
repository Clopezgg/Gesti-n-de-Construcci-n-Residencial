from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / "erpnext" / "construcontrol" / "profile.py"
PAGE = ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_profile" / "construcontrol_profile.js"
INSTALL = ROOT / "erpnext" / "construcontrol" / "install.py"
SHELL = ROOT / "erpnext" / "public" / "js" / "construcontrol_mobile.js"


class ProfileContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = PROFILE.read_text(encoding="utf-8")
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.install = INSTALL.read_text(encoding="utf-8")
        cls.shell = SHELL.read_text(encoding="utf-8")

    def test_profile_is_self_service_only(self) -> None:
        self.assertIn("frappe.session.user", self.profile)
        self.assertIn("update_my_profile", self.profile)
        self.assertNotIn("target_user", self.profile)
        self.assertNotIn("roles =", self.profile.split("def update_my_profile", 1)[1])

    def test_profile_exposes_professional_information(self) -> None:
        for phrase in (
            "recent_activity",
            "projects",
            "two_factor_enabled",
            "last_login",
            "mobile_no",
            "time_zone",
        ):
            self.assertIn(phrase, self.profile)
            self.assertIn(phrase.replace("_", "-") if phrase == "mobile_no" else phrase.split("_")[0], self.page)

    def test_profile_page_stays_inside_construcontrol(self) -> None:
        self.assertIn('"construcontrol-profile"', self.install)
        self.assertIn("cc-profile-button", self.shell)
        self.assertIn('go(["construcontrol-profile"])', self.shell)
        self.assertFalse((ROOT / "erpnext" / "public" / "js" / "construcontrol_profile_bridge.js").exists())


if __name__ == "__main__":
    unittest.main()
