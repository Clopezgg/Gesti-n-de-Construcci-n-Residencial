from __future__ import annotations


def _run_construcontrol_install() -> None:
    """Run migration-backed setup in the same guarded context used by Frappe."""
    import frappe

    from erpnext.construcontrol.install import after_migrate

    had_flag = "in_migrate" in frappe.flags
    previous = frappe.flags.get("in_migrate")
    frappe.flags.in_migrate = True
    try:
        after_migrate()
    finally:
        if had_flag:
            frappe.flags.in_migrate = previous
        else:
            frappe.flags.pop("in_migrate", None)


def after_install() -> None:
    """Run ERPNext's official installer, then install ConstruControl runtime."""
    from erpnext.setup.install import after_install as erpnext_after_install

    erpnext_after_install()
    _run_construcontrol_install()
