from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / "erpnext" / "construcontrol" / "business_events.py"
HOOKS = ROOT / "erpnext" / "hooks.py"
UX = ROOT / "erpnext" / "public" / "js" / "construcontrol_ux.js"
DASHBOARD = (
	ROOT / "erpnext" / "construcontrol" / "page" / "construcontrol_dashboard" / "construcontrol_dashboard.js"
)


class Document:
	doctype = "CC Expense Control"
	name = "CC-EXP-0001"
	project = "PROJ-0001"

	def __init__(self, previous=None):
		self.previous = previous

	def get_doc_before_save(self):
		return self.previous


def load_service(published: list[dict]):
	frappe = types.ModuleType("frappe")
	frappe.publish_realtime = lambda event, **kwargs: published.append({"event": event, **kwargs})
	utils = types.ModuleType("frappe.utils")
	utils.now_datetime = lambda: datetime(2026, 7, 20, 12, 30, 45)
	spec = importlib.util.spec_from_file_location("cc_business_events_test", SERVICE)
	module = importlib.util.module_from_spec(spec)
	assert spec and spec.loader
	with patch.dict(sys.modules, {"frappe": frappe, "frappe.utils": utils}):
		spec.loader.exec_module(module)
	return module


class BusinessEventsTest(unittest.TestCase):
	def test_payload_is_exact_versioned_project_scoped_and_secret_free(self) -> None:
		service = load_service([])
		payload = service.build_business_event(
			Document(),
			"on_update",
			occurred_at=datetime(2026, 7, 20, 12, 30, 45),
		)
		self.assertEqual(
			payload,
			{
				"version": 1,
				"project": "PROJ-0001",
				"domain": "FI02",
				"document_type": "CC Expense Control",
				"document_name": "CC-EXP-0001",
				"action": "created",
				"occurred_at": "2026-07-20T12:30:45",
			},
		)
		self.assertFalse({"password", "token", "email", "amount"} & set(payload))

	def test_updates_and_out_of_scope_documents_are_distinguished(self) -> None:
		service = load_service([])
		self.assertEqual(service.build_business_event(Document(previous=object()))["action"], "updated")
		outside = types.SimpleNamespace(doctype="User", name="user@example.com", project="PROJ-0001")
		self.assertIsNone(service.build_business_event(outside))
		unscoped = types.SimpleNamespace(doctype="CC Expense Control", name="CC-EXP-0002")
		self.assertIsNone(service.build_business_event(unscoped))

	def test_publication_is_queued_after_commit(self) -> None:
		published: list[dict] = []
		service = load_service(published)
		service.publish_business_event(Document(), "on_update")
		self.assertEqual(len(published), 1)
		self.assertEqual(published[0]["event"], "construcontrol:business-event:v1")
		self.assertIs(published[0]["after_commit"], True)
		self.assertEqual(
			set(published[0]["message"]),
			{"version", "project", "domain", "document_type", "document_name", "action", "occurred_at"},
		)

	def test_hooks_and_client_refresh_canonical_server_aggregates(self) -> None:
		hooks = HOOKS.read_text(encoding="utf-8")
		ux = UX.read_text(encoding="utf-8")
		dashboard = DASHBOARD.read_text(encoding="utf-8")
		self.assertIn("business_events.publish_business_event", hooks)
		self.assertIn("frappe.realtime.on(BUSINESS_EVENT_NAME", ux)
		self.assertIn('new CustomEvent("construcontrol:refresh-canonical"', ux)
		self.assertIn('window.addEventListener("construcontrol:refresh-canonical"', dashboard)
		self.assertIn("loadDashboard();", dashboard)


if __name__ == "__main__":
	unittest.main()
