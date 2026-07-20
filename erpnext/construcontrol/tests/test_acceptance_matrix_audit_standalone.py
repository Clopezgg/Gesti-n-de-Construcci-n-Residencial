from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[3] / "scripts" / "audit_requirements_1to1.py"
SPEC = importlib.util.spec_from_file_location("cc_audit_1to1", MODULE_PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class AcceptanceMatrixAuditTest(unittest.TestCase):
    def _root_with_matrix(self, *, state: str = "APROBADO", negative: str = "`tests/negative.py`") -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        matrix = root / "docs/reconstruction/MATRIZ_ACEPTACION_1A1.md"
        matrix.parent.mkdir(parents=True)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src/module.py").write_text("value = 1\n", encoding="utf-8")
        (root / "tests/functional.py").write_text("pass\n", encoding="utf-8")
        (root / "tests/negative.py").write_text("pass\n", encoding="utf-8")
        columns = AUDIT.MATRIX_COLUMNS
        row = {
            "Identificador": "T-01",
            "Fuente": "Orden de prueba",
            "Requisito": "Contrato verificable",
            "Módulo": "Prueba",
            "Implementación encontrada": "Implementación real",
            "Archivos": "`src/module.py`",
            "Commit": "HEAD certificado",
            "Prueba funcional": "`tests/functional.py`",
            "Prueba negativa": negative,
            "Entorno": "CI",
            "Resultado esperado": "Aceptación",
            "Resultado obtenido": "Aceptación demostrada",
            "Evidencia": "Workflow y artifact de CI",
            "Incumplimiento": "Ninguno",
            "Severidad": "Crítica",
            "Corrección aplicada": "Prueba de regresión",
            "Commit de corrección": "abc1234",
            "Resultado posterior": "Cumple 1:1",
            "Estado": state,
        }
        lines = [
            "# Matriz",
            "",
            "| " + " | ".join(columns) + " |",
            "|" + "|".join(["---"] * len(columns)) + "|",
            "| " + " | ".join(row[column] for column in columns) + " |",
        ]
        matrix.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return root

    def test_accepts_complete_approved_matrix(self) -> None:
        root = self._root_with_matrix()
        result = AUDIT.validate_acceptance_matrix(root, required_ids={"T-01"})
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(result["rows"], 1)

    def test_rejects_unresolved_state(self) -> None:
        root = self._root_with_matrix(state="NO DEMOSTRADO")
        result = AUDIT.validate_acceptance_matrix(root, required_ids={"T-01"})
        self.assertFalse(result["passed"])
        self.assertTrue(any("unresolved state" in item for item in result["failures"]))

    def test_rejects_missing_negative_evidence(self) -> None:
        root = self._root_with_matrix(negative="Sin prueba")
        result = AUDIT.validate_acceptance_matrix(root, required_ids={"T-01"})
        self.assertFalse(result["passed"])
        self.assertTrue(any("Prueba negativa" in item for item in result["failures"]))

    def test_rejects_missing_requirement_id(self) -> None:
        root = self._root_with_matrix()
        result = AUDIT.validate_acceptance_matrix(root, required_ids={"T-01", "T-02"})
        self.assertFalse(result["passed"])
        self.assertTrue(any("Missing requirement IDs" in item for item in result["failures"]))


if __name__ == "__main__":
    unittest.main()
