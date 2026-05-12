from __future__ import annotations

from typing import Any

from fdtd_lab_mcp.adapters.real_base import ScriptSessionAdapter
from fdtd_lab_mcp.errors import AdapterUnavailable


class LumapiAdapter(ScriptSessionAdapter):
    name = "lumapi"

    def _import_lumapi(self) -> Any:
        try:
            import lumapi  # type: ignore
        except Exception as exc:
            raise AdapterUnavailable(f"direct lumapi is unavailable: {exc}") from exc
        return lumapi

    def status(self) -> dict[str, Any]:
        try:
            lumapi = self._import_lumapi()
            return {
                "ok": True,
                "installation_detected": True,
                "api": "lumapi",
                "module": getattr(lumapi, "__name__", None),
                "products": ["FDTD"],
                "notes": ["Direct lumapi import succeeded; open/run still require FDTD_LAB_ENABLE_REAL_LUMERICAL=1 and a company-local license."],
            }
        except Exception as exc:
            return {"ok": False, "installation_detected": False, "api": "lumapi", "error": str(exc), "products": ["FDTD"], "notes": []}

    def open_project(self, path: str, readonly: bool = True):
        self._require_enabled()
        fsp = self._validate_fsp(path)
        lumapi = self._import_lumapi()
        try:
            session = lumapi.FDTD(hide=True)
            session.load(fsp)
        except Exception as exc:  # pragma: no cover - requires real Lumerical
            raise AdapterUnavailable(f"Failed to open FDTD project through direct lumapi: {exc}") from exc
        return self._store_session(session, fsp, readonly=readonly)
