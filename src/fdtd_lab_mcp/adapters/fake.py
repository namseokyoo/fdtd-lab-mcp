from __future__ import annotations
from pathlib import Path
from typing import Any
from uuid import uuid4

from .base import ProjectHandle
from fdtd_lab_mcp.domain.authoring import validate_fsp_save_path, validate_object_name, validate_property_name, validate_properties, validate_result_name
from fdtd_lab_mcp.errors import ValidationError

class FakeLumericalAdapter:
    name = "fake"

    def __init__(self) -> None:
        self.projects: dict[str, dict[str, Any]] = {}

    def status(self) -> dict[str, Any]:
        return {"ok": True, "installation_detected": False, "api": "fake", "products": ["FDTD"], "notes": ["Fake adapter for tests/CI; no Lumerical license required."]}

    def open_project(self, path: str, readonly: bool = True) -> ProjectHandle:
        p=Path(path).expanduser()
        if not p.exists():
            raise ValidationError(f".fsp file does not exist: {path}")
        if p.suffix.lower() != ".fsp":
            raise ValidationError(f"expected .fsp file, got: {path}")
        sid=f"fake-session-{uuid4().hex[:8]}"; pid=f"fake-project-{uuid4().hex[:8]}"
        self.projects[pid]={"path": str(p), "readonly": readonly, "session_id": sid, "objects": self._fixture()}
        return ProjectHandle(sid, pid, str(p), readonly)

    def new_project(self) -> ProjectHandle:
        sid=f"fake-session-{uuid4().hex[:8]}"; pid=f"fake-project-{uuid4().hex[:8]}"
        self.projects[pid]={"path": "<unsaved>", "readonly": False, "session_id": sid, "objects": {}}
        return ProjectHandle(sid, pid, "<unsaved>", readonly=False)

    def save_project_as(self, project_id: str, path: str, overwrite: bool = False) -> dict[str, Any]:
        pr=self._project(project_id)
        self._require_writable(project_id, "save_project_as")
        safe_path=validate_fsp_save_path(path, overwrite=overwrite)
        Path(safe_path).write_bytes(b"fake generated fsp bytes")
        pr["path"] = safe_path
        return {"project_id": project_id, "path": safe_path, "saved": True, "adapter": self.name}

    def _project(self, project_id: str) -> dict[str, Any]:
        if project_id not in self.projects: raise ValidationError(f"unknown project_id: {project_id}")
        return self.projects[project_id]

    def _require_writable(self, project_id: str, operation: str) -> None:
        if self._project(project_id).get("readonly", True):
            raise ValidationError(f"operation {operation} requires a writable project handle; reopen with readonly=False or create a new project")

    def _fixture(self) -> dict[str, dict[str, Any]]:
        return {
            "FDTD": {"type": "simulation_region", "properties": {"mesh accuracy": 2, "x span": 1e-6, "y span": 1e-6, "z span": 5e-7}},
            "source": {"type": "source", "properties": {"wavelength start": 4e-7, "wavelength stop": 7e-7}},
            "HTL": {"type": "structure", "properties": {"z span": 4e-8, "material": "HTL_mat"}},
            "EML": {"type": "structure", "properties": {"z span": 3e-8, "material": "EML_mat"}},
            "ETL": {"type": "structure", "properties": {"z span": 3e-8, "material": "ETL_mat"}},
            "T_monitor": {"type": "monitor", "properties": {"monitor type": "2D Z-normal"}},
            "R_monitor": {"type": "monitor", "properties": {"monitor type": "2D Z-normal"}},
        }

    def list_objects(self, project_id: str) -> list[dict[str, Any]]:
        pr=self._project(project_id)
        return [{"name": n, "type": v["type"]} for n,v in pr["objects"].items()]

    def list_properties(self, project_id: str, object_name: str) -> list[str]:
        obj=self._object(project_id, object_name)
        return list(obj["properties"].keys())

    def _object(self, project_id: str, object_name: str) -> dict[str, Any]:
        safe_name=validate_object_name(object_name)
        objs=self._project(project_id)["objects"]
        if safe_name not in objs:
            raise ValidationError(f"object '{safe_name}' not found. Available: {', '.join(objs)}")
        return objs[safe_name]

    def _add_object(self, project_id: str, name: str, object_type: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require_writable(project_id, f"add_{object_type}")
        safe_name=validate_object_name(name)
        props=validate_properties(properties)
        objs=self._project(project_id)["objects"]
        if safe_name in objs:
            raise ValidationError(f"object '{safe_name}' already exists")
        objs[safe_name]={"type": object_type, "properties": props}
        return {"project_id": project_id, "object_name": safe_name, "object_type": object_type, "properties": props, "adapter": self.name}

    def add_fdtd_region(self, project_id: str, name: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._add_object(project_id, name, "simulation_region", properties)

    def add_rectangle(self, project_id: str, name: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._add_object(project_id, name, "structure", properties)

    def add_dipole_source(self, project_id: str, name: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._add_object(project_id, name, "source", properties)

    def add_power_monitor(self, project_id: str, name: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._add_object(project_id, name, "monitor", properties)

    def delete_object(self, project_id: str, object_name: str) -> dict[str, Any]:
        self._require_writable(project_id, "delete_object")
        safe_name=validate_object_name(object_name)
        objs=self._project(project_id)["objects"]
        if safe_name not in objs:
            raise ValidationError(f"object '{safe_name}' not found. Available: {', '.join(objs)}")
        del objs[safe_name]
        return {"project_id": project_id, "object_name": safe_name, "deleted": True, "adapter": self.name}

    def get_property(self, project_id: str, object_name: str, property_name: str) -> dict[str, Any]:
        safe_property = validate_property_name(property_name)
        obj=self._object(project_id, object_name); props=obj["properties"]
        if safe_property not in props:
            raise ValidationError(f"property '{safe_property}' not found on '{object_name}'. Available: {', '.join(props)}")
        return {"object_name": object_name, "property_name": safe_property, "value": props[safe_property], "unit_guess": "m" if "span" in safe_property or "wavelength" in safe_property else None}

    def set_property(self, project_id: str, object_name: str, property_name: str, value: Any) -> dict[str, Any]:
        self._require_writable(project_id, "set_property")
        safe_property = validate_property_name(property_name)
        before=self.get_property(project_id, object_name, safe_property)["value"]
        self._object(project_id, object_name)["properties"][safe_property]=value
        return {"object_name": object_name, "property_name": safe_property, "before": before, "after": value}

    def run(self, project_id: str, timeout_sec: int = 3600) -> dict[str, Any]:
        self._require_writable(project_id, "run")
        return {"status": "completed", "elapsed_sec": 0.01, "warnings": [], "adapter": self.name}

    def get_monitor_result(self, project_id: str, monitor_name: str, result_name: str) -> dict[str, Any]:
        safe_monitor = validate_object_name(monitor_name)
        safe_result = validate_result_name(result_name)
        self._object(project_id, safe_monitor)
        if safe_result.lower() in {"e", "field", "field_profile"}:
            values = {
                "Ex": [[0.0, 0.2, 0.4, 0.2], [0.1, 0.5, 0.9, 0.4], [0.0, 0.3, 0.6, 0.2]],
                "Ey": [[0.1, 0.1, 0.2, 0.1], [0.2, 0.4, 0.6, 0.3], [0.1, 0.2, 0.3, 0.1]],
            }
            return {
                "monitor_name": safe_monitor,
                "result_name": safe_result,
                "axes": {"x_m": {"values": [-1.5e-7, -5e-8, 5e-8, 1.5e-7], "unit": "m"}, "y_m": {"values": [-1e-7, 0.0, 1e-7], "unit": "m"}},
                "values": values,
                "shape": [3, 4],
                "metadata": {"project_id": project_id, "source": "fake", "normalized": True, "field_components": list(values)},
                "warnings": ["Fake field data is a deterministic 2D fixture for exporter tests, not a physical simulation result."],
            }
        wavelengths=[4.5e-7, 5.0e-7, 5.5e-7, 6.0e-7]
        values=[0.41, 0.55, 0.49, 0.43] if safe_monitor.startswith("T") else [0.12,0.10,0.13,0.15]
        return {"monitor_name": safe_monitor, "result_name": safe_result, "axes": {"wavelength_m": {"values": wavelengths, "unit": "m"}}, "values": values, "shape": [len(values)], "metadata": {"project_id": project_id, "source": "fake", "normalized": True}, "warnings": []}

    def close_project(self, project_id: str) -> dict[str, Any]:
        pr = self._project(project_id)
        session_id = pr["session_id"]
        del self.projects[project_id]
        return {"project_id": project_id, "session_id": session_id, "closed": True, "adapter": self.name}

    def close(self, session_id: str) -> dict[str, Any]:
        closed_projects = []
        for pid in [pid for pid,p in self.projects.items() if p["session_id"]==session_id]:
            closed_projects.append(self.close_project(pid)["project_id"])
        return {"closed": True, "session_id": session_id, "project_ids": closed_projects, "adapter": self.name}
