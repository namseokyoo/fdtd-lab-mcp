from pathlib import Path
from typing import Any

from fdtd_lab_mcp.errors import ValidationError

_UNSAFE_NAME_CHARS = {'"', "'", ";", "\n", "\r"}
_UNSAFE_PROPERTY_CHARS = {'"', "'", ";", "\n", "\r"}


def _validate_lsf_label(value: str, label: str, unsafe_chars: set[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    stripped = value.strip()
    if any(ch in stripped for ch in unsafe_chars):
        raise ValidationError(f"unsafe {label}: {value!r}")
    return stripped


def validate_object_name(name: str) -> str:
    return _validate_lsf_label(name, "object name", _UNSAFE_NAME_CHARS)


def validate_property_name(name: str) -> str:
    return _validate_lsf_label(name, "property name", _UNSAFE_PROPERTY_CHARS)


def validate_result_name(name: str) -> str:
    return _validate_lsf_label(name, "result name", _UNSAFE_NAME_CHARS)


def validate_properties(properties: dict[str, Any] | None) -> dict[str, Any]:
    if properties is None:
        return {}
    if not isinstance(properties, dict):
        raise ValidationError("properties must be a dictionary")
    validated: dict[str, Any] = {}
    for key, value in properties.items():
        validated[validate_property_name(key)] = value
    return validated


def validate_fsp_save_path(path: str, overwrite: bool = False) -> str:
    p = Path(path).expanduser()
    if p.suffix.lower() != ".fsp":
        raise ValidationError(f"expected .fsp save path, got: {path}")
    if p.exists() and not overwrite:
        raise ValidationError(f"save path already exists: {path}")
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


def lsf_quote(value: str) -> str:
    # Lumerical script strings are double-quoted. Escape anyway so validated labels
    # and filesystem paths can be embedded without creating executable syntax.
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
