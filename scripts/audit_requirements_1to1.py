#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

_MATRIX_SPEC = Path(__file__).with_name("acceptance_matrix.py")
_SPEC = importlib.util.spec_from_file_location("construcontrol_acceptance_matrix", _MATRIX_SPEC)
if not _SPEC or not _SPEC.loader:
	raise RuntimeError(f"Unable to load acceptance requirement specification: {_MATRIX_SPEC}")
_ACCEPTANCE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ACCEPTANCE)
_RECEIPTS_SPEC = Path(__file__).with_name("acceptance_receipts.py")
_RECEIPTS_MODULE_SPEC = importlib.util.spec_from_file_location(
	"construcontrol_acceptance_receipts", _RECEIPTS_SPEC
)
if not _RECEIPTS_MODULE_SPEC or not _RECEIPTS_MODULE_SPEC.loader:
	raise RuntimeError(f"Unable to load acceptance receipt helpers: {_RECEIPTS_SPEC}")
_RECEIPTS = importlib.util.module_from_spec(_RECEIPTS_MODULE_SPEC)
_RECEIPTS_MODULE_SPEC.loader.exec_module(_RECEIPTS)
MATRIX_COLUMNS = _ACCEPTANCE.COLUMNS
REQUIRED_MATRIX_IDS = _ACCEPTANCE.requirement_ids()
ALLOWED_STATES = {"APROBADO", "RECHAZADO", "NO DEMOSTRADO", "EN CORRECCIÓN"}

GENERIC_EVIDENCE_PHRASES = (
	"implementación canónica",
	"comportamiento demostrado",
	"ninguno conocido",
	"historial funcional",
	"cumple solicitado",
	"head certificado",
)
SPECIFIC_EVIDENCE_COLUMNS = (
	"Implementación encontrada",
	"Resultado obtenido",
	"Evidencia",
	"Corrección aplicada",
	"Resultado posterior",
)
EXACT_SHA = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", re.I)

REQUIRED_MODULES = {
	"US01": ("erpnext/construcontrol/users.py", "erpnext/construcontrol/access.py"),
	"FI01": (
		"erpnext/construcontrol/finance.py",
		"erpnext/construcontrol/business_rules.py",
	),
	"FI02": ("erpnext/construcontrol/expenses.py",),
	"PR01": ("erpnext/construcontrol/construction.py",),
	"CO01": ("erpnext/construcontrol/construction.py",),
	"MM01": ("erpnext/construcontrol/inventory.py",),
	"MM02": ("erpnext/construcontrol/inventory.py",),
	"MIGO": ("erpnext/construcontrol/inventory.py",),
	"QC01": ("erpnext/construcontrol/quality.py",),
	"CL01": ("erpnext/construcontrol/closing.py", "erpnext/construcontrol/weekly.py"),
	"BI01": (
		"erpnext/construcontrol/reporting.py",
		"erpnext/construcontrol/reporting_summary.py",
	),
	"AU01": ("erpnext/construcontrol/audit.py",),
	"MIG": ("erpnext/construcontrol/migration", "deploy/coolify/restore-verify.sh"),
}
REQUIRED_FILES = (
	"Dockerfile",
	"docker-compose.yml",
	"MANUAL_PASO_A_PASO.md",
	"docs/reconstruction/MATRIZ_ACEPTACION_1A1.md",
	"deploy/coolify/backup-now.sh",
	"deploy/coolify/restore-verify.sh",
	"scripts/verify_backup_manifest.py",
	"scripts/acceptance_matrix.py",
	"scripts/audit_requirements_1to1.py",
	".github/workflows/construcontrol-full-certification.yml",
	"erpnext/public/construcontrol/manifest.webmanifest",
	"erpnext/www/construcontrol-service-worker.js",
	"erpnext/construcontrol/tests/test_ci_gate_contract_standalone.py",
)
BACKTICK_PATH = re.compile(r"`([^`]+)`")


def _split_row(line: str) -> list[str]:
	stripped = line.strip()
	if not stripped.startswith("|") or not stripped.endswith("|"):
		return []
	return [cell.strip().replace(r"\|", "|") for cell in stripped[1:-1].split("|")]


def parse_acceptance_matrix(path: Path) -> list[dict[str, str]]:
	lines = path.read_text(encoding="utf-8").splitlines()
	header_index = next(
		(index for index, line in enumerate(lines) if line.lstrip().startswith("| Identificador |")),
		None,
	)
	if header_index is None:
		raise ValueError("Acceptance matrix table header was not found.")
	header = _split_row(lines[header_index])
	if header != MATRIX_COLUMNS:
		raise ValueError(f"Acceptance matrix columns differ: {header!r}")
	rows: list[dict[str, str]] = []
	for line in lines[header_index + 2 :]:
		if not line.strip().startswith("|"):
			if rows:
				break
			continue
		cells = _split_row(line)
		if len(cells) != len(MATRIX_COLUMNS):
			raise ValueError(f"Malformed matrix row with {len(cells)} cells: {line[:120]}")
		rows.append(dict(zip(MATRIX_COLUMNS, cells, strict=True)))
	if not rows:
		raise ValueError("Acceptance matrix has no requirement rows.")
	return rows


def _referenced_paths(value: str) -> list[str]:
	return [token for token in BACKTICK_PATH.findall(value) if "/" in token and not token.startswith("http")]


def validate_acceptance_matrix(
	root: Path,
	*,
	required_ids: Iterable[str] = REQUIRED_MATRIX_IDS,
	require_all_approved: bool = True,
	matrix_path: Path | None = None,
) -> dict[str, Any]:
	matrix_path = matrix_path or root / "docs/reconstruction/MATRIZ_ACEPTACION_1A1.md"
	if not matrix_path.is_file():
		return {
			"passed": False,
			"rows": 0,
			"failures": ["Acceptance matrix is missing."],
		}
	try:
		rows = parse_acceptance_matrix(matrix_path)
	except ValueError as exc:
		return {"passed": False, "rows": 0, "failures": [str(exc)]}

	failures: list[str] = []
	ids = [row["Identificador"] for row in rows]
	duplicates = sorted({item for item in ids if ids.count(item) > 1})
	if duplicates:
		failures.append("Duplicate requirement IDs: " + ", ".join(duplicates))
	missing = sorted(set(required_ids) - set(ids))
	if missing:
		failures.append("Missing requirement IDs: " + ", ".join(missing))

	for index, row in enumerate(rows, start=1):
		rid = row["Identificador"] or f"row-{index}"
		for column in MATRIX_COLUMNS:
			value = row[column].strip()
			if not value or value in {"-", "—", "N/A"}:
				failures.append(f"{rid}: empty or non-evidentiary column {column}")
		state = row["Estado"].strip().upper()
		if state not in ALLOWED_STATES:
			failures.append(f"{rid}: invalid state {state!r}")
		if require_all_approved and state != "APROBADO":
			failures.append(f"{rid}: unresolved state {state}")
		combined = " ".join(row[column] for column in MATRIX_COLUMNS).casefold()
		for phrase in GENERIC_EVIDENCE_PHRASES:
			if phrase in combined:
				failures.append(f"{rid}: generic evidence phrase is forbidden: {phrase}")
		for column in SPECIFIC_EVIDENCE_COLUMNS:
			if rid.casefold() not in row[column].casefold():
				failures.append(f"{rid}: {column} does not identify the requirement")
		evidence = row["Evidencia"].casefold()
		if "workflow" not in evidence or "artifact" not in evidence:
			failures.append(f"{rid}: evidence must identify both workflow and artifact")
		if state == "APROBADO":
			for column in ("Commit", "Commit de corrección"):
				if not EXACT_SHA.search(row[column]):
					failures.append(f"{rid}: {column} lacks an exact 40-character commit SHA")
		for column in ("Archivos", "Prueba funcional", "Prueba negativa"):
			references = _referenced_paths(row[column])
			if not references:
				failures.append(f"{rid}: {column} does not reference a repository path")
			for relative in references:
				if not (root / relative.rstrip("/")).exists():
					failures.append(f"{rid}: missing referenced path {relative}")
	states = {
		state: sum(row["Estado"].strip().upper() == state for row in rows) for state in sorted(ALLOWED_STATES)
	}
	return {"passed": not failures, "rows": len(rows), "states": states, "failures": failures}


def validate_acceptance_receipts(
	root: Path,
	*,
	matrix_path: Path,
	receipts_dir: Path,
	artifacts_root: Path,
	cert_sha: str,
	required_ids: Iterable[str] = REQUIRED_MATRIX_IDS,
) -> dict[str, Any]:
	failures: list[str] = []
	if not _RECEIPTS.EXACT_SHA.fullmatch(cert_sha):
		return {"passed": False, "receipts": 0, "failures": [f"Invalid CERT_SHA: {cert_sha!r}"]}
	try:
		rows = parse_acceptance_matrix(matrix_path)
	except ValueError as exc:
		return {"passed": False, "receipts": 0, "failures": [str(exc)]}
	row_by_id = {row["Identificador"]: row for row in rows}
	expected_ids = set(required_ids)
	files = sorted(receipts_dir.glob("*.json")) if receipts_dir.is_dir() else []
	actual_ids = {path.stem for path in files}
	missing = sorted(expected_ids - actual_ids)
	extra = sorted(actual_ids - expected_ids)
	if missing:
		failures.append("Missing receipt IDs: " + ", ".join(missing))
	if extra:
		failures.append("Unexpected receipt IDs: " + ", ".join(extra))

	artifact_cache: dict[str, tuple[str, list[dict[str, Any]]]] = {}
	fingerprints: dict[str, str] = {}
	validated = 0
	for path in files:
		rid = path.stem
		if rid not in expected_ids or rid not in row_by_id:
			continue
		row = row_by_id[rid]
		try:
			receipt = json.loads(path.read_text(encoding="utf-8"))
		except Exception as exc:
			failures.append(f"{rid}: invalid receipt JSON: {exc}")
			continue
		missing_fields = sorted(_RECEIPTS.REQUIRED_RECEIPT_FIELDS - set(receipt))
		if missing_fields:
			failures.append(f"{rid}: receipt is missing fields: {', '.join(missing_fields)}")
			continue
		if receipt.get("schema_version") != 1:
			failures.append(f"{rid}: unsupported receipt schema")
		if receipt.get("requirement_id") != rid:
			failures.append(f"{rid}: receipt ID does not match its filename")
		if receipt.get("cert_sha") != cert_sha:
			failures.append(f"{rid}: receipt belongs to another SHA")
		if receipt.get("module") != row["Módulo"]:
			failures.append(f"{rid}: receipt module differs from the certified matrix")
		if receipt.get("result") != "APROBADO" or row["Estado"].strip().upper() != "APROBADO":
			failures.append(f"{rid}: receipt and certified matrix must both be APROBADO")

		implementation = receipt.get("implementation")
		if not isinstance(implementation, dict):
			failures.append(f"{rid}: implementation locator is invalid")
			implementation = {}
		implementation_files = implementation.get("files")
		if not isinstance(implementation_files, list) or not implementation_files:
			failures.append(f"{rid}: receipt has no implementation files")
			implementation_files = []
		for relative in implementation_files:
			if not isinstance(relative, str) or not (root / relative).exists():
				failures.append(f"{rid}: missing receipt implementation path {relative!r}")
		for field in ("implementation_sha", "correction_sha"):
			if not _RECEIPTS.EXACT_SHA.fullmatch(str(implementation.get(field) or "")):
				failures.append(f"{rid}: {field} is not an exact commit SHA")
		if rid.casefold() not in str(implementation.get("locator") or "").casefold():
			failures.append(f"{rid}: implementation locator is not requirement-specific")

		command = receipt.get("command")
		if not isinstance(command, str) or len(command.strip()) < 12:
			failures.append(f"{rid}: receipt command is absent or non-evidentiary")
		test = receipt.get("test")
		if not isinstance(test, dict):
			failures.append(f"{rid}: receipt test contract is invalid")
			test = {}
		if test.get("assertion") != row["Resultado esperado"]:
			failures.append(f"{rid}: receipt assertion differs from the requirement")
		for scenario_type in ("positive", "negative"):
			references = test.get(scenario_type)
			if not isinstance(references, list) or not references:
				failures.append(f"{rid}: receipt has no {scenario_type} tests")
				continue
			for relative in references:
				if not isinstance(relative, str) or not (root / relative).exists():
					failures.append(f"{rid}: missing {scenario_type} test path {relative!r}")
		scenarios = receipt.get("scenarios")
		if not isinstance(scenarios, dict):
			failures.append(f"{rid}: receipt scenarios are invalid")
			scenarios = {}
		positive = str(scenarios.get("positive") or "")
		negative = str(scenarios.get("negative") or "")
		if rid not in positive or rid not in negative or positive == negative:
			failures.append(
				f"{rid}: positive and negative scenarios must be distinct and requirement-specific"
			)

		artifact = receipt.get("artifact")
		if not isinstance(artifact, dict):
			failures.append(f"{rid}: receipt artifact is invalid")
			artifact = {}
		artifact_name = str(artifact.get("name") or "")
		artifact_relative = str(artifact.get("path") or "")
		if (
			not artifact_name
			or artifact_relative != artifact_name
			or Path(artifact_relative).name != artifact_relative
		):
			failures.append(f"{rid}: artifact path must be one safe artifact directory name")
		else:
			artifact_path = artifacts_root / artifact_relative
			try:
				if artifact_name not in artifact_cache:
					artifact_cache[artifact_name] = _RECEIPTS.artifact_digest(artifact_path)
				actual_digest, manifest = artifact_cache[artifact_name]
				if artifact.get("sha256") != actual_digest:
					failures.append(f"{rid}: artifact digest mismatch")
				if artifact.get("file_count") != len(manifest):
					failures.append(f"{rid}: artifact file count mismatch")
			except Exception as exc:
				failures.append(f"{rid}: artifact validation failed: {exc}")
		if "workflow" not in artifact or not str(artifact.get("workflow") or "").strip():
			failures.append(f"{rid}: artifact workflow is absent")

		actual_receipt_digest = _RECEIPTS.receipt_digest(receipt)
		if receipt.get("receipt_sha256") != actual_receipt_digest:
			failures.append(f"{rid}: receipt digest mismatch")
		evidence = row["Evidencia"]
		for token in (
			artifact_name,
			str(artifact.get("sha256") or ""),
			actual_receipt_digest,
			f"receipts/{rid}.json",
		):
			if not token or token not in evidence:
				failures.append(f"{rid}: certified matrix evidence omits receipt/artifact token {token!r}")

		fingerprint_payload = {
			"implementation": implementation_files,
			"command": command,
			"test": test,
			"scenarios": scenarios,
			"artifact": artifact_name,
		}
		fingerprint = json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True)
		if fingerprint in fingerprints:
			failures.append(f"{rid}: evidence repeats receipt {fingerprints[fingerprint]}")
		else:
			fingerprints[fingerprint] = rid
		validated += 1

	return {
		"passed": not failures,
		"receipts": validated,
		"artifacts": len(artifact_cache),
		"failures": failures,
	}


def _check(identifier: str, passed: bool, detail: Any) -> dict[str, Any]:
	return {"id": identifier, "passed": bool(passed), "detail": detail}


def run_audit(
	root: Path,
	*,
	matrix_path: Path | None = None,
	receipts_dir: Path | None = None,
	artifacts_root: Path | None = None,
	cert_sha: str | None = None,
) -> dict[str, Any]:
	checks = [_check(f"file:{path}", (root / path).exists(), path) for path in REQUIRED_FILES]
	matrix = validate_acceptance_matrix(root, matrix_path=matrix_path)
	checks.append(_check("matrix:acceptance-1to1", matrix["passed"], matrix))
	if receipts_dir is not None or artifacts_root is not None or cert_sha is not None:
		if not all((matrix_path, receipts_dir, artifacts_root, cert_sha)):
			receipts = {
				"passed": False,
				"receipts": 0,
				"failures": ["Certified audit requires matrix, receipts, artifacts and CERT_SHA together."],
			}
		else:
			receipts = validate_acceptance_receipts(
				root,
				matrix_path=matrix_path,
				receipts_dir=receipts_dir,
				artifacts_root=artifacts_root,
				cert_sha=cert_sha,
			)
		checks.append(_check("receipts:acceptance-1to1", receipts["passed"], receipts))
	for module, paths in REQUIRED_MODULES.items():
		checks.append(_check(f"module:{module}", all((root / path).exists() for path in paths), paths))

	compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
	services = {
		"mariadb",
		"redis-cache",
		"redis-queue",
		"backend",
		"websocket",
		"queue-short",
		"queue-long",
		"scheduler",
		"frontend",
		"backup",
	}
	for service in sorted(services):
		checks.append(
			_check(
				f"service:{service}",
				re.search(rf"^  {re.escape(service)}:\s*$", compose, re.M),
				"declared",
			)
		)
	checks.append(
		_check(
			"architecture:linux-amd64",
			"platform: linux/amd64" in compose,
			"canonical platform",
		)
	)
	checks.append(
		_check(
			"architecture:private-data-services",
			"3306:3306" not in compose and "6379:6379" not in compose,
			"database and redis remain private",
		)
	)

	historical = root / "docs/historical/README.md"
	checks.append(
		_check(
			"documentation:historical-obsolete",
			historical.is_file() and "OBSOLETO" in historical.read_text(encoding="utf-8").upper(),
			"historical deployment guidance marked obsolete",
		)
	)

	manifest = json.loads(
		(root / "erpnext/public/construcontrol/manifest.webmanifest").read_text(encoding="utf-8")
	)
	checks.append(
		_check(
			"pwa:start-url",
			manifest.get("start_url") == "/app/construcontrol-dashboard",
			manifest.get("start_url"),
		)
	)
	icon_sizes = {icon.get("sizes") for icon in manifest.get("icons", [])}
	checks.append(_check("pwa:icons", {"192x192", "512x512"}.issubset(icon_sizes), sorted(icon_sizes)))

	workflow = (root / ".github/workflows/construcontrol-full-certification.yml").read_text(encoding="utf-8")
	sequence = [
		"needs: freeze",
		"needs: gate-a",
		"needs: gate-b",
		"needs: gate-c",
		"needs: final",
	]
	checks.append(
		_check(
			"certification:sequential",
			all(item in workflow for item in sequence),
			sequence,
		)
	)

	failed = [check for check in checks if not check["passed"]]
	return {
		"status": "passed" if not failed else "failed",
		"summary": {
			"total": len(checks),
			"passed": len(checks) - len(failed),
			"failed": len(failed),
			"matrix_rows": matrix.get("rows", 0),
		},
		"checks": checks,
	}


def main() -> int:
	parser = argparse.ArgumentParser(description="Independent ConstruControl 1:1 acceptance audit")
	parser.add_argument("--root", default=".")
	parser.add_argument("--output")
	parser.add_argument("--matrix", type=Path)
	parser.add_argument("--receipts", type=Path)
	parser.add_argument("--artifacts-root", type=Path)
	parser.add_argument("--cert-sha")
	args = parser.parse_args()
	report = run_audit(
		Path(args.root).resolve(),
		matrix_path=args.matrix.resolve() if args.matrix else None,
		receipts_dir=args.receipts.resolve() if args.receipts else None,
		artifacts_root=args.artifacts_root.resolve() if args.artifacts_root else None,
		cert_sha=args.cert_sha,
	)
	rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
	if args.output:
		target = Path(args.output)
		target.parent.mkdir(parents=True, exist_ok=True)
		target.write_text(rendered, encoding="utf-8")
	print(rendered, end="")
	return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
	raise SystemExit(main())
