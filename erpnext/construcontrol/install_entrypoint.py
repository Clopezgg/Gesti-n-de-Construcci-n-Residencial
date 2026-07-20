from __future__ import annotations


def after_install() -> None:
    """Run ERPNext's official installer, then install ConstruControl runtime."""
    from erpnext.setup.install import after_install as erpnext_after_install

    from erpnext.construcontrol.install import after_migrate

    erpnext_after_install()
    after_migrate()
