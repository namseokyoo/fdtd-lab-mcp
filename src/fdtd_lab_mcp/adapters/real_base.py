from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fdtd_lab_mcp.adapters.base import ProjectHandle
from fdtd_lab_mcp.domain.authoring import lsf_quote, validate_fsp_save_path, validate_object_name, validate_properties
from fdtd_lab_mcp.errors import AdapterUnavailable, ValidationError

REAL_ENABLE_ENV = "FDTD_LAB_ENABLE_REAL_LUMERICAL"
logger = logging.getLogger(__name__)


def real_enabled() -> bool:
    return os.environ.get(REAL_ENABLE_ENV, "").lower() in {"1", "true", "yes", "on"}


def _json_safe(value: Any) -> Any:
    """Convert Lumerical/numpy-ish values into MCP JSON-serializable data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "tolist"):
        return _json_safe(value.tolist())
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))
    return str(value)


class ScriptSessionAdapter:
    """Shared real-adapter skeleton for Lumerical APIs exposing eval/getv/putv/close.

    Phase 4 deliberately keeps real execution behind FDTD_LAB_ENABLE_REAL_LUMERICAL=1.
    This prevents accidental license consumption or mutation from normal tests/MCP use.
    """

    name = "script_session"
    product = "FDTD"

    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}

    def _require_enabled(self) -> None:
        if not real_enabled():
            raise AdapterUnavailable(
                f"Real Lumerical operations are disabled. Set {REAL_ENABLE_ENV}=1 "
                "inside the company local-network Lumerical environment to enable gated integration."
            )

    def _validate_fsp(self, path: str) -> str:
        p = Path(path).expanduser()
        if not p.exists():
            raise ValidationError(f".fsp file does not exist: {path}")
        if p.suffix.lower() != ".fsp":
            raise ValidationError(f"expected .fsp file, got: {path}")
        return str(p)

    def _store_session(self, session: Any, path: str, readonly: bool) -> ProjectHandle:
        session_id = f"{self.name}-session-{uuid4().hex[:8]}"
        project_id = f"{self.name}-project-{uuid4().hex[:8]}"
        self.projects[project_id] = {
            "session_id": session_id,
            "session": session,
            "path": path,
            "readonly": readonly,
        }
        logger.info("Stored Lumerical session adapter=%s project_id=%s readonly=%s path=%s", self.name, project_id, readonly, path)
        return ProjectHandle(session_id=session_id, project_id=project_id, path=path, readonly=readonly)

    def _create_blank_session(self) -> Any:
        raise NotImplementedError("real adapters must implement _create_blank_session")

    def new_project(self) -> ProjectHandle:
        logger.info("Creating blank Lumerical project adapter=%s", self.name)
        self._require_enabled()
        try:
            session = self._create_blank_session()
        except Exception as exc:  # pragma: no cover - requires real Lumerical
            raise AdapterUnavailable(f"Failed to create blank FDTD project through {self.name}: {exc}") from exc
        return self._store_session(session, "<unsaved>", readonly=False)

    def save_project_as(self, project_id: str, path: str, overwrite: bool = False) -> dict[str, Any]:
        safe_path = validate_fsp_save_path(path, overwrite=overwrite)
        self._eval(project_id, f"save({lsf_quote(safe_path)});")
        self._project(project_id)["path"] = safe_path
        return {"project_id": project_id, "path": safe_path, "saved": True, "adapter": self.name}

    def _set_properties(self, project_id: str, properties: dict[str, Any]) -> None:
        for prop, value in validate_properties(properties).items():
            self._putv(project_id, "fdtd_lab_new_value", value)
            self._eval(project_id, f"set({lsf_quote(prop)}, fdtd_lab_new_value);")

    def _add_object(self, project_id: str, name: str, command: str, object_type: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        safe_name = validate_object_name(name)
        props = validate_properties(properties)
        self._eval(project_id, f"{command}; set(\"name\", {lsf_quote(safe_name)});")
        self._set_properties(project_id, props)
        return {"project_id": project_id, "object_name": safe_name, "object_type": object_type, "properties": props, "adapter": self.name}

    def add_fdtd_region(self, project_id: str, name: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._add_object(project_id, name, "addfdtd", "simulation_region", properties)

    def add_rectangle(self, project_id: str, name: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._add_object(project_id, name, "addrect", "structure", properties)

    def add_dipole_source(self, project_id: str, name: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._add_object(project_id, name, "adddipole", "source", properties)

    def add_power_monitor(self, project_id: str, name: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._add_object(project_id, name, "addpower", "monitor", properties)

    def delete_object(self, project_id: str, object_name: str) -> dict[str, Any]:
        safe_name = validate_object_name(object_name)
        self._eval(project_id, f"select({lsf_quote(safe_name)}); delete;")
        return {"project_id": project_id, "object_name": safe_name, "deleted": True, "adapter": self.name}

    def _project(self, project_id: str) -> dict[str, Any]:
        try:
            return self.projects[project_id]
        except KeyError as exc:
            raise ValidationError(f"unknown project_id: {project_id}") from exc

    def _session(self, project_id: str) -> Any:
        return self._project(project_id)["session"]

    def _eval(self, project_id: str, script: str) -> None:
        try:
            self._session(project_id).eval(script)
        except Exception as exc:  # pragma: no cover - requires real Lumerical
            raise AdapterUnavailable(f"Lumerical script execution failed: {exc}") from exc

    def _getv(self, project_id: str, name: str) -> Any:
        try:
            return self._session(project_id).getv(name)
        except Exception as exc:  # pragma: no cover - requires real Lumerical
            raise AdapterUnavailable(f"Lumerical getv('{name}') failed: {exc}") from exc

    def _putv(self, project_id: str, name: str, value: Any) -> None:
        try:
            self._session(project_id).putv(name, value)
        except Exception as exc:  # pragma: no cover - requires real Lumerical
            raise AdapterUnavailable(f"Lumerical putv('{name}') failed: {exc}") from exc

    def list_objects(self, project_id: str) -> list[dict[str, Any]]:
        """List selected project objects without relying on Lumerical for-loop/array syntax.

        Some company-local Lumerical scripting contexts did not support the earlier
        `for (...) { ... }` + cell-array script. Keep the iteration in Python and use
        only small scalar Lumerical statements per object.
        """
        logger.info("Listing objects adapter=%s project_id=%s", self.name, project_id)
        self._eval(project_id, "selectall; fdtd_lab_n = getnumber;")
        raw_count = self._getv(project_id, "fdtd_lab_n")
        try:
            count = int(float(_json_safe(raw_count)))
        except (TypeError, ValueError) as exc:
            raise AdapterUnavailable(f"Could not read selected object count from Lumerical: {raw_count!r}") from exc

        objects: list[dict[str, Any]] = []
        for index in range(1, count + 1):
            self._eval(
                project_id,
                f'fdtd_lab_object_name = get("name", {index}); fdtd_lab_object_type = get("type", {index});',
            )
            name = _json_safe(self._getv(project_id, "fdtd_lab_object_name"))
            obj_type = _json_safe(self._getv(project_id, "fdtd_lab_object_type"))
            if str(name) not in {"", "None"}:
                objects.append({"name": str(name), "type": str(obj_type)})
        logger.info("Listed %s objects adapter=%s project_id=%s", len(objects), self.name, project_id)
        return objects

    def _pair_objects(self, names: Any, types: Any) -> list[dict[str, Any]]:
        names = _json_safe(names)
        types = _json_safe(types)
        if not isinstance(names, list):
            names = [names]
        if not isinstance(types, list):
            types = [types] * len(names)
        return [{"name": str(n), "type": str(t)} for n, t in zip(names, types) if str(n) not in {"", "None"}]

    def list_properties(self, project_id: str, object_name: str) -> list[str]:
        # Lumerical has version-dependent property discovery. Return a pragmatic common set
        # after selecting the object; failures clearly indicate naming mismatch.
        self._eval(project_id, f'select("{object_name}");')
        return ["x", "y", "z", "x span", "y span", "z span", "material", "wavelength start", "wavelength stop"]

    def get_property(self, project_id: str, object_name: str, property_name: str) -> dict[str, Any]:
        var = "fdtd_lab_property_value"
        self._eval(project_id, f'select("{object_name}"); {var}=get("{property_name}");')
        return {"object_name": object_name, "property_name": property_name, "value": _json_safe(self._getv(project_id, var)), "unit_guess": "m" if "span" in property_name or "wavelength" in property_name else None}

    def set_property(self, project_id: str, object_name: str, property_name: str, value: Any) -> dict[str, Any]:
        before = self.get_property(project_id, object_name, property_name)["value"]
        self._putv(project_id, "fdtd_lab_new_value", value)
        self._eval(project_id, f'select("{object_name}"); set("{property_name}", fdtd_lab_new_value);')
        after = self.get_property(project_id, object_name, property_name)["value"]
        return {"object_name": object_name, "property_name": property_name, "before": before, "after": after}

    def run(self, project_id: str, timeout_sec: int = 3600) -> dict[str, Any]:
        self._eval(project_id, "run;")
        return {"status": "completed", "elapsed_sec": None, "warnings": [], "adapter": self.name}

    def get_monitor_result(self, project_id: str, monitor_name: str, result_name: str) -> dict[str, Any]:
        logger.info("Getting monitor result adapter=%s project_id=%s monitor=%s result=%s", self.name, project_id, monitor_name, result_name)
        self._eval(project_id, f'fdtd_lab_result = getresult("{monitor_name}", "{result_name}");')
        raw = _json_safe(self._getv(project_id, "fdtd_lab_result"))
        return {"monitor_name": monitor_name, "result_name": result_name, "raw": raw, "axes": {}, "values": [], "shape": [], "metadata": {"project_id": project_id, "source": "getresult", "adapter": self.name}, "warnings": ["Raw real-adapter result returned; schema normalization requires first company-local sample .fsp."]}

    def close(self, session_id: str) -> dict[str, Any]:
        for project_id, record in list(self.projects.items()):
            if record["session_id"] != session_id:
                continue
            try:
                logger.info("Closing Lumerical session adapter=%s session_id=%s project_id=%s", self.name, session_id, project_id)
                record["session"].close()
            finally:
                del self.projects[project_id]
        return {"closed": True, "session_id": session_id}
