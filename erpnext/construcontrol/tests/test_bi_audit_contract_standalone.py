from __future__ import annotations

import ast
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORTING = ROOT / "erpnext" / "construcontrol" / "reporting.py"
REPORTING_EXPORTS = ROOT / "erpnext" / "construcontrol" / "reporting_exports.py"
REPORTING_NOTIFICATIONS = ROOT / "erpnext" / "construcontrol" / "reporting_notifications.py"
REPORTING_UTILS = ROOT / "erpnext" / "construcontrol" / "reporting_utils.py"
EXECUTIVE = ROOT / "erpnext" / "construcontrol" / "executive.py"
AUDIT = ROOT / "erpnext" / "construcontrol" / "audit.py"
HOOKS = ROOT / "erpnext" / "hooks.py"
PAGE = (
    ROOT
    / "erpnext"
    / "construcontrol"
    / "page"
    / "construcontrol_reporting_center"
    / "construcontrol_reporting_center.js"
)


def load_reporting_utils():
    spec = importlib.util.spec_from_file_location("cc_reporting_utils_test", REPORTING_UTILS)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class BIAndAuditContractTest(unittest.TestCase):
    def test_reporting_and_audit_parse(self) -> None:
        for path in (
            REPORTING,
            REPORTING_EXPORTS,
            REPORTING_NOTIFICATIONS,
            EXECUTIVE,
            AUDIT,
        ):
            ast.parse(path.read_text(encoding="utf-8"))

    def test_formula_injection_is_neutralized(self) -> None:
        module = load_reporting_utils()
        for value in ("=SUM(A1:A2)", "+1", "-2", "@cmd"):
            self.assertTrue(module.sanitize_csv_cell(value).startswith("'"))
        self.assertEqual(module.sanitize_csv_cell("Normal"), "Normal")

    def test_report_key_is_deterministic_and_sensitive_to_sources(self) -> None:
        module = load_reporting_utils()
        first = module.deterministic_report_key(
            "financial", "P1", "2026-07-01", "2026-07-19", {"x": 1}
        )
        second = module.deterministic_report_key(
            "financial", "P1", "2026-07-01", "2026-07-19", {"x": 1}
        )
        changed = module.deterministic_report_key(
            "financial", "P1", "2026-07-01", "2026-07-19", {"x": 2}
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)

    def test_export_is_private_and_project_attached(self) -> None:
        source = REPORTING_EXPORTS.read_text(encoding="utf-8")
        self.assertIn('"is_private": 1', source)
        self.assertIn('"attached_to_doctype": "CC Project Profile"', source)
        self.assertIn("_EXPORT_ROLES", source)
        self.assertIn("_require_exact_project", source)

    def test_dashboard_reuses_canonical_reporting_service(self) -> None:
        source = EXECUTIVE.read_text(encoding="utf-8")
        self.assertIn(
            "from erpnext.construcontrol.reporting import get_reporting_summary", source
        )
        self.assertNotIn("expense_amounts", source)
        self.assertIn('counts["quality_issues"]', source)
        self.assertIn('counts["closings"]', source)
        self.assertIn("alerts[:4]", source)

    def test_audit_covers_business_transitions_and_identity(self) -> None:
        source = AUDIT.read_text(encoding="utf-8")
        for action in (
            "CREATE",
            "UPDATE",
            "APPROVE",
            "REJECT",
            "PAY",
            "CANCEL",
            "REVERSE",
            "DELETE",
        ):
            self.assertIn(f'"{action}"', source)
        for field in (
            "module",
            "origin",
            "correlation_id",
            "fingerprint",
            "previous_state",
            "next_state",
        ):
            self.assertIn(f'"{field}"', source)
        self.assertIn("protect_audit_record", source)

    def test_hooks_protect_audit_records(self) -> None:
        source = HOOKS.read_text(encoding="utf-8")
        self.assertIn('"CC Audit Log"', source)
        self.assertIn("erpnext.construcontrol.audit.protect_audit_record", source)

    def test_reporting_page_has_working_export_and_request_guard(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        self.assertIn("export_report_csv", source)
        self.assertIn("reportingRequest", source)
        self.assertIn("get_reporting_context", source)
        for report in (
            "FI03 Cuentas por Pagar",
            "PR02 Presupuesto vs Ejecución",
            "PR03 Fases y Desviaciones",
            "MM03 Inventario Crítico",
            "FI04 Ingresos y Conciliación",
        ):
            self.assertIn(report, source)


if __name__ == "__main__":
    unittest.main()
