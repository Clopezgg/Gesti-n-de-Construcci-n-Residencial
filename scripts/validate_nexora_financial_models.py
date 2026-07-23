#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCTYPE_ROOT = ROOT / "nexora_app/nexora/nexora/doctype"
EXPECTED = {
	"NXR Document Sequence",
	"NXR Fund Source",
	"NXR Operation",
	"NXR Operation Effect",
	"NXR Fund Allocation",
	"NXR Commitment",
	"NXR Idempotency Record",
	"NXR Audit Event",
}


def main() -> int:
	errors: list[str] = []
	found: set[str] = set()
	for path in DOCTYPE_ROOT.glob("*/*.json"):
		payload = json.loads(path.read_text(encoding="utf-8"))
		if payload.get("name", "").startswith("NXR "):
			found.add(payload["name"])
			fieldnames = [field["fieldname"] for field in payload.get("fields", [])]
			if len(fieldnames) != len(set(fieldnames)):
				errors.append(f"duplicate fields in {payload['name']}")
			if payload.get("module") != "NEXORA":
				errors.append(f"wrong module in {payload['name']}")
	if missing := EXPECTED - found:
		errors.append(f"missing doctypes: {sorted(missing)}")
	patch = ROOT / "nexora_app/nexora/patches/v0_1/create_sequence_counter.py"
	if "AUTO_INCREMENT" not in patch.read_text(encoding="utf-8"):
		errors.append("sequence counter is not native AUTO_INCREMENT")
	if errors:
		for error in errors:
			print(f"ERROR: {error}", file=sys.stderr)
		return 1
	print(f"NEXORA financial model contract valid: {len(EXPECTED)} canonical DocTypes.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
