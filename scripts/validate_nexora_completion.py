#!/usr/bin/env python3
"""NEXORA — Auditor de certificación integral (Bloque 19).

Verifica que cada requisito de la MATRIZ_REQUISITOS.md tenga
evidencia, SHA y prueba documentados en EXECUTION_STATE.md y BLOQUE_*.md.
"""

from __future__ import annotations

import pathlib
import re
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / "docs/nexora/MATRIZ_REQUISITOS.md"
STATE_PATH = REPO_ROOT / "EXECUTION_STATE.md"
BLOQUE_DIR = REPO_ROOT / "docs/nexora"

REQUIREMENT_PATTERN = re.compile(r"\|\s*(NXR-\w+-\d+)\s*\|")

SHA_PATTERN = re.compile(r"[0-9a-f]{7,40}")
STATE_BLOCK_PATTERN = re.compile(r"## Bloque (\d+).*?SHA\s+`([0-9a-f]{7,40})`", re.DOTALL)


def parse_matrix() -> dict[str, dict[str, Any]]:
    """Parse MATRIZ_REQUISITOS.md into {requirement_id: {line, status, block}}."""
    if not MATRIX_PATH.is_file():
        print(f"ERROR: {MATRIX_PATH} not found")
        sys.exit(1)
    text = MATRIX_PATH.read_text(encoding="utf-8")
    requirements: dict[str, dict[str, Any]] = {}
    current_block = ""
    for line in text.splitlines():
        m = re.search(r"\|.*?(NXR-\w+-\d+).*?\|.*?\|(.*?)\|.*?BLOQUE\s*(\d+)", line)
        if m:
            req_id = m.group(1)
            status = m.group(2).strip()
            block = f"BLOQUE {m.group(3)}"
            requirements[req_id] = {"line": line, "status": status, "block": block, "evidence": False}
    return requirements


def parse_state() -> dict[str, str]:
    """Parse EXECUTION_STATE.md into {block_name: sha}."""
    if not STATE_PATH.is_file():
        return {}
    text = STATE_PATH.read_text(encoding="utf-8")
    blocks: dict[str, str] = {}
    for m in STATE_BLOCK_PATTERN.finditer(text):
        block = f"BLOQUE {m.group(1)}"
        sha = m.group(2)
        blocks[block] = sha
    return blocks


def check_requirements(requirements: dict[str, Any], blocks: dict[str, str]) -> dict[str, Any]:
    """Verify each requirement has evidence."""
    results: dict[str, Any] = {"passed": [], "failed": []}
    for req_id, info in requirements.items():
        if info["status"] in ("IMPLEMENTADO Y VALIDADO", "OBSOLETO JUSTIFICADO", "NO APLICA JUSTIFICADO"):
            block = info["block"]
            if block in blocks:
                info["evidence"] = True
                info["sha"] = blocks[block]
                results["passed"].append(req_id)
            else:
                info["evidence"] = False
                results["failed"].append(req_id)
        else:
            results["failed"].append(req_id)
    return results


def main() -> int:
    print("=" * 60)
    print("NEXORA — Auditor de certificación integral")
    print("=" * 60)
    requirements = parse_matrix()
    print(f"\nRequisitos encontrados: {len(requirements)}")
    if not requirements:
        print("ERROR: No se pudieron parsear requisitos.")
        return 1
    blocks = parse_state()
    print(f"Bloques certificados: {len(blocks)}")
    results = check_requirements(requirements, blocks)
    passed = len(results["passed"])
    failed = len(results["failed"])
    total = passed + failed
    print(f"\nResultados: {passed}/{total} aprobados, {failed}/{total} pendientes")
    if failed:
        print("\nRequisitos sin evidencia completa:")
        for req_id in results["failed"]:
            info = requirements[req_id]
            print(f"  {req_id} [{info['status']}] - {info['block']}")
    else:
        print("\nTodos los requisitos tienen evidencia completa.")
    print(f"\nCobertura: {passed}/{total} ({100 * passed / total:.1f}%)")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
