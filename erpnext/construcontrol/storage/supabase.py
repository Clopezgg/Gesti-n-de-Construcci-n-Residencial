from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen

import frappe
from frappe import _

REMOTE_PREFIX = "/api/method/erpnext.construcontrol.storage.supabase.download?object_key="
CHUNK_SIZE = 1024 * 1024
MAX_REMOTE_FILE_BYTES = 64 * 1024 * 1024


def _enabled() -> bool:
    return os.getenv("SUPABASE_STORAGE_MODE", "").strip().lower() == "enabled"


def _server_key() -> str:
    for name in ("SUPABASE_SERVER_KEY", "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _validated_supabase_url(value: str) -> str:
    url = str(value or "").strip().rstrip("/")
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").casefold()
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or not hostname.endswith(".supabase.co")
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        frappe.throw(
            _("SUPABASE_URL debe ser una URL HTTPS directa del proyecto con formato https://PROYECTO.supabase.co."),
            title=_("Configuración de Storage no válida"),
        )
    return url


def _configuration(bucket_override: str | None = None) -> tuple[str, str, str]:
    url = _validated_supabase_url(os.getenv("SUPABASE_URL", ""))
    key = _server_key()
    bucket = str(bucket_override or os.getenv("SUPABASE_STORAGE_BUCKET", "construction-evidence")).strip()
    if not key or not bucket:
        frappe.throw(
            _("Supabase Storage está activado, pero falta su configuración privada del servidor."),
            title=_("Error de configuración de Storage"),
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", bucket):
        frappe.throw(_("El nombre del bucket no es válido."), frappe.PermissionError)
    return url, key, bucket


def _auth_headers(key: str) -> dict[str, str]:
    headers = {"apikey": key, "User-Agent": "ConstruControl-Server/1.0"}
    # sb_secret_ keys are opaque API keys, not JWTs. Legacy service_role values
    # remain supported only on the server and still require the Bearer header.
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _safe_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.basename(value)).strip("._")
    return name[:180] or "attachment.bin"


def _safe_object_key(value: str) -> str:
    parts = [part for part in str(value or "").replace("\\", "/").split("/") if part]
    if (
        not parts
        or len(parts) > 32
        or any(part in {".", ".."} for part in parts)
        or any(len(part) > 255 for part in parts)
        or any(any(ord(character) < 32 for character in part) for part in parts)
    ):
        frappe.throw(_("Clave de objeto de Storage no válida."), frappe.PermissionError)
    return "/".join(parts)


def _encoded_object_path(bucket: str, object_key: str) -> str:
    bucket_part = quote(bucket, safe="")
    key_part = "/".join(quote(part, safe="") for part in _safe_object_key(object_key).split("/"))
    return f"{bucket_part}/{key_part}"


def _object_key(file_name: str, content: bytes, is_private: int | bool) -> str:
    digest = hashlib.sha256(content).hexdigest()
    site = _safe_name(getattr(frappe.local, "site", None) or "default")
    visibility = "private" if is_private else "authenticated"
    return f"frappe/{site}/{visibility}/{digest[:2]}/{digest}-{_safe_name(file_name)}"


def upload_object(bucket: str, object_key: str, content: bytes, content_type: str | None = None) -> None:
    if len(content) > MAX_REMOTE_FILE_BYTES:
        frappe.throw(_("El archivo supera el límite remoto de 64 MiB."))
    url, key, _ = _configuration(bucket)
    endpoint = f"{url}/storage/v1/object/{_encoded_object_path(bucket, object_key)}"
    headers = {
        **_auth_headers(key),
        "Content-Type": content_type or "application/octet-stream",
        "Content-Length": str(len(content)),
        "x-upsert": "true",
    }
    request = Request(endpoint, data=content, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=120) as response:  # nosec B310: URL is strictly validated above.
            response.read()
    except HTTPError as exc:
        frappe.throw(
            _("Falló la carga a Supabase Storage con estado HTTP {0}.").format(exc.code),
            title=_("Falló la solicitud de Storage"),
        )


def download_object_to_path(
    bucket: str,
    object_key: str,
    target: str | Path,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    url, key, _ = _configuration(bucket)
    endpoint = f"{url}/storage/v1/object/authenticated/{_encoded_object_path(bucket, object_key)}"
    request = Request(endpoint, headers=_auth_headers(key), method="GET")
    target_path = Path(target).expanduser().resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    total = 0
    effective_limit = min(max_bytes or MAX_REMOTE_FILE_BYTES, MAX_REMOTE_FILE_BYTES)
    try:
        with urlopen(request, timeout=180) as response, target_path.open("wb") as handle:  # nosec B310
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > effective_limit:
                raise ValueError("Storage object exceeds the configured download limit.")
            while chunk := response.read(CHUNK_SIZE):
                total += len(chunk)
                if total > effective_limit:
                    raise ValueError("Storage object exceeds the configured download limit.")
                handle.write(chunk)
                digest.update(chunk)
    except HTTPError as exc:
        target_path.unlink(missing_ok=True)
        frappe.throw(
            _("Falló la descarga de Supabase Storage con estado HTTP {0}.").format(exc.code),
            title=_("Falló la solicitud de Storage"),
        )
    except Exception:
        target_path.unlink(missing_ok=True)
        raise
    return {"bytes": total, "sha256": digest.hexdigest(), "path": str(target_path)}


def download_object_bytes(bucket: str, object_key: str, max_bytes: int = 16 * 1024 * 1024) -> bytes:
    effective_limit = min(max_bytes, MAX_REMOTE_FILE_BYTES)
    url, key, _ = _configuration(bucket)
    endpoint = f"{url}/storage/v1/object/authenticated/{_encoded_object_path(bucket, object_key)}"
    request = Request(endpoint, headers=_auth_headers(key), method="GET")
    try:
        with urlopen(request, timeout=120) as response:  # nosec B310
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > effective_limit:
                frappe.throw(_("El objeto de Storage supera el tamaño permitido."))
            content = response.read(effective_limit + 1)
    except HTTPError as exc:
        frappe.throw(
            _("Falló la descarga de Supabase Storage con estado HTTP {0}.").format(exc.code),
            title=_("Falló la solicitud de Storage"),
        )
    if len(content) > effective_limit:
        frappe.throw(_("El objeto de Storage supera el tamaño permitido."))
    return content


def delete_object(bucket: str, object_key: str) -> None:
    url, key, _ = _configuration(bucket)
    payload = json.dumps({"prefixes": [_safe_object_key(object_key)]}).encode("utf-8")
    request = Request(
        f"{url}/storage/v1/object/{quote(bucket, safe='')}",
        data=payload,
        headers={
            **_auth_headers(key),
            "Content-Type": "application/json",
            "Content-Length": str(len(payload)),
        },
        method="DELETE",
    )
    try:
        with urlopen(request, timeout=60) as response:  # nosec B310
            response.read()
    except HTTPError as exc:
        frappe.throw(
            _("Falló la eliminación en Supabase Storage con estado HTTP {0}.").format(exc.code),
            title=_("Falló la solicitud de Storage"),
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

    _, _, bucket = _configuration()
    if len(args) == 1 and hasattr(args[0], "_content"):
        doc = args[0]
        content = doc._content.encode() if isinstance(doc._content, str) else bytes(doc._content)
        content_type = getattr(doc, "content_type", None) or mimetypes.guess_type(doc.file_name)[0]
        key = _object_key(doc.file_name, content, doc.is_private)
        upload_object(bucket, key, content, content_type)
        doc.file_name = _safe_name(doc.file_name)
        doc.file_url = _remote_url(key)
        return {"file_name": doc.file_name, "file_url": doc.file_url}

    file_name, content = args[:2]
    content_bytes = content.encode() if isinstance(content, str) else bytes(content)
    content_type = kwargs.get("content_type") or mimetypes.guess_type(str(file_name))[0]
    key = _object_key(str(file_name), content_bytes, kwargs.get("is_private", 0))
    upload_object(bucket, key, content_bytes, content_type)
    return {"file_name": _safe_name(str(file_name)), "file_url": _remote_url(key)}


def delete_file(doc: Any, only_thumbnail: bool = False) -> None:
    key = _extract_key(getattr(doc, "file_url", None))
    if key and _enabled() and not only_thumbnail:
        _, _, bucket = _configuration()
        delete_object(bucket, key)
        return
    from frappe.utils.file_manager import delete_file_from_filesystem

    delete_file_from_filesystem(doc, only_thumbnail=only_thumbnail)


@frappe.whitelist()
def download(object_key: str) -> None:
    """Stream one remote object only to an authenticated user with File permission."""
    if frappe.session.user == "Guest":
        frappe.throw(_("Debe iniciar sesión para descargar archivos."), frappe.PermissionError)
    if not _enabled() or not object_key or not object_key.startswith("frappe/") or ".." in object_key.split("/"):
        frappe.throw(_("Objeto de Storage no válido."), frappe.PermissionError)

    file_url = _remote_url(object_key)
    file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
    if not file_name:
        frappe.throw(_("Archivo no encontrado."), frappe.DoesNotExistError)
    file_doc = frappe.get_doc("File", file_name)
    if not file_doc.has_permission("read"):
        frappe.throw(_("No tiene permiso para descargar este archivo."), frappe.PermissionError)

    _, _, bucket = _configuration()
    content = download_object_bytes(bucket, object_key)
    frappe.local.response.filename = file_doc.file_name
    frappe.local.response.filecontent = content
    frappe.local.response.type = "download"
    frappe.local.response.display_content_as = "attachment"
