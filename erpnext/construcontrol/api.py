from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime
from frappe.utils.file_manager import save_file

from erpnext.construcontrol.migration.backup_reader import BackupFormatError, load_backup_content
from erpnext.construcontrol.migration.importer import run_import, validate_payload

ALLOWED_EXTENSIONS = (".tar.gz", ".tgz", ".sql", ".sql.gz", ".json")
MAX_UPLOAD_BYTES = 64 * 1024 * 1024


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str)


def _require_manager() -> None:
    roles = set(frappe.get_roles())
    if not ({"System Manager", "ConstruControl Manager"} & roles):
        frappe.throw(_("No tiene permisos para ejecutar la migración."), frappe.PermissionError)


def _require_reader() -> None:
    roles = set(frappe.get_roles())
    allowed = {"System Manager", "ConstruControl Manager", "ConstruControl Auditor", "ConstruControl Operator", "ConstruControl Viewer"}
    if not (allowed & roles):
        frappe.throw(_("No tiene permisos para consultar ConstruControl."), frappe.PermissionError)


def _uploaded_bytes() -> tuple[bytes, str]:
    content = getattr(frappe.local, "uploaded_file", None)
    filename = str(getattr(frappe.local, "uploaded_filename", "") or "").strip()
    if not isinstance(content, (bytes, bytearray)) or not filename:
        frappe.throw(_("No se recibió un archivo válido."))
    if len(content) > MAX_UPLOAD_BYTES:
        frappe.throw(_("El respaldo supera el límite de seguridad de 64 MiB."))
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        frappe.throw(_("Formato no admitido. Use TAR.GZ, TGZ, SQL, SQL.GZ o JSON."))
    return bytes(content), filename


def _new_run(*, dry_run: bool, source_kind: str, source_sha: str) -> Any:
    return frappe.get_doc({
        "doctype": "ConstruControl Migration Run",
        "status": "Validating",
        "dry_run": cint(dry_run),
        "source_kind": "Supabase Export" if source_kind == "Supabase Logical Backup" else (
            source_kind if source_kind in {"ConstruControl Backup", "Supabase Export", "LocalStorage Export"}
            else "ConstruControl Backup"
        ),
        "source_sha256": source_sha,
        "started_at": now_datetime(),
        "rollback_status": "Not Requested",
    }).insert(ignore_permissions=True)


def _file_for_run(run: Any, content: bytes, filename: str) -> Any:
    safe_name = Path(filename).name
    file_doc = save_file(safe_name, content, run.doctype, run.name, is_private=1)
    run.source_file = file_doc.file_url
    run.save(ignore_permissions=True)
    return file_doc


def _read_run_file(run: Any) -> tuple[bytes, str]:
    if not run.source_file:
        frappe.throw(_("La ejecución no tiene un archivo privado adjunto."))
    file_name = frappe.db.get_value("File", {"file_url": run.source_file}, "name")
    if not file_name:
        frappe.throw(_("No se encontró el archivo privado de la migración."))
    file_doc = frappe.get_doc("File", file_name)
    return file_doc.get_content(), file_doc.file_name


def _set_failed(run: Any, exc: Exception) -> None:
    frappe.db.rollback()
    try:
        run = frappe.get_doc(run.doctype, run.name)
        run.db_set({
            "status": "Failed",
            "completed_at": now_datetime(),
            "error_log": frappe.get_traceback() if frappe.get_traceback() else str(exc),
        }, update_modified=False)
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()


def _create_database_backup() -> str:
    bench = shutil.which("bench")
    bench_root = Path("/home/frappe/frappe-bench")
    if not bench or not bench_root.exists():
        frappe.throw(_("No se encontró Bench; la migración definitiva fue bloqueada antes de escribir datos."))
    site = str(frappe.local.site)
    backup_dir = bench_root / "sites" / site / "private" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    before = {p.resolve() for p in backup_dir.glob("*") if p.is_file()}
    process = subprocess.run(
        [bench, "--site", site, "backup", "--with-files"],
        cwd=bench_root,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if process.returncode != 0:
        frappe.throw(_("No se pudo crear el respaldo previo. La migración fue cancelada. Detalle: {0}").format(process.stderr[-1200:]))
    created = sorted(
        (p for p in backup_dir.glob("*") if p.is_file() and p.resolve() not in before),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    database_files = [p for p in created if "database" in p.name and p.suffix == ".gz"]
    selected = database_files[0] if database_files else (created[0] if created else None)
    if not selected or not selected.exists() or selected.stat().st_size == 0:
        frappe.throw(_("Bench no produjo un respaldo verificable. La migración fue cancelada."))
    return str(selected)


def _cleanup_demo_data() -> dict[str, Any]:
    demo_company = frappe.db.get_single_value("Global Defaults", "demo_company")
    if not demo_company:
        return {"requested": False, "status": "not_present", "message": "No había una compañía demo registrada."}
    from erpnext.setup.demo import clear_demo_data
    clear_demo_data()
    return {"requested": True, "status": "started", "company": demo_company, "message": "ERPNext inició la eliminación oficial de los datos demo."}


@frappe.whitelist()
def upload_and_validate() -> dict[str, Any]:
    _require_manager()
    content, filename = _uploaded_bytes()
    source_sha = hashlib.sha256(content).hexdigest()
    run = None
    try:
        payload, reader_report = load_backup_content(content, filename)
        validation = validate_payload(payload)
        run = _new_run(dry_run=True, source_kind=reader_report["source_kind"], source_sha=source_sha)
        _file_for_run(run, content, filename)
        result = run_import(payload, run.name, dry_run=True)
        status = "Completed with Warnings" if validation.get("warnings") else "Completed"
        run.db_set({
            "status": status,
            "completed_at": now_datetime(),
            "input_counts_json": _json(validation.get("counts", {})),
            "output_counts_json": _json({}),
            "validation_report_json": _json({"reader": reader_report, "validation": validation}),
            "error_log": "",
        }, update_modified=False)
        frappe.db.commit()
        return {
            "migration_run": run.name,
            "source_sha256": source_sha,
            "reader": reader_report,
            "validation": validation,
            "dry_run": result,
        }
    except (BackupFormatError, ValueError, json.JSONDecodeError) as exc:
        if run:
            _set_failed(run, exc)
        frappe.throw(str(exc), title=_("Respaldo no válido"))
    except Exception as exc:
        if run:
            _set_failed(run, exc)
        raise


@frappe.whitelist()
def execute_migration(validation_run: str, confirmation: str) -> dict[str, Any]:
    _require_manager()
    if str(confirmation or "").strip().upper() != "MIGRAR":
        frappe.throw(_("Escriba MIGRAR para confirmar la operación."))
    validated_run = frappe.get_doc("ConstruControl Migration Run", validation_run)
    if not validated_run.dry_run or validated_run.status not in {"Completed", "Completed with Warnings"}:
        frappe.throw(_("Primero debe completar una validación exitosa del respaldo."))
    content, filename = _read_run_file(validated_run)
    source_sha = hashlib.sha256(content).hexdigest()
    if source_sha != validated_run.source_sha256:
        frappe.throw(_("La huella del archivo cambió. La migración fue bloqueada."))
    payload, reader_report = load_backup_content(content, filename)
    validation = validate_payload(payload)
    if not validation.get("valid"):
        frappe.throw(_("El archivo dejó de superar la validación."))

    run = _new_run(dry_run=False, source_kind=reader_report["source_kind"], source_sha=source_sha)
    _file_for_run(run, content, filename)
    try:
        settings = frappe.get_single("ConstruControl Settings")
        require_backup = cint(settings.get("require_backup_before_import")) if settings.meta.has_field("require_backup_before_import") else 1
        if not require_backup:
            frappe.throw(_("La política de respaldo obligatorio está desactivada. Se bloqueó la migración por seguridad."))
        backup_reference = _create_database_backup()
        run.db_set({"status": "Running", "backup_reference": backup_reference, "rollback_status": "Ready"}, update_modified=False)
        frappe.db.commit()

        result = run_import(payload, run.name, dry_run=False)
        run.db_set({
            "status": "Completed with Warnings" if validation.get("warnings") else "Completed",
            "completed_at": now_datetime(),
            "input_counts_json": _json(result.get("input_counts", {})),
            "output_counts_json": _json(result.get("output_counts", {})),
            "validation_report_json": _json({"reader": reader_report, "validation": validation, "result": result}),
            "error_log": "",
        }, update_modified=False)
        if settings.meta.has_field("last_migration_run"):
            frappe.db.set_single_value("ConstruControl Settings", "last_migration_run", run.name)
        if settings.meta.has_field("last_migration_at"):
            frappe.db.set_single_value("ConstruControl Settings", "last_migration_at", now_datetime())
        frappe.db.commit()

        cleanup = {"requested": False, "status": "disabled"}
        cleanup_demo = cint(settings.get("cleanup_demo_after_migration")) if settings.meta.has_field("cleanup_demo_after_migration") else 1
        if cleanup_demo:
            try:
                cleanup = _cleanup_demo_data()
                frappe.db.commit()
            except Exception as cleanup_error:
                frappe.db.rollback()
                cleanup = {"requested": True, "status": "failed", "message": str(cleanup_error)}
                run.db_set({
                    "status": "Completed with Warnings",
                    "error_log": "Los datos se migraron y conciliaron, pero la limpieza demo requiere revisión: " + str(cleanup_error),
                }, update_modified=False)
                frappe.db.commit()
        return {"migration_run": run.name, "backup_reference": backup_reference, "result": result, "demo_cleanup": cleanup}
    except Exception as exc:
        _set_failed(run, exc)
        raise


@frappe.whitelist()
def get_dashboard_summary() -> dict[str, Any]:
    _require_reader()
    funds = frappe.get_all("CC Funding Source", filters={"is_logically_deleted": 0}, fields=["status", "amount_hnl", "spent_hnl", "pending_hnl", "available_hnl"])
    expenses = frappe.get_all("CC Expense Control", filters={"is_logically_deleted": 0}, fields=["status", "financial_status", "amount_hnl"])
    contracts = frappe.get_all("CC Labor Contract", filters={"is_logically_deleted": 0}, fields=["project_value_hnl", "labor_value_hnl", "paid_hnl", "balance_hnl"])
    phases = frappe.get_all("CC Construction Phase", filters={"is_logically_deleted": 0}, fields=["progress_percent", "budget_hnl"])
    received = sum(flt(row.amount_hnl) for row in funds if row.status == "received")
    spent = sum(flt(row.amount_hnl) for row in expenses if row.status != "pending" and row.financial_status not in {"cancelled", "reimbursed"})
    pending = sum(flt(row.amount_hnl) for row in expenses if row.status == "pending" or row.financial_status == "pending")
    active_contracts = sum(flt(row.project_value_hnl or row.labor_value_hnl) for row in contracts)
    progress = round(sum(flt(row.progress_percent) for row in phases) / len(phases), 2) if phases else 0
    demo_company = frappe.db.get_single_value("Global Defaults", "demo_company")
    return {
        "received_hnl": round(received, 2), "spent_hnl": round(spent, 2), "pending_hnl": round(pending, 2),
        "available_hnl": round(received - spent, 2), "contracted_hnl": round(active_contracts, 2),
        "fund_count": len(funds), "expense_count": len(expenses), "contract_count": len(contracts), "phase_count": len(phases),
        "overall_progress": progress, "demo_present": bool(demo_company), "demo_company": demo_company,
        "last_migration_run": frappe.db.get_value(
            "ConstruControl Migration Run", {"dry_run": 0}, "name", order_by="started_at desc"
        ),
        "images_imported": 0,
    }
