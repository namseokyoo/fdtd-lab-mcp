from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from fdtd_lab_mcp.adapters import make_adapter
from fdtd_lab_mcp.adapters.fake import FakeLumericalAdapter
from fdtd_lab_mcp.adapters.ansys_core import AnsysCoreAdapter
from fdtd_lab_mcp.adapters.lumapi import LumapiAdapter
from fdtd_lab_mcp.domain.oled import classify_role
from fdtd_lab_mcp.reporting.csv_export import export_monitor_csv
from fdtd_lab_mcp.reporting.summary import generate_summary
from fdtd_lab_mcp.safety.run_manager import RunManager, sha256_file

DEFAULT_ADAPTER_ENV = "FDTD_LAB_ADAPTER"
_ADAPTER = make_adapter(os.environ.get(DEFAULT_ADAPTER_ENV, "fake"))
_RUNS: dict[str, dict[str, Any]] = {}


def active_adapter() -> dict[str, Any]:
    env_default = os.environ.get(DEFAULT_ADAPTER_ENV, "fake")
    return {"adapter": _ADAPTER.name, "env_default": env_default, "default_env": env_default}


def reset_state(adapter: str | None = None) -> dict[str, Any]:
    """Reset in-memory MCP state and select the active adapter.

    Adapter defaults to FDTD_LAB_ADAPTER, then fake. Real adapters still require
    FDTD_LAB_ENABLE_REAL_LUMERICAL=1 before opening/running projects.
    """
    global _ADAPTER, _RUNS
    selected = adapter or os.environ.get(DEFAULT_ADAPTER_ENV, "fake")
    _ADAPTER = make_adapter(selected)
    _RUNS = {}
    return active_adapter()


def lumerical_status(adapter: str = "fake") -> dict[str, Any]:
    if adapter == "all":
        return {"fake": FakeLumericalAdapter().status(), "ansys_core": AnsysCoreAdapter().status(), "lumapi": LumapiAdapter().status()}
    return make_adapter(adapter).status()


def open_fsp(path: str, readonly: bool = True) -> dict[str, Any]:
    h = _ADAPTER.open_project(path, readonly=readonly)
    return {"session_id": h.session_id, "project_id": h.project_id, "path": h.path, "readonly": h.readonly, "adapter": _ADAPTER.name}


def list_objects(project_id: str) -> dict[str, Any]:
    return {"project_id": project_id, "objects": _ADAPTER.list_objects(project_id)}


def list_properties(project_id: str, object_name: str) -> dict[str, Any]:
    return {"project_id": project_id, "object_name": object_name, "properties": _ADAPTER.list_properties(project_id, object_name)}


def get_object_property(project_id: str, object_name: str, property_name: str) -> dict[str, Any]:
    return _ADAPTER.get_property(project_id, object_name, property_name)


def set_object_property(project_id: str, object_name: str, property_name: str, value: Any, run_id: str | None = None) -> dict[str, Any]:
    result = _ADAPTER.set_property(project_id, object_name, property_name, value)
    if run_id and run_id in _RUNS:
        RunManager().append_change(_RUNS[run_id]["provenance_path"], result)
    return result


def describe_project(project_id: str) -> dict[str, Any]:
    objects = _ADAPTER.list_objects(project_id)
    sources=[o["name"] for o in objects if classify_role(o["name"], o.get("type","")) == "source"]
    monitors=[o["name"] for o in objects if classify_role(o["name"], o.get("type","")) == "monitor"]
    regions=[o["name"] for o in objects if classify_role(o["name"], o.get("type","")) == "simulation_region"]
    structures=[o["name"] for o in objects if o.get("type") == "structure"]
    candidates=[]
    for name in structures + sources:
        try:
            props=_ADAPTER.list_properties(project_id, name)
        except Exception:
            props=[]
        for prop in props:
            if "span" in prop or "wavelength" in prop:
                candidates.append({"object": name, "property": prop, "reason": "layer thickness" if "span" in prop else "spectral range"})
    return {"project_id": project_id, "project_type_guess": "OLED stack or planar optical stack", "simulation_regions": regions, "sources": sources, "monitors": monitors, "structures": structures, "sweep_candidates": candidates, "warnings": []}


def inspect_fsp(path: str, readonly: bool = True) -> dict[str, Any]:
    opened=open_fsp(path, readonly=readonly)
    return {**opened, "objects": list_objects(opened["project_id"])["objects"], "description": describe_project(opened["project_id"])}


def create_run_dir(base_fsp: str, run_name: str) -> dict[str, Any]:
    info=RunManager().create_run_dir(base_fsp, run_name)
    _RUNS[info.run_id] = info.__dict__
    return info.__dict__


def run_simulation(project_id: str, timeout_sec: int = 3600, run_id: str | None = None) -> dict[str, Any]:
    result=_ADAPTER.run(project_id, timeout_sec=timeout_sec)
    if run_id and run_id in _RUNS:
        RunManager().update_status(_RUNS[run_id]["provenance_path"], result["status"], _ADAPTER.name)
    return result


def get_monitor_result(project_id: str, monitor_name: str, result_name: str) -> dict[str, Any]:
    return _ADAPTER.get_monitor_result(project_id, monitor_name, result_name)


def propose_experiment_plan(base_fsp: str, run_name: str, object_name: str, property_name: str, values: list[Any], monitor_name: str, result_name: str) -> dict[str, Any]:
    return {"dry_run": True, "plan_id": f"plan_{Path(base_fsp).stem}_{run_name}", "base_fsp": base_fsp, "run_name": run_name, "approved_changes": [{"object_name": object_name, "property_name": property_name, "allowed_values": values}], "monitor_name": monitor_name, "result_name": result_name, "will_create_run_dir": True}


def validate_experiment_plan(plan: dict[str, Any]) -> dict[str, Any]:
    missing=[k for k in ["base_fsp","run_name","approved_changes","monitor_name","result_name"] if k not in plan]
    if missing: return {"ok": False, "errors": [f"missing {k}" for k in missing]}
    if not Path(plan["base_fsp"]).exists(): return {"ok": False, "errors": [f"base_fsp does not exist: {plan['base_fsp']}"]}
    return {"ok": True, "errors": [], "warnings": ["Real object/property/monitor validation requires opening project; fake validation occurs during execution."]}


def export_csv(rows: list[dict[str, Any]], path: str) -> dict[str, Any]:
    return export_monitor_csv(rows, path)


def run_parameter_sweep(base_fsp: str, run_name: str, object_name: str, property_name: str, values: list[Any], monitor_name: str, result_name: str, approved_changes: list[dict[str, Any]] | None = None, dry_run: bool = False) -> dict[str, Any]:
    if dry_run:
        return propose_experiment_plan(base_fsp, run_name, object_name, property_name, values, monitor_name, result_name)
    allowed = approved_changes or [{"object_name": object_name, "property_name": property_name, "allowed_values": values}]
    if not any(c.get("object_name")==object_name and c.get("property_name")==property_name and set(values).issubset(set(c.get("allowed_values", []))) for c in allowed):
        raise ValueError("sweep values are not covered by approved_changes")
    before=sha256_file(base_fsp)
    run=create_run_dir(base_fsp, run_name)
    opened=open_fsp(run["working_fsp"], readonly=False)
    rows=[]
    for i,value in enumerate(values, start=1):
        change=set_object_property(opened["project_id"], object_name, property_name, value, run_id=run["run_id"])
        status=run_simulation(opened["project_id"], run_id=run["run_id"])["status"]
        result=get_monitor_result(opened["project_id"], monitor_name, result_name)
        wavelengths=result["axes"]["wavelength_m"]["values"]
        for wl,rv in zip(wavelengths, result["values"]):
            rows.append({"run_id": run["run_id"], "case_id": f"case_{i:04d}", "object": object_name, "property": property_name, "value": value, "monitor": monitor_name, "result": result_name, "wavelength_m": wl, "result_value": rv, "status": status})
    csv_path=str(Path(run["run_dir"])/"results"/"results.csv")
    summary_path=str(Path(run["run_dir"])/"summary.md")
    csv_info=export_monitor_csv(rows, csv_path)
    summary=generate_summary(summary_path, run_id=run["run_id"], parameter={"object": object_name, "property": property_name, "values": values}, result_rows=rows)
    after=sha256_file(base_fsp)
    if before != after:
        raise RuntimeError("safety violation: base .fsp checksum changed")
    return {"run_id": run["run_id"], "run_dir": run["run_dir"], "working_fsp": run["working_fsp"], "results_csv": csv_info["path"], "summary_md": summary["path"], "provenance_json": run["provenance_path"], "rows": len(rows), "base_checksum_unchanged": True}
