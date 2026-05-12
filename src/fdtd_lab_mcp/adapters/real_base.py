from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fdtd_lab_mcp.adapters.base import ProjectHandle
from fdtd_lab_mcp.errors import AdapterUnavailable, ValidationError

REAL_ENABLE_ENV = "FDTD_LAB_ENABLE_REAL_LUMERICAL"


def real_enabled() -> bool:
    return os.environ.get(REAL_ENABLE_ENV, "").lower() in {"1", "true", "yes", "on"}


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
        return ProjectHandle(session_id=session_id, project_id=project_id, path=path, readonly=readonly)

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
        # Conservative first-pass script. Real sites may need naming conventions or a custom .lsf inspector.
        script = """
fdtd_lab_object_names = {};
fdtd_lab_object_types = {};
selectall;
fdtd_lab_n = getnumber;
for (fdtd_lab_i=1:fdtd_lab_n) {
  fdtd_lab_name = get(\"name\", fdtd_lab_i);
  fdtd_lab_type = get(\"type\", fdtd_lab_i);
  fdtd_lab_object_names{fdtd_lab_i} = fdtd_lab_name;
  fdtd_lab_object_types{fdtd_lab_i} = fdtd_lab_type;
}
"""
        self._eval(project_id, script)
        names = self._getv(project_id, "fdtd_lab_object_names")
        types = self._getv(project_id, "fdtd_lab_object_types")
        return self._pair_objects(names, types)

    def _pair_objects(self, names: Any, types: Any) -> list[dict[str, Any]]:
        if not isinstance(names, (list, tuple)):
            names = list(names) if hasattr(names, "__iter__") and not isinstance(names, str) else [names]
        if not isinstance(types, (list, tuple)):
            types = list(types) if hasattr(types, "__iter__") and not isinstance(types, str) else [types] * len(names)
        return [{"name": str(n), "type": str(t)} for n, t in zip(names, types) if str(n) not in {"", "None"}]

    def list_properties(self, project_id: str, object_name: str) -> list[str]:
        # Lumerical has version-dependent property discovery. Return a pragmatic common set
        # after selecting the object; failures clearly indicate naming mismatch.
        self._eval(project_id, f'select("{object_name}");')
        return ["x", "y", "z", "x span", "y span", "z span", "material", "wavelength start", "wavelength stop"]

    def get_property(self, project_id: str, object_name: str, property_name: str) -> dict[str, Any]:
        var = "fdtd_lab_property_value"
        self._eval(project_id, f'select("{object_name}"); {var}=get("{property_name}");')
        return {"object_name": object_name, "property_name": property_name, "value": self._getv(project_id, var), "unit_guess": "m" if "span" in property_name or "wavelength" in property_name else None}

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
        self._eval(project_id, f'fdtd_lab_result = getresult("{monitor_name}", "{result_name}");')
        raw = self._getv(project_id, "fdtd_lab_result")
        return {"monitor_name": monitor_name, "result_name": result_name, "raw": raw, "axes": {}, "values": [], "shape": [], "metadata": {"project_id": project_id, "source": "getresult", "adapter": self.name}, "warnings": ["Raw real-adapter result returned; schema normalization requires first company-local sample .fsp."]}

    def close(self, session_id: str) -> dict[str, Any]:
        for project_id, record in list(self.projects.items()):
            if record["session_id"] != session_id:
                continue
            try:
                record["session"].close()
            finally:
                del self.projects[project_id]
        return {"closed": True, "session_id": session_id}
