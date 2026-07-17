from __future__ import annotations

import hashlib
import mimetypes
import os
import re
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen

import frappe
from frappe import _


REMOTE_PREFIX = "/api/method/erpnext.construcontrol.storage.supabase.download?object_key="


def _enabled() -> bool:
	return os.getenv("SUPABASE_STORAGE_MODE", "").strip().lower() == "enabled"


def _configuration() -> tuple[str, str, str]:
	url = os.getenv("SUPABASE_URL", "").rstrip("/")
	key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
	bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "construction-evidence")
	if not url or not key or not bucket:
		frappe.throw(
			_("Supabase Storage is enabled but its server-side configuration is incomplete."),
			title=_("Storage configuration error"),
		)
	return url, key, bucket


def _safe_name(value: str) -> str:
	name = re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.basename(value)).strip("._")
	return name[:180] or "attachment.bin"


def _object_key(file_name: str, content: bytes, is_private: int | bool) -> str:
	digest = hashlib.sha256(content).hexdigest()
	site = _safe_name(getattr(frappe.local, "site", None) or "default")
	visibility = "private" if is_private else "public"
	return f"frappe/{site}/{visibility}/{digest[:2]}/{digest}-{_safe_name(file_name)}"


def _headers(content_type: str | None = None) -> dict[str, str]:
	_, key, _ = _configuration()
	headers = {"Authorization": f"Bearer {key}", "apikey": key}
	if content_type:
		headers["Content-Type"] = content_type
	return headers


def _request(method: str, object_key: str, content: bytes | None = None, content_type: str | None = None) -> bytes:
	url, _, bucket = _configuration()
	path = "/".join(quote(part, safe="") for part in object_key.split("/"))
	endpoint = f"{url}/storage/v1/object/{quote(bucket, safe='')}/{path}"
	headers = _headers(content_type)
	if method in {"POST", "PUT"}:
		headers["x-upsert"] = "true"
	request = Request(endpoint, data=content, headers=headers, method=method)
	try:
		with urlopen(request, timeout=60) as response:  # nosec B310: URL is administrator configured.
			return response.read()
	except HTTPError as exc:
		# Do not include response bodies: Storage errors can echo sensitive policy context.
		frappe.throw(
			_("Supabase Storage request failed with HTTP status {0}.").format(exc.code),
			title=_("Storage request failed"),
		)


def _remote_url(object_key: str) -> str:
	return REMOTE_PREFIX + quote(object_key, safe="")


def _extract_key(file_url: str | None) -> str | None:
	if not file_url or not file_url.startswith(REMOTE_PREFIX):
		return None
	key = unquote(file_url[len(REMOTE_PREFIX) :])
	if not key.startswith("frappe/") or ".." in key.split("/"):
		return None
	return key


def write_file(*args: Any, **kwargs: Any) -> Any:
	"""Write both Frappe v15 File objects and legacy file-manager calls."""
	if not _enabled():
		if len(args) == 1 and hasattr(args[0], "save_file_on_filesystem"):
			return args[0].save_file_on_filesystem()
		from frappe.utils.file_manager import save_file_on_filesystem

		return save_file_on_filesystem(*args, **kwargs)

	if len(args) == 1 and hasattr(args[0], "_content"):
		doc = args[0]
		content = doc._content.encode() if isinstance(doc._content, str) else bytes(doc._content)
		content_type = getattr(doc, "content_type", None) or mimetypes.guess_type(doc.file_name)[0]
		key = _object_key(doc.file_name, content, doc.is_private)
		_request("POST", key, content, content_type or "application/octet-stream")
		doc.file_name = _safe_name(doc.file_name)
		doc.file_url = _remote_url(key)
		return {"file_name": doc.file_name, "file_url": doc.file_url}

	file_name, content = args[:2]
	content_bytes = content.encode() if isinstance(content, str) else bytes(content)
	content_type = kwargs.get("content_type") or mimetypes.guess_type(str(file_name))[0]
	key = _object_key(str(file_name), content_bytes, kwargs.get("is_private", 0))
	_request("POST", key, content_bytes, content_type or "application/octet-stream")
	return {"file_name": _safe_name(str(file_name)), "file_url": _remote_url(key)}


def delete_file(doc: Any, only_thumbnail: bool = False) -> None:
	key = _extract_key(getattr(doc, "file_url", None))
	if key and _enabled() and not only_thumbnail:
		_request("DELETE", key)
		return
	from frappe.utils.file_manager import delete_file_from_filesystem

	delete_file_from_filesystem(doc, only_thumbnail=only_thumbnail)


@frappe.whitelist(allow_guest=True)
def download(object_key: str) -> None:
	"""Stream one remote object after enforcing the corresponding Frappe File permission."""
	if not _enabled() or not object_key or not object_key.startswith("frappe/") or ".." in object_key.split("/"):
		frappe.throw(_("Invalid storage object."), frappe.PermissionError)
	file_url = _remote_url(object_key)
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not file_name:
		frappe.throw(_("File not found."), frappe.DoesNotExistError)
	file_doc = frappe.get_doc("File", file_name)
	if file_doc.is_private and not file_doc.has_permission("read"):
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	content = _request("GET", object_key)
	frappe.local.response.filename = file_doc.file_name
	frappe.local.response.filecontent = content
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"
