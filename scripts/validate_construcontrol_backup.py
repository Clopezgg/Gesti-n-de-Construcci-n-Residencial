#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "erpnext" / "construcontrol" / "migration" / "schema.py"


def load_schema():
	spec = importlib.util.spec_from_file_location("construcontrol_schema", SCHEMA_PATH)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Cannot load migration schema from {SCHEMA_PATH}")
	module = importlib.util.module_from_spec(spec)
	sys.modules[spec.name] = module
	spec.loader.exec_module(module)
	return module


def main() -> int:
	parser = argparse.ArgumentParser(description="Validate and reconcile a ConstruControl JSON export.")
	parser.add_argument("source", type=Path, help="Backup, localStorage export, or Supabase JSON export")
	parser.add_argument("--report", type=Path, help="Optional path for the JSON validation report")
	parser.add_argument(
		"--allow-relational-errors",
		action="store_true",
		help="Return success even when duplicates or orphan references are detected",
	)
	args = parser.parse_args()

	schema = load_schema()
	raw = args.source.read_bytes()
	payload = json.loads(raw.decode("utf-8-sig"))
	projects = schema.normalize_export_document(payload)
	project_reports = [
		{"project_key": project.project_key, "report": schema.preflight_snapshot(project.snapshot)}
		for project in projects
	]
	report = {
		"source": str(args.source.resolve()),
		"source_sha256": __import__("hashlib").sha256(raw).hexdigest(),
		"project_count": len(projects),
		"aggregate_counts": schema.aggregate_counts(item["report"] for item in project_reports),
		"projects": project_reports,
	}
	rendered = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
	print(rendered)
	if args.report:
		args.report.parent.mkdir(parents=True, exist_ok=True)
		args.report.write_text(rendered + "\n", encoding="utf-8")
	error_count = sum(item["report"]["error_count"] for item in project_reports)
	return 0 if args.allow_relational_errors or error_count == 0 else 2


if __name__ == "__main__":
	raise SystemExit(main())
