#!/usr/bin/env python3
"""Validate the executable NEXORA governance baseline."""

from __future__ import annotations

import argparse
import collections
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "nexora"
REQUIREMENTS = DOCS / "MATRIZ_REQUISITOS.md"
MACHINES = DOCS / "CATALOGO_MAQUINAS_ESTADO.md"
CONTROLS = DOCS / "CATALOGO_CONTROLES.md"
DECISIONS = DOCS / "DECISIONES.md"
ARCHITECTURE = DOCS / "ARQUITECTURA.md"
PLAN = DOCS / "PLAN_MAESTRO.md"
STATE = ROOT / "EXECUTION_STATE.md"

ALLOWED_STATES = {
	"CONFIRMADO",
	"PROPUESTO",
	"REQUIERE DECISIÓN",
	"EXISTENTE Y REUTILIZABLE",
	"EXISTENTE PERO DEFECTUOSO",
	"OBSOLETO",
	"NO DEMOSTRADO",
	"IMPLEMENTADO Y VALIDADO",
}
REQUIREMENT_RE = re.compile(r"^NXR-[A-Z]+-\d{4}$")
MACHINE_RE = re.compile(r"^STM-[A-Z0-9-]+$")
CONTROL_RE = re.compile(r"^(?:CTL|TST)-[A-Z0-9-]+$")
DECISION_RE = re.compile(r"^DEC-\d{3}$")


def die(errors: list[str]) -> None:
	for error in errors:
		print(f"ERROR: {error}", file=sys.stderr)
	raise SystemExit(1)


def split_row(line: str) -> list[str]:
	raw = line.strip().strip("|")
	cells = re.split(r"(?<!\\)\|", raw)
	return [cell.strip().replace("\\|", "|") for cell in cells]


def ids(cell: str, pattern: re.Pattern[str]) -> set[str]:
	return {token for token in re.findall(r"`([^`]+)`", cell) if pattern.fullmatch(token)}


def parse_requirements() -> list[dict[str, str]]:
	lines = REQUIREMENTS.read_text(encoding="utf-8").splitlines()
	header = None
	records: list[dict[str, str]] = []
	for line in lines:
		if line.startswith("| ID | Título |"):
			header = split_row(line)
			continue
		if header and line.startswith("| `NXR-"):
			values = split_row(line)
			if len(values) != len(header):
				raise ValueError(f"row has {len(values)} cells, expected {len(header)}: {line[:80]}")
			records.append(dict(zip(header, values, strict=True)))
	return records


def parse_machine_sections(text: str) -> dict[str, dict[str, object]]:
	lines = text.splitlines()
	header = None
	result: dict[str, dict[str, object]] = {}
	for line in lines:
		if line.startswith("| ID | Documento propietario |"):
			header = split_row(line)
			continue
		if header and line.startswith("| `STM-"):
			values = split_row(line)
			record = dict(zip(header, values, strict=True))
			machine_id = record["ID"].strip("`")
			states = {value.strip() for value in record["Estados"].split(",") if value.strip()}
			transitions = []
			for value in record["Transiciones permitidas"].split(";"):
				value = value.strip()
				if not value:
					continue
				source, target = (part.strip() for part in value.split("→", 1))
				transitions.append((source, target))
			result[machine_id] = {"states": states, "transitions": transitions}
	return result


def git_output(*args: str) -> str | None:
	try:
		return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
	except (OSError, subprocess.CalledProcessError):
		return None


def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument("--expected-main-head")
	args = parser.parse_args()

	required_files = [REQUIREMENTS, MACHINES, CONTROLS, DECISIONS, ARCHITECTURE, PLAN, STATE]
	errors = [
		f"missing required file: {path.relative_to(ROOT)}" for path in required_files if not path.is_file()
	]
	if errors:
		die(errors)

	records = parse_requirements()
	req_ids = [record["ID"].strip("`") for record in records]
	if len(records) != 166:
		errors.append(f"expected 166 requirements, found {len(records)}")
	duplicates = [key for key, count in collections.Counter(req_ids).items() if count > 1]
	if duplicates:
		errors.append(f"duplicate requirement IDs: {duplicates}")
	invalid_ids = [value for value in req_ids if not REQUIREMENT_RE.fullmatch(value)]
	if invalid_ids:
		errors.append(f"invalid requirement IDs: {invalid_ids}")

	machine_text = MACHINES.read_text(encoding="utf-8")
	control_text = CONTROLS.read_text(encoding="utf-8")
	decision_text = DECISIONS.read_text(encoding="utf-8")
	machines = parse_machine_sections(machine_text)
	controls = set(re.findall(r"^\| `((?:CTL|TST)-[A-Z0-9-]+)` \|", control_text, flags=re.MULTILINE))
	decisions = set(re.findall(r"^\| `(DEC-\d{3})` \|", decision_text, flags=re.MULTILINE))

	if len(machines) != 37:
		errors.append(f"expected 37 machines, found {len(machines)}")
	control_count = sum(1 for value in controls if value.startswith("CTL-"))
	test_count = sum(1 for value in controls if value.startswith("TST-"))
	if control_count != 32 or test_count != 9:
		errors.append(f"expected 32 controls and 9 shared tests, found {control_count} and {test_count}")
	if decisions != {f"DEC-{number:03d}" for number in range(1, 20)}:
		errors.append(f"decision catalog mismatch: {sorted(decisions)}")

	acceptance_seen: collections.Counter[str] = collections.Counter()
	referenced_decisions: set[str] = set()
	for record in records:
		rid = record["ID"].strip("`")
		state = record["Estado"]
		if state not in ALLOWED_STATES:
			errors.append(f"{rid}: invalid state {state!r}")
		owner = record["Propietario"]
		if not re.fullmatch(r"BLOQUE (?:[0-9]|1[0-9]|20)", owner):
			errors.append(f"{rid}: invalid primary owner {owner!r}")
		machine_cell = record["Máquina"]
		machine_ids = ids(machine_cell, MACHINE_RE)
		if machine_cell != "NO APLICA":
			if len(machine_ids) != 1:
				errors.append(f"{rid}: expected one machine, found {machine_cell!r}")
			elif not machine_ids <= machines.keys():
				errors.append(f"{rid}: nonexistent machine {sorted(machine_ids - machines.keys())}")
		control_ids = ids(record["Controles"], CONTROL_RE)
		if not control_ids:
			errors.append(f"{rid}: no common controls assigned")
		if missing := control_ids - controls:
			errors.append(f"{rid}: nonexistent controls {sorted(missing)}")
		decision_ids = ids(record["Decisiones"], DECISION_RE)
		referenced_decisions.update(decision_ids)
		if missing := decision_ids - decisions:
			errors.append(f"{rid}: nonexistent decisions {sorted(missing)}")
		dependency_ids = ids(record["Dependencias"], REQUIREMENT_RE)
		if missing := dependency_ids - set(req_ids):
			errors.append(f"{rid}: nonexistent requirements {sorted(missing)}")
		acceptance = re.sub(r"`NXR-[A-Z]+-\d{4}`", "`NXR-ID`", record["Aceptación verificable"])
		acceptance = re.sub(r"\s+", " ", acceptance).strip().lower()
		if len(acceptance) < 80:
			errors.append(f"{rid}: acceptance criterion is too short")
		acceptance_seen[acceptance] += 1
		if state == "IMPLEMENTADO Y VALIDADO":
			row_text = " ".join(record.values())
			if not re.search(r"\b[0-9a-f]{40}\b", row_text) or "evidencia" not in row_text.lower():
				errors.append(f"{rid}: IMPLEMENTADO Y VALIDADO lacks SHA and evidence")

	repeated = {text: count for text, count in acceptance_seen.items() if count > 2}
	if repeated:
		errors.append(
			f"mass-repeated acceptance templates detected: {sorted(repeated.values(), reverse=True)[:5]}"
		)
	if referenced_decisions != decisions:
		errors.append(f"unconnected decisions: {sorted(decisions - referenced_decisions)}")

	forbidden_reopen = {("CERRADO", "ABIERTO"), ("EJECUTADO", "BORRADOR"), ("REGISTRADO", "BORRADOR")}
	for machine_id, specification in machines.items():
		states = specification["states"]
		transitions = specification["transitions"]
		if not states:
			errors.append(f"{machine_id}: no states declared")
		for source, target in transitions:
			if source not in states or target not in states:
				errors.append(f"{machine_id}: transition {source}->{target} uses undeclared state")
			allowed_self = {
				("STM-ADVANCE-ACCOUNT", "PARCIALMENTE_LIQUIDADO"),
				("STM-PURCHASE-REQUEST", "CONVERTIDA_PARCIAL"),
				("STM-PURCHASE-ORDER", "RECIBIDA_PARCIAL"),
			}
			if source == target and (machine_id, source) not in allowed_self:
				errors.append(f"{machine_id}: unjustified self-transition {source}->{target}")
			if (source, target) in forbidden_reopen:
				errors.append(f"{machine_id}: forbidden transition {source}->{target}")

	architecture = ARCHITECTURE.read_text(encoding="utf-8")
	plan = PLAN.read_text(encoding="utf-8")
	state_text = STATE.read_text(encoding="utf-8")
	if "NO_MIGRACION_HISTORICA: true" not in architecture:
		errors.append("architecture does not prohibit historical migration")
	if "NO_SEGUNDO_REPOSITORIO: true" not in architecture:
		errors.append("architecture does not prohibit a second repository")
	if "NO_SEGUNDO_LEDGER_CANONICO: true" not in architecture:
		errors.append("architecture does not prohibit a second canonical ledger")
	official_repo = "Clopezgg/Gesti-n-de-Construcci-n-Residencial"
	if official_repo not in architecture or official_repo not in plan or official_repo not in state_text:
		errors.append("official repository is inconsistent across governance files")

	documented_match = re.search(
		r"HEAD (?:inicial de|de) `main`(?: verificado)?: `([0-9a-f]{40})`", state_text
	)
	documented_head = documented_match.group(1) if documented_match else None
	if args.expected_main_head and documented_head != args.expected_main_head:
		errors.append(
			f"documented main HEAD {documented_head!r} differs from expected {args.expected_main_head}"
		)
	origin_main = git_output("rev-parse", "origin/main")
	if origin_main and documented_head != origin_main:
		errors.append(f"documented main HEAD {documented_head} differs from origin/main {origin_main}")

	if errors:
		die(errors)
	print(
		"NEXORA governance valid: "
		f"{len(records)} requirements, {len(machines)} machines, "
		f"{control_count} controls, {test_count} shared tests, {len(decisions)} decisions."
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
