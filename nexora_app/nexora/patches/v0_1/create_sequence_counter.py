from __future__ import annotations

import frappe

TABLE = "tabNXR Document Sequence Counter"


def execute() -> None:
    frappe.db.sql(
        f"""
        CREATE TABLE IF NOT EXISTS `{TABLE}` (
            `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            `issued_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            PRIMARY KEY (`id`)
        ) ENGINE=InnoDB
        """
    )
