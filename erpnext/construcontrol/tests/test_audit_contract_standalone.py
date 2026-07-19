from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / "erpnext" / "construcontrol" / "audit.py"
CONSTRUCTION = ROOT / "erpnext" / "construcontrol" / "construction.py"


class FakeDocument:
    def __init__(self, values, previous=None, ignore=False):
        self.doctype = values.get("doctype", "CC Project Profile")
        self.name = values.get("name", "CC00")
        self._values = dict(values)
        self._previous = previous
        self.flags = types.SimpleNamespace(ignore_construcontrol_audit=ignore, in_insert=False)
        self.meta = types.SimpleNamespace(fields=[])

    def as_dict(self):
        return dict(self._values)

    def get_doc_before_save(self):
        return self._previous

    def get(self, key, default=None):
        return self._values.get(key, default)


def load_audit(inserted: list[dict]):
    fake = types.ModuleType("frappe")
    fake.flags = types.SimpleNamespace(
        in_construcontrol_migration=False,
        in_construcontrol_recalculation=False,
        in_install=False,
        in_migrate=False,
    )
    fake.session = types.SimpleNamespace(user="admin@example.com")
    fake.get_roles = lambda: ["System Manager"]
    fake.db = types.SimpleNamespace(get_value=lambda *args, **kwargs: "Carlos López")

    class Insertable:
        def __init__(self, values):
            self.values = values

        def insert(self, ignore_permissions=False):
            inserted.append(self.values)
            return self

    fake.get_doc = lambda values: Insertable(values)
    utils = types.ModuleType("frappe.utils")
    utils.now_datetime = lambda: datetime(2026, 7, 19, 12, 0, 0)
    utils.today = lambda: "2026-07-19"
    fake.utils = utils
    sys.modules["frappe"] = fake
    sys.modules["frappe.utils"] = utils

    name = "cc_audit_test_module"
    spec = importlib.util.spec_from_file_location(name, SERVICE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class AuditContractTest(unittest.TestCase):
    def test_identical_update_does_not_create_audit_noise(self) -> None:
        inserted: list[dict] = []
        module = load_audit(inserted)
        previous = FakeDocument({"doctype": "CC Project Profile", "name": "CC00", "status": "active"})
        current = FakeDocument({"doctype": "CC Project Profile", "name": "CC00", "status": "active"}, previous=previous)
        module.record_event(current, "on_update")
        self.assertEqual(inserted, [])

    def test_explicit_ignore_flag_prevents_calculation_noise(self) -> None:
        inserted: list[dict] = []
        module = load_audit(inserted)
        module.record_event(FakeDocument({"doctype": "CC Project Profile", "name": "CC00"}, ignore=True), "on_update")
        self.assertEqual(inserted, [])

    def test_real_change_creates_sanitized_actor_event(self) -> None:
        inserted: list[dict] = []
        module = load_audit(inserted)
        previous = FakeDocument({"doctype": "CC Expense Control", "name": "EXP-1", "amount_hnl": 100, "api_secret": "hidden"})
        current = FakeDocument({"doctype": "CC Expense Control", "name": "EXP-1", "amount_hnl": 150, "api_secret": "hidden"}, previous=previous)
        module.record_event(current, "on_update")
        self.assertEqual(len(inserted), 1)
        event = inserted[0]
        self.assertEqual(event["actor"], "ADMIN")
        self.assertEqual(event["actor_email"], "admin@example.com")
        self.assertNotIn("hidden", event["previous_state"])
        self.assertNotIn("hidden", event["next_state"])

    def test_password_tokens_and_configuration_payloads_are_removed(self) -> None:
        module = load_audit([])
        cleaned = module._clean(
            {
                "name": "integration",
                "password": "never-store",
                "credential_secret": "never-store",
                "api_key": "never-store",
                "configuration_json": '{"secret":"never-store"}',
                "payload_json": '{"password":"never-store"}',
                "nested": {"refresh_token": "never-store", "safe": "visible"},
            }
        )
        self.assertEqual(cleaned, {"name": "integration", "nested": {"safe": "visible"}})

    def test_dashboard_read_path_cannot_persist_project_indicators(self) -> None:
        source = CONSTRUCTION.read_text(encoding="utf-8")
        read_path = source.split("def get_project_center", 1)[1]
        self.assertIn("persist=False", read_path)
        self.assertNotIn("profile.save", read_path)
        self.assertNotIn("frappe.db.set_value", read_path)


if __name__ == "__main__":
    unittest.main()
