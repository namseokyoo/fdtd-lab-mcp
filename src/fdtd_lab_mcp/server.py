from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from . import tools

SERVER_NAME = "fdtd-lab-mcp"

def create_server() -> FastMCP:
    server = FastMCP(SERVER_NAME, instructions="FDTD Experiment Agent MCP. Inspect, plan, safely copy, sweep, and report Lumerical .fsp projects. Default adapter is fake/CI-safe.")
    for fn in [tools.active_adapter, tools.reset_state, tools.lumerical_status, tools.open_fsp, tools.list_objects, tools.list_properties, tools.get_object_property, tools.set_object_property, tools.describe_project, tools.create_run_dir, tools.run_simulation, tools.get_monitor_result, tools.run_parameter_sweep, tools.export_csv, tools.inspect_fsp, tools.propose_experiment_plan, tools.validate_experiment_plan]:
        server.tool(name=fn.__name__)(fn)
    return server

def main() -> None:
    create_server().run(transport="stdio")
