#!/usr/bin/env python3
"""NEXORA — auditor de certificación integral (Bloque 19).

Verifica que los 166 requisitos de la matriz tengan un estado terminal y
que su bloque propietario aparezca certificado con un SHA completo en la
tabla oficial de EXECUTION_STATE.md.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / "docs/nexora/MATRIZ_REQUISITOS.md"
STATE_PATH = REPO_ROOT / "EXECUTION_STATE.md"
TERMINAL_STATES = {
    "IMPLEMENTADO Y VALIDADO",
    "OBSOLETO JUSTIFICADO",
    "NO APLICA JUSTIFICADO",
}
REQUIREMENT_RE = re.compile(r"^NXR-[A-Z]+-\d{4}$")
SHA_RE = re.compile(r"`([0-9a-f]{40})`")


def split_row(line: str) -> list[str]:
    raw = line.strip().strip("|")
    cells = re.split(r"(?<!\\)\|", raw)
    return [cell.strip().replace("\|", "|") for cell in cells]


def parse_matrix() -> dict[str, dict[str, Any]]:
    if not MATRIX_PATH.is_file():
        raise FileNotFoundError(MATRIX_PATH)
    header: list[str] | None = None
    requirements: dict[str, dict[str, Any]] = {}
    for line in MATRIX_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("| ID | Título |"):
            header = split_row(line)
            continue
        if not header or not line.startswith("| `NXR-"):
            continue
        values = split_row(line)
        if len(values) != len(header):
            raise ValueError(
                f"Requirement row has {len(values)} cells; expected {len(header)}: {line[:100]}"
            )
        record = dict(zip(header, values, strict=True))
        requirement_id = record["ID"].strip("`")
        if not REQUIREMENT_RE.fullmatch(requirement_id):
            raise ValueError(f"Invalid requirement ID: {requirement_id}")
        requirements[requirement_id] = {
            "status": record["Estado"],
            "block": record["Propietario"].upper(),
            "evidence": False,
        }
    return requirements


def expand_block_cell(value: str) -> list[int]:
    normalized = value.replace("*", "").replace("`", "").strip()
    match = re.fullmatch(r"(\d+)(?:\s*[–-]\s*(\d+))?", normalized)
    if not match:
        return []
    start = int(match.group(1))
    end = int(match.group(2) or start)
    return list(range(start, end + 1))


def parse_state() -> dict[str, str]:
    if not STATE_PATH.is_file():
        raise FileNotFoundError(STATE_PATH)
    header: list[str] | None = None
    blocks: dict[str, str] = {}
    for line in STATE_PATH.read_text(encoding="utf-8").splitlines():
        cells = split_row(line) if line.startswith("|") else []
        if cells and cells[0].strip() == "Bloque" and "Estado" in cells:
            header = cells
            continue
        if not header or not cells or len(cells) != len(header):
            continue
        record = dict(zip(header, cells, strict=True))
        status = record["Estado"].replace("*", "").strip()
        if status not in TERMINAL_STATES:
            continue
        sha_match = SHA_RE.search(record["SHA funcional certificado"])
        if not sha_match:
            continue
        for number in expand_block_cell(record["Bloque"]):
            blocks[f"BLOQUE {number}"] = sha_match.group(1)
    return blocks


def check_requirements(
    requirements: dict[str, dict[str, Any]], blocks: dict[str, str]
) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {"passed": [], "failed": []}
    for requirement_id, info in requirements.items():
        block = info["block"]
        if info["status"] in TERMINAL_STATES and block in blocks:
            info["evidence"] = True
            info["sha"] = blocks[block]
            results["passed"].append(requirement_id)
        else:
            results["failed"].append(requirement_id)
    return results


def main() -> int:
    print("=" * 60)
    print("NEXORA — Auditor de certificación integral")
    print("=" * 60)
    try:
        requirements = parse_matrix()
        blocks = parse_state()
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"\nRequisitos encontrados: {len(requirements)}")
    print(f"Bloques certificados: {len(blocks)}")
    results = check_requirements(requirements, blocks)
    passed = len(results["passed"])
    failed = len(results["failed"])
    total = passed + failed

    structural_errors: list[str] = []
    if len(requirements) != 166:
        structural_errors.append(
            f"Se esperaban 166 requisitos y se encontraron {len(requirements)}."
        )
    missing_blocks = [
        f"BLOQUE {number}" for number in range(21) if f"BLOQUE {number}" not in blocks
    ]
    if missing_blocks:
        structural_errors.append(
            f"Bloques sin certificación terminal: {', '.join(missing_blocks)}"
        )

    print(f"\nResultados: {passed}/{total} aprobados, {failed}/{total} pendientes")
    if failed:
        print("\nRequisitos sin evidencia completa:")
        for requirement_id in results["failed"]:
            info = requirements[requirement_id]
            print(f"  {requirement_id} [{info['status']}] - {info['block']}")
    for error in structural_errors:
        print(f"ERROR: {error}")

    coverage = 100 * passed / total if total else 0
    print(f"\nCobertura: {passed}/{total} ({coverage:.1f}%)")
    return 0 if not failed and not structural_errors else 1


if __name__ == "__main__":
    sys.exit(main())
