#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import mimetypes
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

CHUNK_SIZE = 1024 * 1024


def require_env(name: str) -> str:
	value = os.environ.get(name, "").strip()
	if not value:
		raise RuntimeError(f"Missing required environment variable: {name}")
	return value


def server_key() -> str:
	for name in ("SUPABASE_SERVER_KEY", "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
		value = os.environ.get(name, "").strip()
		if value:
			return value
	raise RuntimeError(
		"Missing server-side Supabase key. Set SUPABASE_SERVER_KEY to an sb_secret_ key "
		"or, temporarily, to the legacy service_role JWT."
	)


def auth_headers(key: str) -> dict[str, str]:
	headers = {"apikey": key}
	# New sb_secret_ keys are opaque API keys and must not be sent as Bearer JWTs.
	if not key.startswith("sb_secret_"):
		headers["Authorization"] = f"Bearer {key}"
	return headers


def _object_path(bucket: str, object_key: str) -> str:
	bucket_part = quote(bucket.strip("/"), safe="")
	key_part = "/".join(quote(part, safe="") for part in object_key.replace("\\", "/").split("/") if part)
	if not bucket_part or not key_part or ".." in object_key.replace("\\", "/").split("/"):
		raise ValueError("Bucket and object key must be non-empty safe relative paths.")
	return f"{bucket_part}/{key_part}"


def _connection(url: str) -> tuple[http.client.HTTPConnection, str]:
	parsed = urlparse(url)
	if parsed.scheme not in {"http", "https"} or not parsed.hostname:
		raise ValueError("SUPABASE_URL must be a valid http(s) project URL.")
	connection_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
	port = parsed.port
	connection = connection_cls(parsed.hostname, port=port, timeout=180)
	base_path = parsed.path.rstrip("/")
	return connection, base_path


def upload_file(source: Path, bucket: str, object_key: str, content_type: str | None = None) -> dict[str, object]:
	source = source.expanduser().resolve()
	if not source.is_file():
		raise FileNotFoundError(source)
	url = require_env("SUPABASE_URL").rstrip("/")
	key = server_key()
	object_path = _object_path(bucket, object_key)
	connection, base_path = _connection(url)
	endpoint = f"{base_path}/storage/v1/object/{object_path}"
	content_type = content_type or mimetypes.guess_type(source.name)[0] or "application/octet-stream"
	size = source.stat().st_size
	headers = auth_headers(key)
	headers.update(
		{
			"Content-Type": content_type,
			"Content-Length": str(size),
			"x-upsert": "true",
			"User-Agent": "ConstruControl-Server/1.0",
		}
	)
	connection.putrequest("POST", endpoint)
	for name, value in headers.items():
		connection.putheader(name, value)
	connection.endheaders()
	digest = hashlib.sha256()
	with source.open("rb") as handle:
		while chunk := handle.read(CHUNK_SIZE):
			connection.send(chunk)
			digest.update(chunk)
	response = connection.getresponse()
	body = response.read(4096)
	connection.close()
	if response.status not in {200, 201}:
		raise RuntimeError(f"Supabase upload failed with HTTP {response.status}: {body.decode('utf-8', 'replace')}")
	return {
		"operation": "upload",
		"bucket": bucket,
		"object_key": object_key,
		"bytes": size,
		"sha256": digest.hexdigest(),
		"http_status": response.status,
	}


def download_file(bucket: str, object_key: str, destination: Path) -> dict[str, object]:
	url = require_env("SUPABASE_URL").rstrip("/")
	key = server_key()
	object_path = _object_path(bucket, object_key)
	request = Request(
		f"{url}/storage/v1/object/authenticated/{object_path}",
		headers={**auth_headers(key), "User-Agent": "ConstruControl-Server/1.0"},
	)
	destination = destination.expanduser().resolve()
	destination.parent.mkdir(parents=True, exist_ok=True)
	digest = hashlib.sha256()
	total = 0
	try:
		with urlopen(request, timeout=180) as response, destination.open("wb") as handle:  # nosec B310
			while chunk := response.read(CHUNK_SIZE):
				handle.write(chunk)
				digest.update(chunk)
				total += len(chunk)
	except HTTPError as exc:
		destination.unlink(missing_ok=True)
		raise RuntimeError(f"Supabase download failed with HTTP {exc.code}") from exc
	return {
		"operation": "download",
		"bucket": bucket,
		"object_key": object_key,
		"destination": str(destination),
		"bytes": total,
		"sha256": digest.hexdigest(),
	}


def delete_object(bucket: str, object_key: str) -> dict[str, object]:
	url = require_env("SUPABASE_URL").rstrip("/")
	key = server_key()
	# Validate both components before sending a destructive request.
	_object_path(bucket, object_key)
	bucket_part = quote(bucket.strip("/"), safe="")
	payload = json.dumps({"prefixes": [object_key]}).encode("utf-8")
	request = Request(
		f"{url}/storage/v1/object/{bucket_part}",
		data=payload,
		headers={
			**auth_headers(key),
			"Content-Type": "application/json",
			"Content-Length": str(len(payload)),
			"User-Agent": "ConstruControl-Server/1.0",
		},
		method="DELETE",
	)
	try:
		with urlopen(request, timeout=60) as response:  # nosec B310
			response.read()
			status = response.status
	except HTTPError as exc:
		raise RuntimeError(f"Supabase delete failed with HTTP {exc.code}") from exc
	return {"operation": "delete", "bucket": bucket, "object_key": object_key, "http_status": status}


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Transfer private files to or from Supabase Storage.")
	subparsers = parser.add_subparsers(dest="command", required=True)

	upload = subparsers.add_parser("upload", help="Upload one local file")
	upload.add_argument("source", type=Path)
	upload.add_argument("--bucket", required=True)
	upload.add_argument("--object", required=True, dest="object_key")
	upload.add_argument("--content-type")

	download = subparsers.add_parser("download", help="Download one private object")
	download.add_argument("destination", type=Path)
	download.add_argument("--bucket", required=True)
	download.add_argument("--object", required=True, dest="object_key")

	delete = subparsers.add_parser("delete", help="Delete one private object")
	delete.add_argument("--bucket", required=True)
	delete.add_argument("--object", required=True, dest="object_key")
	return parser


def main() -> int:
	args = build_parser().parse_args()
	if args.command == "upload":
		result = upload_file(args.source, args.bucket, args.object_key, args.content_type)
	elif args.command == "download":
		result = download_file(args.bucket, args.object_key, args.destination)
	else:
		result = delete_object(args.bucket, args.object_key)
	print(json.dumps(result, ensure_ascii=False, indent=2))
	return 0


if __name__ == "__main__":
	try:
		raise SystemExit(main())
	except Exception as exc:
		print(f"Storage transfer failed: {exc}", file=sys.stderr)
		raise SystemExit(1)
