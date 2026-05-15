from __future__ import annotations

import logging
import os

from mcp.server.fastmcp import FastMCP

from . import tools
from .adapters.ansys_core import AnsysCoreAdapter

SERVER_NAME = tools.SERVER_NAME
logger = logging.getLogger(__name__)


def create_server() -> FastMCP:
    server = FastMCP(SERVER_NAME, instructions="FDTD Experiment Agent MCP. Inspect, plan, safely copy, sweep, and report Lumerical .fsp projects. Default adapter is fake/CI-safe.")
    for fn in [tools.server_info, tools.active_adapter, tools.reset_state, tools.lumerical_status, tools.open_fsp, tools.new_project, tools.save_project_as, tools.add_fdtd_region, tools.add_rectangle, tools.add_dipole_source, tools.add_power_monitor, tools.delete_object, tools.list_objects, tools.list_properties, tools.get_object_property, tools.set_object_property, tools.describe_project, tools.create_run_dir, tools.run_simulation, tools.get_monitor_result, tools.close_project, tools.close, tools.run_parameter_sweep, tools.export_csv, tools.export_monitor_plot, tools.export_sweep_plot, tools.export_field_image, tools.inspect_fsp, tools.create_tiny_smoke_project, tools.run_tiny_smoke_project, tools.propose_experiment_plan, tools.validate_experiment_plan]:
        server.tool(name=fn.__name__)(fn)
    return server


def preimport_real_adapters() -> None:
    """Warm the slow Ansys import before serving MCP tool calls.

    Company-local ansys.lumerical.core import can take several minutes on first
    call. Doing it at process startup moves the cost to MCP server startup,
    where clients such as Cline can use a larger startup timeout, and avoids the
    first open_fsp call timing out inside the tool call path.
    """
    if os.environ.get("FDTD_LAB_PREIMPORT_ANSYS_CORE", "1").lower() in {"0", "false", "no", "off"}:
        logger.info("Skipping ansys-lumerical-core preimport because FDTD_LAB_PREIMPORT_ANSYS_CORE is disabled")
        return
    try:
        AnsysCoreAdapter()._import_core()
    except Exception as exc:
        # Keep fake/default MCP usable outside the company Lumerical environment.
        logger.warning("ansys-lumerical-core preimport failed; continuing MCP server startup: %s", exc)


def main() -> None:
    logging.basicConfig(level=os.environ.get("FDTD_LAB_LOG_LEVEL", "INFO"))
    preimport_real_adapters()
    create_server().run(transport="stdio")
