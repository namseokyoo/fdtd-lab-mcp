from __future__ import annotations
import os
import warnings
from pathlib import Path
from typing import Any

from fdtd_lab_mcp import __version__
from fdtd_lab_mcp.adapters import make_adapter
from fdtd_lab_mcp.adapters.fake import FakeLumericalAdapter
from fdtd_lab_mcp.adapters.ansys_core import AnsysCoreAdapter
from fdtd_lab_mcp.adapters.lumapi import LumapiAdapter
from fdtd_lab_mcp.adapters.real_base import REAL_ENABLE_ENV, real_enabled
from fdtd_lab_mcp.domain.oled import classify_role
from fdtd_lab_mcp.reporting.csv_export import export_monitor_csv
from fdtd_lab_mcp.reporting.plots import (
    export_heatmap,
    export_xy_plot,
    normalize_field_matrix,
    normalize_monitor_result,
    normalize_sweep_rows,
    read_sweep_csv,
)
from fdtd_lab_mcp.reporting.summary import generate_summary
from fdtd_lab_mcp.safety.run_manager import RunManager, sha256_file

DEFAULT_ADAPTER_ENV = "FDTD_LAB_ADAPTER"
SERVER_NAME = "fdtd-lab-mcp"
ADAPTER_STATUS_KEYS = {
    "fake": ["api", "installation_detected", "notes", "ok", "products"],
    "ansys_core": ["api", "error", "installation_detected", "module", "notes", "ok", "package_version", "products"],
    "lumapi": ["api", "error", "installation_detected", "module", "notes", "ok", "products"],
}
_ADAPTER = make_adapter(os.environ.get(DEFAULT_ADAPTER_ENV, "fake"))
_RUNS: dict[str, dict[str, Any]] = {}


def _properties_payload(project_id: str, object_name: str, response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        props = response.get("properties", [])
        return {
            "project_id": project_id,
            "object_name": object_name,
            "properties": props,
            "verified": bool(response.get("verified", True)),
            "capability_source": response.get("capability_source", "adapter"),
            "warnings": list(response.get("warnings", [])),
        }
    return {
        "project_id": project_id,
        "object_name": object_name,
        "properties": list(response),
        "verified": True,
        "capability_source": "adapter_dynamic_or_fixture",
        "warnings": [],
    }


def _require_normalized_monitor_result(result: dict[str, Any]) -> None:
    if result.get("metadata", {}).get("normalized") is False or "wavelength_m" not in result.get("axes", {}):
        warnings = result.get("warnings") or []
        detail = f" Warnings: {'; '.join(warnings)}" if warnings else ""
        raise RuntimeError(
            "monitor result is raw/un-normalized and cannot be used for parameter sweep CSV export until real result normalization is implemented."
            + detail
        )


def active_adapter() -> dict[str, Any]:
    env_default = os.environ.get(DEFAULT_ADAPTER_ENV, "fake")
    return {"adapter": _ADAPTER.name, "env_default": env_default, "default_env": env_default}


def server_info() -> dict[str, Any]:
    """Return read-only metadata about this MCP server and adapter gates."""
    env_default = os.environ.get(DEFAULT_ADAPTER_ENV, "fake")
    return {
        "server_name": SERVER_NAME,
        "version": __version__,
        "active_adapter": _ADAPTER.name,
        "env_default": env_default,
        "default_env": env_default,
        "real_lumerical": {
            "env": REAL_ENABLE_ENV,
            "enabled": real_enabled(),
        },
        "adapter_status_keys": ADAPTER_STATUS_KEYS,
    }


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


def _auto_close_internal_project(project_id: str, primary_error: BaseException | None = None) -> None:
    """Close a project opened by a one-shot helper without hiding its primary failure."""
    try:
        close_project(project_id)
    except Exception as close_error:
        if primary_error is not None:
            note = f"Additionally failed to close internally opened project {project_id}: {close_error}"
            if hasattr(primary_error, "add_note"):
                primary_error.add_note(note)
            else:
                warnings.warn(note, RuntimeWarning, stacklevel=2)
            return
        raise RuntimeError(f"failed to close internally opened project {project_id}: {close_error}") from close_error


def open_fsp(path: str, readonly: bool = True) -> dict[str, Any]:
    h = _ADAPTER.open_project(path, readonly=readonly)
    return {"session_id": h.session_id, "project_id": h.project_id, "path": h.path, "readonly": h.readonly, "adapter": _ADAPTER.name}


def new_project() -> dict[str, Any]:
    h = _ADAPTER.new_project()
    return {"session_id": h.session_id, "project_id": h.project_id, "path": h.path, "readonly": h.readonly, "adapter": _ADAPTER.name}


def save_project_as(project_id: str, path: str, overwrite: bool = False) -> dict[str, Any]:
    return _ADAPTER.save_project_as(project_id, path, overwrite=overwrite)


def add_fdtd_region(project_id: str, name: str = "FDTD", properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return _ADAPTER.add_fdtd_region(project_id, name, properties or {})


def add_rectangle(project_id: str, name: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return _ADAPTER.add_rectangle(project_id, name, properties or {})


def add_dipole_source(project_id: str, name: str = "source", properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return _ADAPTER.add_dipole_source(project_id, name, properties or {})


def add_power_monitor(project_id: str, name: str = "T_monitor", properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return _ADAPTER.add_power_monitor(project_id, name, properties or {})


def delete_object(project_id: str, object_name: str) -> dict[str, Any]:
    return _ADAPTER.delete_object(project_id, object_name)


def list_objects(project_id: str) -> dict[str, Any]:
    return {"project_id": project_id, "objects": _ADAPTER.list_objects(project_id)}


def list_properties(project_id: str, object_name: str) -> dict[str, Any]:
    return _properties_payload(project_id, object_name, _ADAPTER.list_properties(project_id, object_name))


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
            payload=_properties_payload(project_id, name, _ADAPTER.list_properties(project_id, name))
            props=payload["properties"]
            if not payload.get("verified", True):
                for prop in props:
                    if "span" in prop or "wavelength" in prop:
                        candidates.append({"object": name, "property": prop, "reason": "unverified static candidate", "verified": False, "capability_source": payload.get("capability_source")})
                continue
        except Exception:
            props=[]
        for prop in props:
            if "span" in prop or "wavelength" in prop:
                candidates.append({"object": name, "property": prop, "reason": "layer thickness" if "span" in prop else "spectral range", "verified": True})
    warnings=[]
    if any(candidate.get("verified") is False for candidate in candidates):
        warnings.append("Some sweep candidates are static real-adapter property candidates and are not verified object-specific capabilities.")
    return {"project_id": project_id, "project_type_guess": "OLED stack or planar optical stack", "simulation_regions": regions, "sources": sources, "monitors": monitors, "structures": structures, "sweep_candidates": candidates, "warnings": warnings}


def inspect_fsp(path: str, readonly: bool = True) -> dict[str, Any]:
    opened = open_fsp(path, readonly=readonly)
    project_id = opened["project_id"]
    closed = False
    try:
        return {**opened, "objects": list_objects(project_id)["objects"], "description": describe_project(project_id)}
    except BaseException as exc:
        _auto_close_internal_project(project_id, exc)
        closed = True
        raise
    finally:
        if not closed:
            _auto_close_internal_project(project_id)


def create_tiny_smoke_project(path: str, overwrite: bool = False) -> dict[str, Any]:
    opened = new_project()
    project_id = opened["project_id"]
    closed = False
    try:
        add_fdtd_region(project_id, "FDTD", {"x span": 1e-6, "y span": 1e-6, "z span": 1e-6, "mesh accuracy": 1})
        add_rectangle(project_id, "block", {"x span": 2e-7, "y span": 2e-7, "z span": 2e-7, "material": "Si (Silicon) - Palik"})
        add_dipole_source(project_id, "source", {"wavelength start": 4e-7, "wavelength stop": 7e-7})
        add_power_monitor(project_id, "T_monitor", {"monitor type": "2D Z-normal"})
        saved = save_project_as(project_id, path, overwrite=overwrite)
        objects = list_objects(project_id)["objects"]
        return {
            **opened,
            **saved,
            "objects": objects,
            "description": describe_project(project_id),
            "warnings": [
                "Tiny smoke project is not a production OLED/FDTD template; it only verifies authoring, save, inspect, and run plumbing.",
                "Material names can be installation-dependent in real Lumerical environments.",
            ],
        }
    except BaseException as exc:
        _auto_close_internal_project(project_id, exc)
        closed = True
        raise
    finally:
        if not closed:
            _auto_close_internal_project(project_id)


def run_tiny_smoke_project(path: str, timeout_sec: int = 120) -> dict[str, Any]:
    opened = open_fsp(path, readonly=False)
    project_id = opened["project_id"]
    closed = False
    try:
        run = run_simulation(project_id, timeout_sec=timeout_sec)
        result = get_monitor_result(project_id, "T_monitor", "T")
        return {**opened, "run": run, "result": result}
    except BaseException as exc:
        _auto_close_internal_project(project_id, exc)
        closed = True
        raise
    finally:
        if not closed:
            _auto_close_internal_project(project_id)


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


def close_project(project_id: str) -> dict[str, Any]:
    """Close an open project by project_id to release the backing Lumerical session/license."""
    return _ADAPTER.close_project(project_id)


def close(session_id: str) -> dict[str, Any]:
    """Close open project sessions by legacy session_id."""
    return _ADAPTER.close(session_id)


def validate_experiment_plan(plan: dict[str, Any]) -> dict[str, Any]:
    missing=[k for k in ["base_fsp","run_name","approved_changes","monitor_name","result_name"] if k not in plan]
    if missing: return {"ok": False, "errors": [f"missing {k}" for k in missing]}
    if not Path(plan["base_fsp"]).exists(): return {"ok": False, "errors": [f"base_fsp does not exist: {plan['base_fsp']}"]}
    return {"ok": True, "errors": [], "warnings": ["Real object/property/monitor validation requires opening project; fake validation occurs during execution."]}


def export_csv(rows: list[dict[str, Any]], path: str) -> dict[str, Any]:
    return export_monitor_csv(rows, path)


def export_monitor_plot(project_id: str, monitor_name: str, result_name: str, path: str, overwrite: bool = False) -> dict[str, Any]:
    """Export a 1D normalized monitor result as a PNG plot."""
    result = get_monitor_result(project_id, monitor_name, result_name)
    normalized = normalize_monitor_result(result)
    title = f"{normalized['monitor_name'] or monitor_name}: {normalized['result_name'] or result_name}"
    plot = export_xy_plot(
        [{"label": str(normalized["result_name"] or result_name), "x": normalized["x"], "y": normalized["y"]}],
        path,
        title=title,
        x_label=normalized["x_label"],
        y_label=normalized["y_label"],
        overwrite=overwrite,
    )
    return {**plot, "project_id": project_id, "monitor_name": monitor_name, "result_name": result_name}


def export_sweep_plot(
    path: str,
    rows: list[dict[str, Any]] | None = None,
    csv_path: str | None = None,
    x_key: str = "wavelength_m",
    y_key: str = "result_value",
    series_key: str = "value",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Export sweep rows or a sweep CSV as an overlay PNG plot."""
    if rows is None:
        if csv_path is None:
            raise ValueError("export_sweep_plot requires rows or csv_path")
        rows = read_sweep_csv(csv_path)
    series = normalize_sweep_rows(rows, x_key=x_key, y_key=y_key, series_key=series_key)
    plot = export_xy_plot(series, path, title="parameter sweep", x_label=x_key, y_label=y_key, overwrite=overwrite)
    return {**plot, "x_key": x_key, "y_key": y_key, "series_key": series_key}


def export_field_image(
    project_id: str,
    monitor_name: str,
    result_name: str,
    path: str,
    component: str | None = None,
    plane: str | None = None,
    slice_index: int | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Export a conservative normalized 2D field result subset as a PNG image."""
    result = get_monitor_result(project_id, monitor_name, result_name)
    normalized = normalize_field_matrix(result, component=component, plane=plane, slice_index=slice_index)
    title_parts = [monitor_name, result_name]
    if normalized.get("component"):
        title_parts.append(str(normalized["component"]))
    title = ": ".join(title_parts)
    image = export_heatmap(normalized["matrix"], path, title=title, overwrite=overwrite)
    return {
        **image,
        "project_id": project_id,
        "monitor_name": monitor_name,
        "result_name": result_name,
        "component": normalized.get("component"),
        "plane": normalized.get("plane"),
    }


def run_parameter_sweep(base_fsp: str, run_name: str, object_name: str, property_name: str, values: list[Any], monitor_name: str, result_name: str, approved_changes: list[dict[str, Any]] | None = None, dry_run: bool = False) -> dict[str, Any]:
    if dry_run:
        return propose_experiment_plan(base_fsp, run_name, object_name, property_name, values, monitor_name, result_name)
    allowed = approved_changes or [{"object_name": object_name, "property_name": property_name, "allowed_values": values}]
    if not any(c.get("object_name")==object_name and c.get("property_name")==property_name and set(values).issubset(set(c.get("allowed_values", []))) for c in allowed):
        raise ValueError("sweep values are not covered by approved_changes")
    before=sha256_file(base_fsp)
    run=create_run_dir(base_fsp, run_name)
    opened=open_fsp(run["working_fsp"], readonly=False)
    project_id = opened["project_id"]
    closed = False
    try:
        rows=[]
        for i,value in enumerate(values, start=1):
            change=set_object_property(project_id, object_name, property_name, value, run_id=run["run_id"])
            status=run_simulation(project_id, run_id=run["run_id"])["status"]
            result=get_monitor_result(project_id, monitor_name, result_name)
            _require_normalized_monitor_result(result)
            wavelengths=result["axes"]["wavelength_m"]["values"]
            for wl,rv in zip(wavelengths, result["values"]):
                rows.append({"run_id": run["run_id"], "case_id": f"case_{i:04d}", "object": object_name, "property": property_name, "value": value, "monitor": monitor_name, "result": result_name, "wavelength_m": wl, "result_value": rv, "status": status})
        csv_path=str(Path(run["run_dir"])/"results"/"results.csv")
        summary_path=str(Path(run["run_dir"])/"summary.md")
        csv_info=export_monitor_csv(rows, csv_path)
        sweep_plot=export_sweep_plot(str(Path(run["run_dir"])/"results"/"sweep.png"), rows=rows, overwrite=True)
        summary=generate_summary(summary_path, run_id=run["run_id"], parameter={"object": object_name, "property": property_name, "values": values}, result_rows=rows)
        after=sha256_file(base_fsp)
        if before != after:
            raise RuntimeError("safety violation: base .fsp checksum changed")
        return {"run_id": run["run_id"], "run_dir": run["run_dir"], "working_fsp": run["working_fsp"], "results_csv": csv_info["path"], "sweep_plot_png": sweep_plot["path"], "summary_md": summary["path"], "provenance_json": run["provenance_path"], "rows": len(rows), "base_checksum_unchanged": True}
    except BaseException as exc:
        _auto_close_internal_project(project_id, exc)
        closed = True
        raise
    finally:
        if not closed:
            _auto_close_internal_project(project_id)
