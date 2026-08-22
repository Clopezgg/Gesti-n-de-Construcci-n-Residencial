from __future__ import annotations

import argparse
import frappe

def main() -> int:
    parser = argparse.ArgumentParser(description="NEXORA: audit remittances/funds before central-treasury migration")
    parser.add_argument("--apply", action="store_true", help="Reserved for an explicitly approved runtime migration; never run implicitly.")
    parser.add_argument("--backup-marker", default="", help="Verified backup receipt path/hash marker.")
    args = parser.parse_args()
    source_count = frappe.db.count("NXR Fund Source", {"project": ["is", "set"]})
    remittance_count = frappe.db.count("NXR Remittance", {"project": ["is", "set"]})
    print(f"FUND_SOURCES_WITH_PROJECT={source_count}")
    print(f"REMITTANCES_WITH_PROJECT={remittance_count}")
    print("DRY_RUN_ONLY=1")
    print("NO_RECORDS_MODIFIED=1")
    if args.apply:
        raise SystemExit("Refusing migration in code block: runtime backup, rollback and exact record reconciliation must be completed first.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
