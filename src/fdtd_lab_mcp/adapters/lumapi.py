from __future__ import annotations
from .fake import FakeLumericalAdapter
from fdtd_lab_mcp.errors import AdapterUnavailable

class LumapiAdapter(FakeLumericalAdapter):
    name = "lumapi"
    def status(self) -> dict:
        try:
            import lumapi  # type: ignore
            return {"ok": True, "installation_detected": True, "api": "lumapi", "module": getattr(lumapi, "__name__", None), "products": ["FDTD"], "notes": ["Direct lumapi import succeeded; integration tests still require license."]}
        except Exception as exc:
            return {"ok": False, "installation_detected": False, "api": "lumapi", "error": str(exc), "products": ["FDTD"], "notes": []}
    def open_project(self, path: str, readonly: bool = True):
        raise AdapterUnavailable("LumapiAdapter is detection-only in Phase 3; use gated lumerical integration task before enabling real mutation/run.")
