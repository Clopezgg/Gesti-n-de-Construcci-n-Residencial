from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

_MARKER = re.compile(r"\b(?:TODO|FIXME|IMPLEMENTAR DESPU[EÉ]S|PENDIENTE DE IMPLEMENTAR)\b", re.IGNORECASE)


def unresolved_implementation_marker(path: Path) -> bool:
    """Detect real implementation markers without treating identifiers such as Frappe ToDo as pending work."""
    source = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() != ".py":
        return bool(_MARKER.search(source))

    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        return any(token.type == tokenize.COMMENT and _MARKER.search(token.string) for token in tokens)
    except (IndentationError, SyntaxError, tokenize.TokenError):
        return bool(_MARKER.search(source))


__all__ = ["unresolved_implementation_marker"]
