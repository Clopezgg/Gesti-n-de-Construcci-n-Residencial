#!/usr/bin/env python3
"""Verify a live NEXORA deployment without exposing credentials."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urljoin


def read_json(url: str, timeout: int, insecure: bool) -> dict:
    context = ssl._create_unverified_context() if insecure else None
    request = urllib.request.Request(url, headers={"User-Agent": "NEXORA-Deployment-Verification/1.0"})
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        if response.status >= 400:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return json.loads(response.read().decode("utf-8"))


def read_text(url: str, timeout: int, insecure: bool) -> str:
    context = ssl._create_unverified_context() if insecure else None
    request = urllib.request.Request(url, headers={"User-Agent": "NEXORA-Deployment-Verification/1.0"})
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        if response.status >= 400:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return response.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify live NEXORA health, identity, manifest and dashboard route")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expected-sha")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--insecure", action="store_true")
    args = parser.parse_args()

    base = args.base_url.rstrip("/") + "/"
    errors: list[str] = []

    try:
        ping = read_json(urljoin(base, "api/method/ping"), args.timeout, args.insecure)
        if ping.get("message") != "pong":
            errors.append(f"Unexpected ping response: {ping!r}")
    except Exception as exc:
        errors.append(f"Health check failed: {exc}")

    build = {}
    try:
        payload = read_json(
            urljoin(base, "api/method/nexora.build_info.get_build_info"),
            args.timeout,
            args.insecure,
        )
        build = payload.get("message") or {}
        if build.get("product") != "NEXORA":
            errors.append(f"Unexpected product identity: {build!r}")
        if args.expected_sha:
            actual = str(build.get("build_sha") or "")
            if actual != args.expected_sha and not args.expected_sha.startswith(actual) and not actual.startswith(args.expected_sha):
                errors.append(f"Deployed SHA mismatch: expected {args.expected_sha}, got {actual or 'missing'}")
    except Exception as exc:
        errors.append(f"Build identity check failed: {exc}")

    try:
        manifest = read_json(urljoin(base, "assets/nexora/manifest.json"), args.timeout, args.insecure)
        if manifest.get("start_url") != "/app/nexora-dashboard":
            errors.append("Manifest does not start at /app/nexora-dashboard")
        if manifest.get("display") != "standalone":
            errors.append("Manifest display is not standalone")
    except Exception as exc:
        errors.append(f"PWA manifest check failed: {exc}")

    try:
        page = read_text(urljoin(base, "app/nexora-dashboard"), args.timeout, args.insecure)
        lowered = page.casefold()
        if "page not found" in lowered or "404 not found" in lowered:
            errors.append("Dashboard route rendered a not-found page")
    except urllib.error.HTTPError as exc:
        # A login redirect/page is acceptable; 4xx/5xx is not.
        errors.append(f"Dashboard route failed: HTTP {exc.code}")
    except Exception as exc:
        errors.append(f"Dashboard route check failed: {exc}")

    print(json.dumps({"base_url": base, "build": build, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
