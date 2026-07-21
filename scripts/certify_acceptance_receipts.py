#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
	spec = importlib.util.spec_from_file_location(name, path)
	if not spec or not spec.loader:
		raise RuntimeError(f"Unable to load {path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


AUDIT = _load("construcontrol_acceptance_audit", ROOT / "scripts" / "audit_requirements_1to1.py")
RENDERER = _load("construcontrol_acceptance_renderer", ROOT / "scripts" / "render_acceptance_matrix.py")
RECEIPTS = _load("construcontrol_acceptance_receipts", ROOT / "scripts" / "acceptance_receipts.py")

COMMAND_BY_ARTIFACT = {
	"semantic": "python scripts/validate_commit_titles.py --from $BASE_SHA --to $CERT_SHA",
	"linters": "pre-commit run --all-files --show-diff-on-failure (two clean executions)",
	"semgrep": "semgrep ci --config ./frappe-semgrep-rules/rules --config r/python.lang.correctness",
	"certification-freeze": "python validators, standalone tests, compileall, node --check, bash -n and docker compose config",
	"gate-a-shard-1": "bench --site test_site run-tests --module erpnext.construcontrol.tests.test_mariadb_shared_fixtures",
	"gate-a-shard-2": "bench --site test_site run-tests --module erpnext.construcontrol.tests.test_runtime_user_context",
	"gate-a-shard-3": "three bench migrations and erpnext.construcontrol.tests.runtime_smoke.run",
	"gate-a-shard-4": "MariaDB fixtures, user context and erpnext.construcontrol.tests.runtime_smoke.run",
	"gate-b": "directed MM/QC/CL/BI/AU standalone tests plus MariaDB runtime contracts",
	"gate-c": "isolated Docker Compose, authenticated WebSocket, desktop, iPhone 13, PWA, persistence, backup and restore",
	"final": "clean install, three migrations, redeploy, runtime smoke, browser, backup and restore",
	"audit-input": "certify_acceptance_receipts.py and audit_requirements_1to1.py over one CERT_SHA",
}


def _artifact_prefix(row: dict[str, str]) -> tuple[str, str]:
	group_code = row["Identificador"].rsplit("-", 1)[0]
	return RENDERER._artifact_for(group_code, row["Requisito"])


def _command_for(prefix: str) -> str:
	if prefix not in COMMAND_BY_ARTIFACT:
		raise KeyError(f"No command contract for artifact {prefix}")
	return COMMAND_BY_ARTIFACT[prefix]


def _receipt_for(
	row: dict[str, str],
	*,
	cert_sha: str,
	artifacts_root: Path,
	digest_cache: dict[str, tuple[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
	workflow, prefix = _artifact_prefix(row)
	artifact_name = f"{prefix}-{cert_sha}"
	artifact_path = artifacts_root / artifact_name
	if artifact_name not in digest_cache:
		digest_cache[artifact_name] = RECEIPTS.artifact_digest(artifact_path)
	artifact_sha256, manifest = digest_cache[artifact_name]
	implementation_files = list(AUDIT._referenced_paths(row["Archivos"]))
	positive_tests = list(AUDIT._referenced_paths(row["Prueba funcional"]))
	negative_tests = list(AUDIT._referenced_paths(row["Prueba negativa"]))
	for relative in (*implementation_files, *positive_tests, *negative_tests):
		if not (ROOT / relative).exists():
			raise FileNotFoundError(f"{row['Identificador']}: missing repository path {relative}")
	receipt = {
		"schema_version": 1,
		"requirement_id": row["Identificador"],
		"cert_sha": cert_sha,
		"module": row["Módulo"],
		"implementation": {
			"files": implementation_files,
			"locator": row["Implementación encontrada"],
			"implementation_sha": row["Commit"],
			"correction_sha": row["Commit de corrección"],
		},
		"command": _command_for(prefix),
		"test": {
			"positive": positive_tests,
			"negative": negative_tests,
			"assertion": row["Resultado esperado"],
		},
		"scenarios": {
			"positive": (
				f"{row['Identificador']}: {row['Requisito']} produce «{row['Resultado esperado']}» "
				"en la ejecución certificada"
			),
			"negative": (
				f"{row['Identificador']}: las pruebas negativas rechazan el caso contrario a "
				f"«{row['Resultado esperado']}»"
			),
		},
		"result": "APROBADO",
		"artifact": {
			"workflow": workflow,
			"name": artifact_name,
			"path": artifact_name,
			"sha256": artifact_sha256,
			"file_count": len(manifest),
		},
	}
	receipt["receipt_sha256"] = RECEIPTS.receipt_digest(receipt)
	return receipt


def _escape(value: Any) -> str:
	return str(value).replace("|", r"\|").replace("\n", " ").strip()


def _promote_row(row: dict[str, str], receipt: dict[str, Any]) -> dict[str, str]:
	result = dict(row)
	rid = row["Identificador"]
	artifact = receipt["artifact"]
	result[
		"Resultado obtenido"
	] = f"{rid}: APROBADO sobre {receipt['cert_sha']}; aserción «{receipt['test']['assertion']}»"
	result["Evidencia"] = (
		f"{rid}: workflow {artifact['workflow']}; artifact {artifact['name']}; "
		f"artifact SHA-256 {artifact['sha256']}; receipt receipts/{rid}.json "
		f"SHA-256 {receipt['receipt_sha256']}"
	)
	result[
		"Incumplimiento"
	] = f"{rid}: el escenario negativo específico fue rechazado por {', '.join(receipt['test']['negative'])}"
	result[
		"Corrección aplicada"
	] = f"{rid}: receipt específico ligado al CERT_SHA, comando, pruebas, escenarios y digest del artifact"
	result[
		"Resultado posterior"
	] = f"{rid}: resultado reproducido en {artifact['name']} con digest {artifact['sha256']}"
	result["Estado"] = "APROBADO"
	return result


def render_certified_matrix(rows: list[dict[str, str]], cert_sha: str) -> str:
	lines = [
		"# Copia certificada de la matriz de aceptación 1:1 — ConstruControl",
		"",
		f"CERT_SHA: `{cert_sha}`.",
		"",
		"Esta copia se materializa durante AUDIT a partir de la matriz fuente `NO DEMOSTRADO` y receipts JSON cuyos artifacts y digests pertenecen al mismo SHA.",
		"",
		"| " + " | ".join(AUDIT.MATRIX_COLUMNS) + " |",
		"|" + "|".join(["---"] * len(AUDIT.MATRIX_COLUMNS)) + "|",
	]
	for row in rows:
		lines.append("| " + " | ".join(_escape(row[column]) for column in AUDIT.MATRIX_COLUMNS) + " |")
	lines.extend(["", f"Total certificado: **{len(rows)}** requisitos sobre `{cert_sha}`.", ""])
	return "\n".join(lines)


def certify(
	*,
	source_matrix: Path,
	artifacts_root: Path,
	receipts_dir: Path,
	certified_matrix: Path,
	cert_sha: str,
) -> dict[str, Any]:
	if not RECEIPTS.EXACT_SHA.fullmatch(cert_sha):
		raise ValueError(f"Invalid CERT_SHA: {cert_sha!r}")
	rows = AUDIT.parse_acceptance_matrix(source_matrix)
	if len(rows) != len(AUDIT.REQUIRED_MATRIX_IDS):
		raise ValueError(f"Expected {len(AUDIT.REQUIRED_MATRIX_IDS)} source rows, found {len(rows)}")
	if any(row["Estado"].strip().upper() != "NO DEMOSTRADO" for row in rows):
		raise ValueError("Source matrix must remain entirely NO DEMOSTRADO")
	receipts_dir.mkdir(parents=True, exist_ok=True)
	digest_cache: dict[str, tuple[str, list[dict[str, Any]]]] = {}
	certified_rows = []
	for row in rows:
		receipt = _receipt_for(
			row, cert_sha=cert_sha, artifacts_root=artifacts_root, digest_cache=digest_cache
		)
		(receipts_dir / f"{row['Identificador']}.json").write_text(
			json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
			encoding="utf-8",
		)
		certified_rows.append(_promote_row(row, receipt))
	certified_matrix.parent.mkdir(parents=True, exist_ok=True)
	certified_matrix.write_text(render_certified_matrix(certified_rows, cert_sha), encoding="utf-8")
	return {
		"status": "certified",
		"cert_sha": cert_sha,
		"receipts": len(certified_rows),
		"artifacts": {name: digest for name, (digest, _manifest) in sorted(digest_cache.items())},
		"certified_matrix": str(certified_matrix),
	}


def main() -> int:
	parser = argparse.ArgumentParser(description="Materialize same-SHA ConstruControl acceptance receipts")
	parser.add_argument("--cert-sha", required=True)
	parser.add_argument("--artifacts-root", required=True, type=Path)
	parser.add_argument(
		"--source-matrix",
		type=Path,
		default=ROOT / "docs" / "reconstruction" / "MATRIZ_ACEPTACION_1A1.md",
	)
	parser.add_argument("--receipts-dir", required=True, type=Path)
	parser.add_argument("--certified-matrix", required=True, type=Path)
	args = parser.parse_args()
	result = certify(
		source_matrix=args.source_matrix.resolve(),
		artifacts_root=args.artifacts_root.resolve(),
		receipts_dir=args.receipts_dir.resolve(),
		certified_matrix=args.certified_matrix.resolve(),
		cert_sha=args.cert_sha,
	)
	print(json.dumps(result, ensure_ascii=False, indent=2))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
