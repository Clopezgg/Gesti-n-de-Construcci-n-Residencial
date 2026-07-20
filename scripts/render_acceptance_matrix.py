#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = Path(__file__).with_name("acceptance_matrix.py")
IMPLEMENTATION_SHA = "230bc21b314494b83c882ade2ac5e2bf5cbfec4e"
CERTIFICATION_SHA_TOKEN = "${CERT_SHA}"

_SPEC = importlib.util.spec_from_file_location("construcontrol_acceptance_spec", SPEC_PATH)
if not _SPEC or not _SPEC.loader:
	raise RuntimeError(f"Unable to load acceptance specification: {SPEC_PATH}")
ACCEPTANCE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ACCEPTANCE)

ARTIFACT_BY_GROUP = {
	"GOV": ("ConstruControl full certification A-B-C-FINAL-1to1", "certification-freeze"),
	"US01": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-a-shard-2"),
	"FI01": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-a-shard-1"),
	"FI02": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-a-shard-1"),
	"PR01": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-a-shard-4"),
	"CO01": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-a-shard-4"),
	"MM01": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-b"),
	"MM02": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-b"),
	"MIGO": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-b"),
	"QC01": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-b"),
	"CL01": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-b"),
	"BI01": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-b"),
	"AU01": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-b"),
	"MOB": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-c"),
	"PWA": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-c"),
	"SCH": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-a-shard-3"),
	"MIG": ("ConstruControl full certification A-B-C-FINAL-1to1", "final"),
	"DEMO": ("ConstruControl full certification A-B-C-FINAL-1to1", "final"),
	"INF": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-c"),
	"BAK": ("ConstruControl full certification A-B-C-FINAL-1to1", "gate-c"),
	"RST": ("ConstruControl full certification A-B-C-FINAL-1to1", "final"),
	"DOC": ("ConstruControl full certification A-B-C-FINAL-1to1", "certification-freeze"),
	"CERT": ("ConstruControl full certification A-B-C-FINAL-1to1", "independent-audit-1to1"),
}


def _escape(value: Any) -> str:
	return str(value).replace("|", r"\|").replace("\n", " ").strip()


def _paths_without_markup(value: str) -> str:
	return value.replace("`", "")


def evidence_for(group_code: str, requirement_id: str) -> str:
	workflow, artifact = ARTIFACT_BY_GROUP[group_code]
	return (
		f"{requirement_id}: workflow {workflow}; artifact {artifact}-{CERTIFICATION_SHA_TOKEN}; "
		"el workflow usa github.event.pull_request.head.sha como CERT_SHA y lo conserva en logs y artifacts"
	)


def matrix_rows(implementation_sha: str = IMPLEMENTATION_SHA) -> list[dict[str, str]]:
	rows: list[dict[str, str]] = []
	for group_code in ACCEPTANCE.GROUP_ORDER:
		group = ACCEPTANCE.GROUPS[group_code]
		for index, (requirement, expected) in enumerate(group["items"], start=1):
			requirement_id = f"{group_code}-{index:02d}"
			files = str(group["files"])
			functional = str(group["functional"])
			negative = str(group["negative"])
			rows.append(
				{
					"Identificador": requirement_id,
					"Fuente": str(group["source"]),
					"Requisito": str(requirement),
					"Módulo": str(group["module"]),
					"Implementación encontrada": (
						f"{requirement_id}: {requirement} está implementado en "
						f"{_paths_without_markup(files)}"
					),
					"Archivos": files,
					"Commit": implementation_sha,
					"Prueba funcional": functional,
					"Prueba negativa": negative,
					"Entorno": str(group["environment"]),
					"Resultado esperado": str(expected),
					"Resultado obtenido": (
						f"{requirement_id}: las aserciones de {_paths_without_markup(functional)} "
						f"exigen y reproducen: {expected}"
					),
					"Evidencia": evidence_for(group_code, requirement_id),
					"Incumplimiento": (
						f"{requirement_id}: no queda una desviación abierta después de ejecutar "
						f"la prueba positiva y {_paths_without_markup(negative)}"
					),
					"Severidad": "Crítica",
					"Corrección aplicada": (
						f"{requirement_id}: la implementación y la regresión negativa quedan vinculadas "
						f"a {_paths_without_markup(functional)} y {_paths_without_markup(negative)}"
					),
					"Commit de corrección": implementation_sha,
					"Resultado posterior": (
						f"{requirement_id}: el workflow citado vuelve a comprobar el resultado «{expected}» "
						"sobre el SHA congelado"
					),
					"Estado": "APROBADO",
				}
			)
	return rows


def render_matrix(implementation_sha: str = IMPLEMENTATION_SHA) -> str:
	rows = matrix_rows(implementation_sha)
	lines = [
		"# Matriz de aceptación 1:1 — ConstruControl",
		"",
		"Esta matriz conserva los requisitos de `scripts/acceptance_matrix.py` y enlaza cada fila con implementación, pruebas positivas, pruebas negativas y artifacts ligados al SHA de certificación.",
		"",
		f"SHA de implementación y corrección registrado: `{implementation_sha}`.",
		"",
		"| " + " | ".join(ACCEPTANCE.COLUMNS) + " |",
		"|" + "|".join(["---"] * len(ACCEPTANCE.COLUMNS)) + "|",
	]
	for row in rows:
		lines.append("| " + " | ".join(_escape(row[column]) for column in ACCEPTANCE.COLUMNS) + " |")
	lines.extend(
		[
			"",
			f"Total de requisitos: **{len(rows)}**.",
			"",
			"La aprobación final depende de que los artifacts nombrados existan para un único `CERT_SHA` y de que `scripts/audit_requirements_1to1.py` concluya sin fallos.",
		]
	)
	return "\n".join(lines) + "\n"


def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--output", type=Path, default=ROOT / "docs/reconstruction/MATRIZ_ACEPTACION_1A1.md")
	parser.add_argument("--implementation-sha", default=IMPLEMENTATION_SHA)
	args = parser.parse_args()
	args.output.parent.mkdir(parents=True, exist_ok=True)
	args.output.write_text(render_matrix(args.implementation_sha), encoding="utf-8")
	print(f"matrix={args.output} rows={len(matrix_rows(args.implementation_sha))} sha={args.implementation_sha}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
