from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from fdtd_lab_mcp.adapters.real_base import ScriptSessionAdapter
from fdtd_lab_mcp.errors import AdapterUnavailable


class AnsysCoreAdapter(ScriptSessionAdapter):
    name = "ansys_core"

    def _import_core(self) -> Any:
        try:
            import ansys.lumerical.core as core  # type: ignore
        except Exception as exc:
            raise AdapterUnavailable(f"ansys-lumerical-core is unavailable: {exc}") from exc
        return core

    def status(self) -> dict[str, Any]:
        try:
            core = self._import_core()
            try:
                pkg = version("ansys-lumerical-core")
            except PackageNotFoundError:
                pkg = None
            return {
                "ok": True,
                "installation_detected": True,
                "api": "ansys-lumerical-core",
                "package_version": pkg,
                "module": getattr(core, "__name__", None),
                "products": ["FDTD"],
                "notes": ["Real adapter detection succeeded; open/run still require FDTD_LAB_ENABLE_REAL_LUMERICAL=1 and a company-local license."],
            }
        except Exception as exc:
            return {"ok": False, "installation_detected": False, "api": "ansys-lumerical-core", "error": str(exc), "products": ["FDTD"], "notes": []}

    def open_project(self, path: str, readonly: bool = True):
        self._require_enabled()
        fsp = self._validate_fsp(path)
        core = self._import_core()
        try:
            session = core.FDTD(hide=True, project=fsp)
        except Exception as exc:  # pragma: no cover - requires real Lumerical
            raise AdapterUnavailable(f"Failed to open FDTD project through ansys-lumerical-core: {exc}") from exc
        return self._store_session(session, fsp, readonly=readonly)
