from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def load_module(name: str, path: Path):
	spec = importlib.util.spec_from_file_location(name, path)
	assert spec and spec.loader
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


AUDIT = load_module("cc_acceptance_audit_receipts_test", ROOT / "scripts" / "audit_requirements_1to1.py")
RECEIPTS = load_module("cc_acceptance_receipts_test", ROOT / "scripts" / "acceptance_receipts.py")
CERTIFIER = load_module("cc_acceptance_certifier_test", ROOT / "scripts" / "certify_acceptance_receipts.py")


class AcceptanceReceiptsTest(unittest.TestCase):
	CERT_SHA = "0123456789abcdef0123456789abcdef01234567"

	def _fixture(self) -> tuple[Path, Path, Path, Path]:
		temporary = tempfile.TemporaryDirectory()
		self.addCleanup(temporary.cleanup)
		root = Path(temporary.name)
		(root / "src").mkdir()
		(root / "tests").mkdir()
		(root / "src/module.py").write_text("value = 1\n", encoding="utf-8")
		(root / "tests/positive.py").write_text("assert True\n", encoding="utf-8")
		(root / "tests/negative.py").write_text("assert True\n", encoding="utf-8")
		artifacts = root / "artifacts"
		artifact_name = f"gate-t-{self.CERT_SHA}"
		artifact = artifacts / artifact_name
		artifact.mkdir(parents=True)
		(artifact / "test.log").write_text("passed\n", encoding="utf-8")
		artifact_sha, manifest = RECEIPTS.artifact_digest(artifact)
		receipts = root / "receipts"
		receipts.mkdir()
		receipt = {
			"schema_version": 1,
			"requirement_id": "T-01",
			"cert_sha": self.CERT_SHA,
			"module": "Prueba",
			"implementation": {
				"files": ["src/module.py"],
				"locator": "T-01: función verificable",
				"implementation_sha": "a" * 40,
				"correction_sha": "b" * 40,
			},
			"command": "python tests/positive.py && python tests/negative.py",
			"test": {
				"positive": ["tests/positive.py"],
				"negative": ["tests/negative.py"],
				"assertion": "Aceptación específica",
			},
			"scenarios": {
				"positive": "T-01: acepta el comportamiento esperado",
				"negative": "T-01: rechaza el comportamiento contrario",
			},
			"result": "APROBADO",
			"artifact": {
				"workflow": "CI",
				"name": artifact_name,
				"path": artifact_name,
				"sha256": artifact_sha,
				"file_count": len(manifest),
			},
		}
		receipt["receipt_sha256"] = RECEIPTS.receipt_digest(receipt)
		(receipts / "T-01.json").write_text(json.dumps(receipt), encoding="utf-8")
		matrix = root / "matrix.md"
		row = {
			"Identificador": "T-01",
			"Fuente": "Orden de prueba",
			"Requisito": "Contrato verificable",
			"Módulo": "Prueba",
			"Implementación encontrada": "T-01: función verificable",
			"Archivos": "`src/module.py`",
			"Commit": "a" * 40,
			"Prueba funcional": "`tests/positive.py`",
			"Prueba negativa": "`tests/negative.py`",
			"Entorno": "CI",
			"Resultado esperado": "Aceptación específica",
			"Resultado obtenido": f"T-01: aprobado sobre {self.CERT_SHA}",
			"Evidencia": (
				f"T-01: workflow CI; artifact {artifact_name}; artifact SHA-256 {artifact_sha}; "
				f"receipts/T-01.json SHA-256 {receipt['receipt_sha256']}"
			),
			"Incumplimiento": "T-01: escenario negativo rechazado",
			"Severidad": "Crítica",
			"Corrección aplicada": "T-01: receipt certificado",
			"Commit de corrección": "b" * 40,
			"Resultado posterior": "T-01: reproducido",
			"Estado": "APROBADO",
		}
		matrix.write_text(
			"# Matriz\n\n| "
			+ " | ".join(AUDIT.MATRIX_COLUMNS)
			+ " |\n|"
			+ "|".join(["---"] * len(AUDIT.MATRIX_COLUMNS))
			+ "|\n| "
			+ " | ".join(row[column] for column in AUDIT.MATRIX_COLUMNS)
			+ " |\n",
			encoding="utf-8",
		)
		return root, matrix, receipts, artifacts

	def test_validates_specific_same_sha_receipt_and_artifact_digest(self) -> None:
		root, matrix, receipts, artifacts = self._fixture()
		result = AUDIT.validate_acceptance_receipts(
			root,
			matrix_path=matrix,
			receipts_dir=receipts,
			artifacts_root=artifacts,
			cert_sha=self.CERT_SHA,
			required_ids={"T-01"},
		)
		self.assertTrue(result["passed"], result["failures"])
		self.assertEqual(result["receipts"], 1)

	def test_rejects_artifact_tampering(self) -> None:
		root, matrix, receipts, artifacts = self._fixture()
		artifact = next(artifacts.iterdir())
		(artifact / "test.log").write_text("tampered\n", encoding="utf-8")
		result = AUDIT.validate_acceptance_receipts(
			root,
			matrix_path=matrix,
			receipts_dir=receipts,
			artifacts_root=artifacts,
			cert_sha=self.CERT_SHA,
			required_ids={"T-01"},
		)
		self.assertFalse(result["passed"])
		self.assertTrue(any("artifact digest mismatch" in failure for failure in result["failures"]))

	def test_materializes_and_validates_all_224_specific_receipts(self) -> None:
		with tempfile.TemporaryDirectory() as temporary:
			base = Path(temporary)
			artifacts = base / "artifacts"
			for prefix in CERTIFIER.COMMAND_BY_ARTIFACT:
				directory = artifacts / f"{prefix}-{self.CERT_SHA}"
				directory.mkdir(parents=True)
				(directory / "result.log").write_text(f"{prefix}=passed\n", encoding="utf-8")
			receipts = base / "receipts"
			certified_matrix = base / "certified-matrix.md"
			result = CERTIFIER.certify(
				source_matrix=ROOT / "docs/reconstruction/MATRIZ_ACEPTACION_1A1.md",
				artifacts_root=artifacts,
				receipts_dir=receipts,
				certified_matrix=certified_matrix,
				cert_sha=self.CERT_SHA,
			)
			self.assertEqual(result["receipts"], 224)
			matrix_result = AUDIT.validate_acceptance_matrix(
				ROOT,
				matrix_path=certified_matrix,
			)
			self.assertTrue(matrix_result["passed"], matrix_result["failures"])
			receipt_result = AUDIT.validate_acceptance_receipts(
				ROOT,
				matrix_path=certified_matrix,
				receipts_dir=receipts,
				artifacts_root=artifacts,
				cert_sha=self.CERT_SHA,
			)
			self.assertTrue(receipt_result["passed"], receipt_result["failures"])
			self.assertEqual(receipt_result["receipts"], 224)
			digests = {
				json.loads(path.read_text(encoding="utf-8"))["receipt_sha256"]
				for path in receipts.glob("*.json")
			}
			self.assertEqual(len(digests), 224)


if __name__ == "__main__":
	unittest.main()
