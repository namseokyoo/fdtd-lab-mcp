from __future__ import annotations

import logging
import time
from importlib.metadata import PackageNotFoundError, version
from types import ModuleType
from typing import Any

from fdtd_lab_mcp.adapters.real_base import ScriptSessionAdapter
from fdtd_lab_mcp.errors import AdapterUnavailable

logger = logging.getLogger(__name__)
_CORE_CACHE: ModuleType | None = None


class AnsysCoreAdapter(ScriptSessionAdapter):
    name = "ansys_core"

    def _import_core(self) -> Any:
        global _CORE_CACHE
        if _CORE_CACHE is not None:
            logger.debug("Using cached ansys.lumerical.core module")
            return _CORE_CACHE

        start = time.perf_counter()
        logger.info("Importing ansys.lumerical.core")
        try:
            import ansys.lumerical.core as core  # type: ignore
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.exception("Failed to import ansys.lumerical.core after %.3fs", elapsed)
            raise AdapterUnavailable(f"ansys-lumerical-core is unavailable: {exc}") from exc

        _CORE_CACHE = core
        logger.info("Imported ansys.lumerical.core in %.3fs", time.perf_counter() - start)
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
        logger.info("Opening FDTD project through ansys-lumerical-core path=%s readonly=%s", path, readonly)
        self._require_enabled()
        fsp = self._validate_fsp(path)
        core = self._import_core()
        start = time.perf_counter()
        try:
            logger.info("Creating ansys.lumerical.core.FDTD session path=%s", fsp)
            session = core.FDTD(hide=True, project=fsp)
        except Exception as exc:  # pragma: no cover - requires real Lumerical
            logger.exception("Failed to open FDTD project after %.3fs path=%s", time.perf_counter() - start, fsp)
            raise AdapterUnavailable(f"Failed to open FDTD project through ansys-lumerical-core: {exc}") from exc
        logger.info("Opened FDTD project in %.3fs path=%s", time.perf_counter() - start, fsp)
        return self._store_session(session, fsp, readonly=readonly)

    def _create_blank_session(self):
        core = self._import_core()
        return core.FDTD(hide=True)
