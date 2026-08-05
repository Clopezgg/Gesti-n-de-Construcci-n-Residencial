#!/usr/bin/env python3
"""Comprueba que la Constitución de NEXORA existe, está completa y gobierna de verdad.

El Capítulo 72 declara la Constitución vinculante para toda inteligencia artificial que
participe en el proyecto. Una autoridad que solo vive en el historial de un chat no
gobierna nada: se pierde con la sesión. Este validador exige que resida en el repositorio,
que conserve sus cinco partes y sus setenta y cuatro capítulos, y que `AGENTS.md` se
declare subordinado en lugar de competir con ella.

No juzga el cumplimiento de los principios —eso lo hacen el producto y su suite—, sino que
el documento rector siga siendo el documento rector.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONSTITUTION = ROOT / "NEXORA_CONSTITUTION.md"
AGENTS = ROOT / "AGENTS.md"

TOTAL_CHAPTERS = 74
PARTS = 5

# Capítulos cuya desaparición cambiaría el proyecto, no solo el documento.
LOAD_BEARING = {
	4: "Objetivo absoluto",
	13: "Priorización",
	35: "Flujos",
	44: "Reglas de programación",
	60: 'Definición de «terminado»',
	68: "Mandamientos de NEXORA",
	72: "Directiva permanente para cualquier IA",
}


def failures() -> list[str]:
	problems: list[str] = []
	if not CONSTITUTION.is_file():
		return [f"falta {CONSTITUTION.name}: sin ella el Capítulo 72 no puede aplicarse"]

	text = CONSTITUTION.read_text(encoding="utf-8")

	parts = re.findall(r"^## PARTE (\d+) —", text, re.MULTILINE)
	if [int(value) for value in parts] != list(range(1, PARTS + 1)):
		problems.append(f"las partes deben ir de 1 a {PARTS}; se encontraron {parts or 'ninguna'}")

	found = [int(value) for value in re.findall(r"^### Capítulo (\d+) —", text, re.MULTILINE)]
	expected = list(range(1, TOTAL_CHAPTERS + 1))
	if found != expected:
		missing = sorted(set(expected) - set(found))
		extra = sorted(set(found) - set(expected))
		detail = []
		if missing:
			detail.append(f"faltan {missing}")
		if extra:
			detail.append(f"sobran {extra}")
		if not detail:
			detail.append("están desordenados")
		problems.append("capítulos incompletos: " + "; ".join(detail))

	for number, title in LOAD_BEARING.items():
		if f"### Capítulo {number} — {title}" not in text:
			problems.append(f"el capítulo {number} debe conservar su título «{title}»")

	# El Capítulo 60 es una lista de comprobación: sin sus trece puntos deja de serlo.
	chapter_60 = text.split("### Capítulo 60 —", 1)
	if len(chapter_60) == 2:
		body = chapter_60[1].split("### Capítulo 61", 1)[0]
		checks = re.findall(r"^- \[ \] ", body, re.MULTILINE)
		if len(checks) != 13:
			problems.append(
				f"«terminado» exige 13 comprobaciones; el capítulo 60 declara {len(checks)}"
			)

	if not AGENTS.is_file():
		problems.append("falta AGENTS.md")
	else:
		agents = AGENTS.read_text(encoding="utf-8")
		if "NEXORA_CONSTITUTION.md" not in agents:
			problems.append("AGENTS.md debe enlazar la Constitución que lo gobierna")
		if "subordinado" not in agents.lower():
			problems.append("AGENTS.md debe declararse subordinado a la Constitución")
		# Capítulo 44: una regla vive en un único lugar. Si AGENTS.md vuelve a enumerar
		# «terminado» por su cuenta, las dos definiciones se separarán.
		if "Capítulo 60" not in agents:
			problems.append("AGENTS.md debe remitir a la definición de «terminado» del capítulo 60")

	return problems


def main() -> int:
	problems = failures()
	if problems:
		print("La Constitución de NEXORA no está íntegra:")
		for problem in problems:
			print(f"- {problem}")
		return 1
	print(
		f"Constitución íntegra: {PARTS} partes, {TOTAL_CHAPTERS} capítulos, "
		"AGENTS.md subordinado."
	)
	return 0


if __name__ == "__main__":
	sys.exit(main())
