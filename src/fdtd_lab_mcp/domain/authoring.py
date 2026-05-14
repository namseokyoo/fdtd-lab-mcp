from __future__ import annotations

from pathlib import Path
from typing import Any

from fdtd_lab_mcp.errors import ValidationError

_UNSAFE_NAME_CHARS = {'"', "'", ";", "\n", "\r"}


def validate_object_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("object name must be a non-empty string")
    stripped = name.strip()
    if any(ch in stripped for ch in _UNSAFE_NAME_CHARS):
        raise ValidationError(f"unsafe object name: {name!r}")
    return stripped


def validate_properties(properties: dict[str, Any] | None) -> dict[str, Any]:
    if properties is None:
        return {}
    if not isinstance(properties, dict):
        raise ValidationError("properties must be a dictionary")
    for key in properties:
        if not isinstance(key, str) or not key.strip():
            raise ValidationError("property names must be non-empty strings")
        if any(ch in key for ch in {'"', "\n", "\r"}):
            raise ValidationError(f"unsafe property name: {key!r}")
    return dict(properties)


def validate_fsp_save_path(path: str, overwrite: bool = False) -> str:
    p = Path(path).expanduser()
    if p.suffix.lower() != ".fsp":
        raise ValidationError(f"expected .fsp save path, got: {path}")
    if p.exists() and not overwrite:
        raise ValidationError(f"save path already exists: {path}")
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


def lsf_quote(value: str) -> str:
    # Lumerical script strings are double-quoted. Backslash/quote escaping is enough
    # after callers validate names and property keys.
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
