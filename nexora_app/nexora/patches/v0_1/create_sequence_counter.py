from __future__ import annotations

import frappe


def execute() -> None:
	frappe.db.sql(
		"""
        CREATE TABLE IF NOT EXISTS `tabNXR Document Sequence Counter` (
            `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            `issued_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            PRIMARY KEY (`id`)
        ) ENGINE=InnoDB
        """
	)
