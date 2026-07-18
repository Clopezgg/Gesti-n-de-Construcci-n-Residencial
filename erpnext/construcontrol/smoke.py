from __future__ import annotations

from collections import Counter
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt

_REQUIRED_DOCTYPES = (
    "CC Project Profile",
    "CC Construction Phase",
    "CC Funding Source",
    "CC Expense Control",
    "CC Labor Contract",
    "CC Material Ledger",
    "CC Inventory Movement",
    "CC Progress Update",
    "CC Weekly Closing",
    "CC Generated Report",
    "CC Notification Contact",
    "CC Notification Rule",
    "CC Notification Log",
    "CC Audit Log",
    "CC User Access",
    "ConstruControl Migration Run",
    "ConstruControl Legacy Record",
)
_REQUIRED_PAGES = (
    "construcontrol-dashboard",
    "construcontrol-migration-console",
    "construcontrol-reporting-center",
    "construcontrol-weekly-closing",
)
_REQUIRED_ROLES = (
    "ConstruControl Manager",
    "ConstruControl Operator",
    "ConstruControl Auditor",
    "ConstruControl Viewer",
)
_DEMO_ITEMS = ("Sneakers", "Coffee Mug", "Television")
_DEMO_PARTIES = (
    "Grant Plastics Ltd.",
    "West View Software Ltd.",
    "Palmer Productions Ltd.",
    "Zuckerman Security Ltd.",
    "MA Inc.",
    "Summit Traders Ltd.",
)


def _require_admin() -> None:
    if "System Manager" not in set(frappe.get_roles()):
        frappe.throw(_("Solo un administrador puede ejecutar la comprobación integral."), frappe.PermissionError)


def _active_expense(row: Any) -> bool:
    return not row.is_logically_deleted and row.financial_status not in {"cancelled", "reimbursed"}


def _permission(doctype: str, role: str) -> dict[str, int]:
    rows = frappe.get_all(
        "DocPerm",
        filters={"parent": doctype, "role": role, "permlevel": 0},
        fields=["read", "write", "create", "delete", "export", "print", "share"],
    )
    if not rows:
        return {}
    return {field: max(int(row.get(field) or 0) for row in rows) for field in rows[0]}


@frappe.whitelist()
def run(require_migration: bool = False, require_no_demo: bool = False) -> dict[str, Any]:
    """Run read-only post-deploy checks against the live ConstruControl database."""
    _require_admin()
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}

    for doctype in _REQUIRED_DOCTYPES:
        if not frappe.db.exists("DocType", doctype):
            errors.append(f"Falta el DocType obligatorio: {doctype}")
    for page in _REQUIRED_PAGES:
        if not frappe.db.exists("Page", page):
            errors.append(f"Falta la página obligatoria: {page}")
    for role in _REQUIRED_ROLES:
        if not frappe.db.exists("Role", role):
            errors.append(f"Falta el rol obligatorio: {role}")

    settings = frappe.get_single("ConstruControl Settings")
    for fieldname in ("require_backup_before_import", "cleanup_demo_after_migration", "import_evidence_files"):
        if not settings.meta.has_field(fieldname):
            errors.append(f"Falta la configuración de seguridad: {fieldname}")
    if settings.meta.has_field("require_backup_before_import") and not settings.require_backup_before_import:
        errors.append("El respaldo obligatorio antes de migrar está desactivado.")
    if settings.meta.has_field("import_evidence_files") and settings.import_evidence_files:
        errors.append("La importación de fotografías históricas está activada.")

    latest_run = frappe.db.get_value(
        "ConstruControl Migration Run",
        {"dry_run": 0},
        ["name", "status", "backup_reference", "source_file"],
        as_dict=True,
        order_by="started_at desc",
    )
    if require_migration and not latest_run:
        errors.append("No existe una migración real ejecutada.")
    if latest_run:
        metrics["latest_migration"] = latest_run.name
        if latest_run.status not in {"Completed", "Completed with Warnings"}:
            errors.append(f"La última migración real no terminó correctamente: {latest_run.status}")
        if not latest_run.backup_reference:
            errors.append("La última migración no conserva referencia del respaldo previo.")
        if latest_run.source_file:
            file_name = frappe.db.get_value("File", {"file_url": latest_run.source_file}, "name")
            if not file_name or not frappe.db.get_value("File", file_name, "is_private"):
                errors.append("El archivo fuente de la migración no está protegido como privado.")

    demo_company = frappe.db.get_single_value("Global Defaults", "demo_company")
    metrics["demo_company"] = demo_company or ""
    if require_no_demo and demo_company:
        errors.append(f"La compañía DEMO continúa registrada: {demo_company}")

    demo_hits: list[str] = []
    for name in _DEMO_ITEMS:
        if frappe.db.exists("Item", name) or frappe.db.exists("Item", {"item_name": name}):
            demo_hits.append(f"Item:{name}")
    for name in _DEMO_PARTIES:
        if frappe.db.exists("Customer", {"customer_name": name}):
            demo_hits.append(f"Customer:{name}")
        if frappe.db.exists("Supplier", {"supplier_name": name}):
            demo_hits.append(f"Supplier:{name}")
    if require_no_demo and demo_hits:
        errors.append("Persisten registros DEMO: " + ", ".join(demo_hits))
    elif demo_hits:
        warnings.append("Se detectaron registros DEMO todavía no retirados: " + ", ".join(demo_hits))

    funds = frappe.get_all(
        "CC Funding Source",
        filters={"is_logically_deleted": 0},
        fields=["name", "amount_hnl", "spent_hnl", "pending_hnl", "available_hnl", "project"],
    )
    expenses = frappe.get_all(
        "CC Expense Control",
        fields=["name", "funding_source", "labor_contract", "status", "financial_status", "amount_hnl", "is_logically_deleted"],
    )
    expenses_by_fund: dict[str, list[Any]] = {}
    expenses_by_contract: dict[str, list[Any]] = {}
    for row in expenses:
        if row.funding_source:
            expenses_by_fund.setdefault(row.funding_source, []).append(row)
        if row.labor_contract:
            expenses_by_contract.setdefault(row.labor_contract, []).append(row)

    for fund in funds:
        active = [row for row in expenses_by_fund.get(fund.name, []) if _active_expense(row)]
        spent = round(sum(flt(row.amount_hnl) for row in active if row.status != "pending" and row.financial_status != "pending"), 2)
        pending = round(sum(flt(row.amount_hnl) for row in active if row.status == "pending" or row.financial_status == "pending"), 2)
        available = round(flt(fund.amount_hnl) - spent, 2)
        if abs(spent - flt(fund.spent_hnl)) > 0.01 or abs(pending - flt(fund.pending_hnl)) > 0.01 or abs(available - flt(fund.available_hnl)) > 0.01:
            errors.append(f"FI01 {fund.name} no está conciliado con sus gastos.")
        if available < -0.01:
            errors.append(f"FI01 {fund.name} tiene saldo negativo.")

    contracts = frappe.get_all(
        "CC Labor Contract",
        filters={"is_logically_deleted": 0},
        fields=["name", "project_value_hnl", "labor_value_hnl", "paid_hnl", "balance_hnl"],
    )
    for contract in contracts:
        active = [row for row in expenses_by_contract.get(contract.name, []) if _active_expense(row) and row.financial_status != "pending"]
        paid = round(sum(flt(row.amount_hnl) for row in active), 2)
        value = flt(contract.project_value_hnl or contract.labor_value_hnl)
        if abs(paid - flt(contract.paid_hnl)) > 0.01 or abs(value - paid - flt(contract.balance_hnl)) > 0.01:
            errors.append(f"CO01 {contract.name} no está conciliado con sus pagos.")

    negative_materials = frappe.get_all(
        "CC Material Ledger",
        filters={"is_logically_deleted": 0, "current_qty": ["<", 0]},
        pluck="name",
    )
    if negative_materials:
        errors.append("Existen materiales con inventario negativo: " + ", ".join(negative_materials[:20]))

    user_rows = frappe.get_all(
        "CC User Access",
        filters={"is_logically_deleted": 0},
        fields=["name", "email", "role_name", "role_label"],
    )
    normalized_emails = [str(row.email or "").strip().casefold() for row in user_rows if row.email]
    duplicate_emails = sorted(email for email, count in Counter(normalized_emails).items() if count > 1)
    if duplicate_emails:
        errors.append("US01 contiene correos duplicados: " + ", ".join(duplicate_emails))
    for row in user_rows:
        if row.role_label and str(row.role_label).casefold() == str(row.email or "").casefold():
            errors.append(f"US01 {row.name} muestra el correo como rol.")

    audit_fields = {field.fieldname for field in frappe.get_meta("CC Audit Log").fields}
    for fieldname in ("actor_name", "actor_email", "actor_role", "actor_user_id"):
        if fieldname not in audit_fields:
            errors.append(f"AU01 no separa el campo de identidad: {fieldname}")

    visible_integrations = []
    for name in ("ERPNext Integrations", "Integrations", "Integrations NEXT", "Integraciones", "Integraciones NEXT"):
        if not frappe.db.exists("Workspace", name):
            continue
        hidden = frappe.db.get_value("Workspace", name, "is_hidden")
        if not hidden:
            visible_integrations.append(name)
    if len(visible_integrations) > 1:
        errors.append("Persisten secciones de integraciones duplicadas: " + ", ".join(visible_integrations))

    viewer_audit = _permission("CC Audit Log", "ConstruControl Viewer")
    viewer_user_access = _permission("CC User Access", "ConstruControl Viewer")
    operator_migration = _permission("ConstruControl Migration Run", "ConstruControl Operator")
    if not viewer_audit.get("read") or viewer_audit.get("write") or viewer_audit.get("delete"):
        errors.append("Los permisos Viewer de AU01 no son de solo lectura.")
    if viewer_user_access.get("read"):
        errors.append("Viewer no debe acceder al registro administrativo US01.")
    if operator_migration.get("create") or operator_migration.get("write") or operator_migration.get("delete"):
        errors.append("Operator conserva permisos administrativos sobre migraciones.")

    external_url = str(frappe.conf.get("host_name") or frappe.conf.get("frappe_external_url") or "")
    metrics["external_url"] = external_url
    if external_url and not external_url.startswith("https://"):
        warnings.append("La URL externa configurada no utiliza HTTPS.")

    metrics.update(
        {
            "funds": len(funds),
            "expenses": len([row for row in expenses if not row.is_logically_deleted]),
            "contracts": len(contracts),
            "materials": frappe.db.count("CC Material Ledger", {"is_logically_deleted": 0}),
            "weekly_closings": frappe.db.count("CC Weekly Closing", {"is_logically_deleted": 0}),
            "audit_events": frappe.db.count("CC Audit Log", {"is_logically_deleted": 0}),
            "users": len(user_rows),
        }
    )

    return {"ok": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}
