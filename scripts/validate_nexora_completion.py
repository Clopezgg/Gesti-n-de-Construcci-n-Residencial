#!/usr/bin/env python3
"""Validate the published NEXORA requirement matrix and execution baseline.

This gate verifies the 184 permanent requirements from the canonical matrix
(166 from PMI-0.4 plus 14 opened in Bloque 12, the master-mission gap audit).
A requirement is complete only when its row has a terminal justified status,
explicit evidence language and a published 40-character commit SHA.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / "docs/nexora/MATRIZ_REQUISITOS.md"
STATE_PATH = REPO_ROOT / "EXECUTION_STATE.md"
REQUIREMENT_ID = re.compile(r"^NXR-[A-Z]+-\d{4}$")
SHA = re.compile(r"\b[0-9a-f]{40}\b")
TERMINAL_STATUSES = {
	"IMPLEMENTADO Y VALIDADO",
	"OBSOLETO JUSTIFICADO",
	"NO APLICA JUSTIFICADO",
}


def split_row(line: str) -> list[str]:
	return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def parse_matrix() -> list[dict[str, str]]:
	if not MATRIX_PATH.is_file():
		raise FileNotFoundError(MATRIX_PATH)
	header: list[str] | None = None
	rows: list[dict[str, str]] = []
	for line in MATRIX_PATH.read_text(encoding="utf-8").splitlines():
		if line.startswith("| ID | Título |"):
			header = split_row(line)
			continue
		if not header or not line.startswith("| `NXR-"):
			continue
		values = split_row(line)
		if len(values) != len(header):
			raise ValueError(
				f"Fila inválida con {len(values)} celdas; se esperaban {len(header)}: {line[:100]}"
			)
		row = dict(zip(header, values, strict=True))
		row["ID"] = row["ID"].strip("`")
		rows.append(row)
	return rows


def validate_rows(rows: list[dict[str, str]]) -> list[str]:
	errors: list[str] = []
	identifiers = [row.get("ID", "") for row in rows]
	if len(rows) != 184:
		errors.append(f"Se esperaban 184 requisitos y se encontraron {len(rows)}.")
	if len(set(identifiers)) != len(identifiers):
		errors.append("La matriz contiene identificadores duplicados.")
	for row in rows:
		requirement = row.get("ID", "")
		if not REQUIREMENT_ID.fullmatch(requirement):
			errors.append(f"Identificador inválido: {requirement!r}.")
			continue
		status = row.get("Estado", "")
		if status not in TERMINAL_STATUSES:
			errors.append(f"{requirement}: estado no terminal {status!r}.")
		serialized = " ".join(row.values())
		if "evidencia" not in serialized.casefold():
			errors.append(f"{requirement}: falta evidencia explícita.")
		if not SHA.search(serialized):
			errors.append(f"{requirement}: falta SHA publicado de 40 caracteres.")
	return errors


def validate_state() -> list[str]:
	if not STATE_PATH.is_file():
		return ["EXECUTION_STATE.md no existe."]
	text = STATE_PATH.read_text(encoding="utf-8")
	errors: list[str] = []
	for marker in (
		"Clopezgg/Gesti-n-de-Construcci-n-Residencial",
		"Rama oficial: `main`",
		"HEAD inicial de `main` verificado:",
		"Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**",
	):
		if marker not in text:
			errors.append(f"EXECUTION_STATE.md no contiene {marker!r}.")
	if not SHA.search(text):
		errors.append("EXECUTION_STATE.md no contiene una línea base publicada verificable.")
	return errors


def main() -> int:
	try:
		rows = parse_matrix()
	except (FileNotFoundError, ValueError) as exc:
		print(f"ERROR: {exc}", file=sys.stderr)
		return 1
	errors = [*validate_rows(rows), *validate_state()]
	print(f"NEXORA completion gate: requirements={len(rows)} errors={len(errors)}")
	for error in errors:
		print(f"ERROR: {error}", file=sys.stderr)
	return 1 if errors else 0


if __name__ == "__main__":
	raise SystemExit(main())
