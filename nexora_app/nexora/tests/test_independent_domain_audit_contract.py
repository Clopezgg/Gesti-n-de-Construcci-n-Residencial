from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
ROOT = APP_ROOT.parent.parent
AUDIT = ROOT / "docs/nexora/INDEPENDENT_DOMAIN_AUDIT.md"


class TestIndependentDomainAuditContract(unittest.TestCase):
    def test_audit_register_exists_and_has_required_domains(self) -> None:
        text = AUDIT.read_text(encoding="utf-8")
        for domain in (
            "Finanzas",
            "Compras",
            "Inventario",
            "Contratos",
            "Cierre",
            "Reportes",
            "Directorio",
            "Evidencias / avance",
            "Notificaciones",
            "Integraciones",
            "UX / PWA",
        ):
            self.assertIn(f"| {domain} |", text)

    def test_audit_register_contains_twelve_golden_paths(self) -> None:
        text = AUDIT.read_text(encoding="utf-8")
        for index in range(1, 13):
            self.assertIn(f"{index}. ", text)

    def test_audit_register_does_not_upgrade_external_dependencies_without_evidence(self) -> None:
        text = AUDIT.read_text(encoding="utf-8")
        self.assertIn("WHATSAPP REALES", text.upper())
        self.assertIn("SAP autorizado", text)
        self.assertIn("IMPLEMENTADO Y VALIDADO", text)
        self.assertIn("no se elevan artificialmente", text)

    def test_audit_register_names_the_real_canonical_layers(self) -> None:
        text = AUDIT.read_text(encoding="utf-8")
        for marker in (
            "NXR Operation Effect",
            "Libro Central",
            "purchases/",
            "inventory/",
            "contracts/",
            "reports/",
            "directory/",
            "notifications/",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
