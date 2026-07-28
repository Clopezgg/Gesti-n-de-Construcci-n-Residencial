from __future__ import annotations

from typing import Any

import frappe

from nexora.email_prompt_policy import (
	pending_emails_are_generic,
	remove_prompt_user,
	split_prompt_users,
)


def suppress_generic_email_password_prompt(bootinfo: Any) -> None:
	"""Hide Frappe's email-password setup dialog only for known placeholder accounts.

	This changes the boot response, not the stored User or Email Account records. Real pending
	email accounts continue to trigger Frappe's normal password validation dialog.
	"""
	sysdefaults = getattr(bootinfo, "sysdefaults", None)
	if sysdefaults is None and isinstance(bootinfo, dict):
		sysdefaults = bootinfo.get("sysdefaults")
	if not isinstance(sysdefaults, dict):
		return

	prompt_value = sysdefaults.get("email_user_password")
	user = str(getattr(frappe.session, "user", "") or "")
	if not user or user not in split_prompt_users(prompt_value):
		return

	pending_email_ids = frappe.get_all(
		"User Email",
		filters={
			"parent": user,
			"parenttype": "User",
			"parentfield": "user_emails",
			"awaiting_password": 1,
		},
		pluck="email_id",
	)
	if not pending_emails_are_generic(pending_email_ids):
		return

	updated_value = remove_prompt_user(prompt_value, user)
	if updated_value is None:
		sysdefaults.pop("email_user_password", None)
	else:
		sysdefaults["email_user_password"] = updated_value
