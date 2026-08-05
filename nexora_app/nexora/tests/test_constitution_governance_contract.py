from __future__ import annotations

import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[3]
ROADMAP = REPO / "ROADMAP.md"
CONSTITUTION = REPO / "NEXORA_CONSTITUTION.md"
RECONSTRUCTION = REPO / "PROJECT_RECONSTRUCTION.md"


class TestConstitutionGovernanceContract(unittest.TestCase):
	"""Parte 5 de la Constitución: gobierno permanente del producto.

	El Capítulo 63 exige una hoja de ruta viva, no una lista estática de módulos; el 64
	fija el orden de prioridad; el 44 y el 67 prohíben que la misma información viva en
	dos sitios y acabe divergiendo.
	"""

	def test_the_permanent_roadmap_exists_and_answers_to_the_constitution(self) -> None:
		self.assertTrue(ROADMAP.is_file(), "falta la hoja de ruta del Capítulo 63")
		roadmap = ROADMAP.read_text(encoding="utf-8")
		self.assertIn("NEXORA_CONSTITUTION.md", roadmap, "la hoja de ruta cita su origen")
		self.assertIn("Capítulo 63", roadmap)
		self.assertIn("Capítulo 64", roadmap)

	def test_the_roadmap_orders_by_the_priority_the_constitution_fixes(self) -> None:
		"""Capítulo 64: el orden no lo elige quien implementa."""
		roadmap = ROADMAP.read_text(encoding="utf-8")
		priorities = [int(value) for value in re.findall(r"^\| (\d+) · ", roadmap, re.MULTILINE)]
		self.assertTrue(priorities, "las filas abiertas deben declarar su prioridad")
		self.assertEqual(sorted(priorities), priorities, "las filas se listan de mayor a menor prioridad")

	def test_the_roadmap_points_at_the_debt_registry_instead_of_copying_it(self) -> None:
		"""Capítulos 44 y 67: una regla en un único lugar; dos copias divergen."""
		roadmap = ROADMAP.read_text(encoding="utf-8")
		self.assertIn("PROJECT_RECONSTRUCTION.md", roadmap)
		debt = RECONSTRUCTION.read_text(encoding="utf-8")
		table = debt.split("## Deuda registrada", 1)[1].split("\n## ", 1)[0]
		rows = [
			row.split("|")[1].strip()
			for row in table.splitlines()
			if row.startswith("|") and "---" not in row
		][1:]
		copied = [row for row in rows if row and row in roadmap]
		self.assertEqual([], copied, "la deuda se referencia, no se reproduce")

	def test_the_constitution_keeps_its_five_parts_and_seventy_four_chapters(self) -> None:
		text = CONSTITUTION.read_text(encoding="utf-8")
		chapters = {int(value) for value in re.findall(r"^### Capítulo (\d+)", text, re.MULTILINE)}
		self.assertEqual(set(range(1, 75)), chapters)


if __name__ == "__main__":
	unittest.main()
