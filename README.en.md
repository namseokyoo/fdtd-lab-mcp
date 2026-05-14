# fdtd-lab-mcp

An MCP server for Ansys Lumerical FDTD `.fsp` workflows.

## Features

- Open `.fsp` files
- List project objects
- List object properties
- Read/write property values
- Create safe run directories
- Run simulations
- Run parameter sweeps
- Read monitor results
- Export results to CSV
- Create blank projects
- Create minimal FDTD authoring smoke projects
- Support `fake`, `ansys_core`, and `lumapi` adapters

## Adapters

| Adapter | Description | Use case |
| --- | --- | --- |
| `fake` | Test adapter that works without Lumerical | Default for development/CI |
| `ansys_core` | Adapter based on `ansys-lumerical-core` | Preferred real Lumerical adapter |
| `lumapi` | Direct `lumapi` adapter | Fallback |

Real Lumerical operations require a safety gate:

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
```

## Test

```bash
python -m pytest
```

Expected result:

```text
25 passed, 1 skipped
```

## Run the MCP server

Default mode uses the `fake` adapter.

```bash
fdtd-lab-mcp
```

Use `ansys_core` in a real Lumerical environment:

```bash
export FDTD_LAB_ADAPTER=ansys_core
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

Use `lumapi` fallback:

```bash
export FDTD_LAB_ADAPTER=lumapi
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

## MCP Tools

### Status and adapters

| Tool | Description |
| --- | --- |
| `active_adapter` | Show current adapter |
| `reset_state` | Reset adapter/state |
| `lumerical_status` | Check adapter detection status |

### File and project inspection

| Tool | Description |
| --- | --- |
| `open_fsp` | Open an `.fsp` file |
| `inspect_fsp` | Open `.fsp` and return objects/description |
| `list_objects` | List objects |
| `list_properties` | List object properties |
| `get_object_property` | Read a property value |
| `describe_project` | Summarize sources/monitors/regions/structures |

### Modification, run, and results

| Tool | Description |
| --- | --- |
| `set_object_property` | Change a property value |
| `create_run_dir` | Create a copied `.fsp` and provenance file |
| `propose_experiment_plan` | Create a sweep plan |
| `validate_experiment_plan` | Validate a sweep plan |
| `run_parameter_sweep` | Run a parameter sweep |
| `run_simulation` | Run a simulation |
| `get_monitor_result` | Read monitor results |
| `export_csv` | Export CSV |

### Authoring

| Tool | Description |
| --- | --- |
| `new_project` | Create a blank project |
| `save_project_as` | Save as `.fsp` |
| `add_fdtd_region` | Add an FDTD region |
| `add_rectangle` | Add a rectangle/structure |
| `add_dipole_source` | Add a dipole source |
| `add_power_monitor` | Add a power monitor |
| `delete_object` | Delete an object |
| `create_tiny_smoke_project` | Create a minimal smoke `.fsp` |
| `run_tiny_smoke_project` | Run/check a smoke `.fsp` |

## Usage examples

### 1. Inspect an `.fsp`

```python
from fdtd_lab_mcp import tools

tools.reset_state(adapter="fake")
out = tools.inspect_fsp("/path/to/sample.fsp")
print(out["objects"])
print(out["description"])
```

### 2. Modify a property

```python
opened = tools.open_fsp("/path/to/sample.fsp", readonly=False)
project_id = opened["project_id"]

before_after = tools.set_object_property(
    project_id,
    object_name="ETL",
    property_name="z span",
    value=4e-8,
)
print(before_after)
```

### 3. Run a parameter sweep

```python
out = tools.run_parameter_sweep(
    base_fsp="/path/to/base.fsp",
    run_name="etl_sweep",
    object_name="ETL",
    property_name="z span",
    values=[2e-8, 3e-8, 4e-8],
    monitor_name="T_monitor",
    result_name="T",
)
print(out["results_csv"])
print(out["summary_md"])
```

### 4. Create a tiny smoke project

```python
from pathlib import Path
from fdtd_lab_mcp import tools

tools.reset_state(adapter="fake")
path = Path("/tmp/fdtd_lab_tiny.fsp")
created = tools.create_tiny_smoke_project(str(path), overwrite=True)
print(created["path"])
print([o["name"] for o in created["objects"]])
```

Created objects:

```text
FDTD
block
source
T_monitor
```

## Hermes MCP config example

```yaml
mcp_servers:
  fdtd_lab:
    command: "fdtd-lab-mcp"
    env:
      FDTD_LAB_ADAPTER: "ansys_core"
      FDTD_LAB_ENABLE_REAL_LUMERICAL: "1"
      FDTD_LAB_PREIMPORT_ANSYS_CORE: "1"
      # If needed:
      # ANSYSLMD_LICENSE_FILE: "1055@your-license-server"
    timeout: 3600
    connect_timeout: 600
```

## Cline config

Example file:

```text
docs/cline_mcp_setting.json
```

## Real Lumerical checks

Detection-only:

```bash
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core
python -m fdtd_lab_mcp.integration_probe --adapter lumapi
```

Real open/list:

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
export FDTD_LAB_SAMPLE_FSP=/path/to/non-sensitive-sample.fsp
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core --open --list
```

Authoring smoke check:

```text
docs/real-authoring-smoke.md
```

## Development commands

```bash
python -m pytest
python -m pytest tests/test_authoring_fake.py -q
python -m compileall src tests
git diff --check
```
