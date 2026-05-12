from __future__ import annotations
from importlib.metadata import PackageNotFoundError, version
from typing import Any
from .fake import FakeLumericalAdapter
from fdtd_lab_mcp.errors import AdapterUnavailable

class AnsysCoreAdapter(FakeLumericalAdapter):
    name = "ansys_core"
    def status(self) -> dict[str, Any]:
        try:
            import ansys.lumerical.core as core  # type: ignore
            pkg = version("ansys-lumerical-core")
            return {"ok": True, "installation_detected": True, "api": "ansys-lumerical-core", "package_version": pkg, "module": getattr(core, "__name__", None), "products": ["FDTD"], "notes": ["Real adapter detection succeeded; integration tests still require license."]}
        except PackageNotFoundError:
            return {"ok": False, "installation_detected": False, "api": "ansys-lumerical-core", "error": "package not installed", "products": ["FDTD"], "notes": []}
        except Exception as exc:
            return {"ok": False, "installation_detected": False, "api": "ansys-lumerical-core", "error": str(exc), "products": ["FDTD"], "notes": []}
    def open_project(self, path: str, readonly: bool = True):
        raise AdapterUnavailable("AnsysCoreAdapter is detection-only in Phase 3; use gated lumerical integration task before enabling real mutation/run.")
