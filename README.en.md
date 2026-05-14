# fdtd-lab-mcp

`fdtd-lab-mcp` is an experimental MCP(Model Context Protocol) server for safely inspecting, copying, modifying, running, and reporting Ansys Lumerical FDTD `.fsp` projects.

The primary target environment is a **company local-network Lumerical environment**. For development and CI, the default adapter is `fake`, so the project can be tested without a Lumerical installation or license.

## Core direction

This project is not intended to be a generator that creates complete production templates from scratch. Instead, it builds reliability in the following order:

1. Safely open and inspect existing `.fsp` files.
2. Copy the original file into a run directory before experimentation.
3. Query objects/properties and apply limited, explicit modifications.
4. Run parameter sweeps, simulations, and monitor result exports.
5. Add minimal CAD authoring primitives only when needed for blank-project and smoke-fixture validation.

In other words, the current authoring feature is **not** a production OLED/FDTD template system. It is the minimum plumbing needed to validate Lumerical API connectivity, save behavior, inspect behavior, and run/result paths.

## Adapter architecture

Supported adapters:

| Adapter | Purpose | Requires Lumerical license |
| --- | --- | --- |
| `fake` | Deterministic adapter for development and CI | No |
| `ansys_core` | Real Lumerical adapter based on `ansys-lumerical-core` | Yes |
| `lumapi` | Direct `lumapi` fallback adapter | Yes |

Intended priority:

1. `ansys_core`
2. `lumapi`
3. `fake` as the development/test default

Real Lumerical operations always require an explicit safety gate:

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
```

Without this value, real adapter operations such as open/run/new project are blocked. This prevents accidental license consumption and accidental mutation of real projects.

## Quick test

Development and CI validation run without Lumerical:

```bash
python -m pytest
```

Expected result example:

```text
25 passed, 1 skipped
```

## Running the MCP server

Default execution uses the `fake` adapter:

```bash
fdtd-lab-mcp
```

For real company-local Lumerical usage with `ansys_core`:

```bash
export FDTD_LAB_ADAPTER=ansys_core
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

If `ansys-lumerical-core` is not available in the local environment, use direct `lumapi` as fallback:

```bash
export FDTD_LAB_ADAPTER=lumapi
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

## Handling slow `import_core`

In some company environments, importing `ansys.lumerical.core` can take a long time. If the import happens inside the first `open_fsp` tool call, that first tool call can time out.

To reduce that risk, the MCP server pre-imports `ansys.lumerical.core` during server startup by default.

```bash
export FDTD_LAB_PREIMPORT_ANSYS_CORE=1
```

This is enabled by default. To disable it:

```bash
export FDTD_LAB_PREIMPORT_ANSYS_CORE=0
```

The intent is to:

- Move the slow import cost from the first tool call into MCP server startup.
- Let clients such as Cline/Hermes use a longer startup/connect timeout.
- Reduce timeout risk on the first `open_fsp` call.

## MCP tools overview

### Status and adapter management

| Tool | Description |
| --- | --- |
| `active_adapter` | Report the current adapter and environment default |
| `reset_state` | Reset in-memory state and optionally switch adapter |
| `lumerical_status` | Check fake/real adapter detection status |

### Existing `.fsp` inspection and modification

| Tool | Description |
| --- | --- |
| `open_fsp` | Open an `.fsp` file |
| `inspect_fsp` | Open a file, list objects, and return project description |
| `list_objects` | List objects in the current project |
| `list_properties` | List properties for an object |
| `get_object_property` | Read an object property value |
| `set_object_property` | Modify an object property value |
| `describe_project` | Summarize source/monitor/simulation region/structure candidates |

### Safe experiment and run management

| Tool | Description |
| --- | --- |
| `create_run_dir` | Copy the original `.fsp` into a run directory and create provenance |
| `propose_experiment_plan` | Create a dry-run parameter sweep plan |
| `validate_experiment_plan` | Validate a sweep plan |
| `run_parameter_sweep` | Run a parameter sweep within approved value ranges |
| `run_simulation` | Run a simulation |
| `get_monitor_result` | Read monitor results |
| `export_csv` | Export result rows to CSV |

### Phase A: minimal authoring primitives

These tools provide blank-project and minimal CAD primitive authoring.

| Tool | Description |
| --- | --- |
| `new_project` | Create a blank FDTD project session |
| `save_project_as` | Save a project as `.fsp` |
| `add_fdtd_region` | Add an FDTD simulation region |
| `add_rectangle` | Add a rectangle/structure object |
| `add_dipole_source` | Add a dipole source |
| `add_power_monitor` | Add a power monitor |
| `delete_object` | Delete an object |

Important constraints:

- These tools are not a production template generator.
- Object names reject quote, semicolon, newline, and other script-injection-risk characters.
- Save paths must use the `.fsp` suffix.
- Existing files are not overwritten unless `overwrite=True` is explicitly passed.
- Arbitrary Lumerical script execution is intentionally not exposed.

### Phase B: tiny smoke project

| Tool | Description |
| --- | --- |
| `create_tiny_smoke_project` | Create a minimal smoke `.fsp` with FDTD/source/monitor/structure |
| `run_tiny_smoke_project` | Open the smoke `.fsp` and validate run/result plumbing |

`create_tiny_smoke_project` creates these objects:

```text
FDTD
block
source
T_monitor
```

The tiny project validates:

- Blank project creation
- Primitive object creation
- `.fsp` save behavior
- Object list/description behavior
- Optional run/result path behavior

Important: this tiny smoke project is **not a production OLED/FDTD template**. Real production stack, material, source, monitor, boundary, and mesh conventions should be derived from actual company `.fsp` samples later, not guessed in this repository.

## Direct Python smoke example

Run with the fake adapter, no Lumerical required:

```bash
python - <<'PY'
from pathlib import Path
from fdtd_lab_mcp import tools

out_path = Path('/tmp/fdtd_lab_tiny_fake.fsp')
tools.reset_state(adapter='fake')
created = tools.create_tiny_smoke_project(str(out_path), overwrite=True)
print(created['path'])
print([o['name'] for o in created['objects']])

run = tools.run_tiny_smoke_project(str(out_path), timeout_sec=120)
print(run['run']['status'])
print(run['result']['monitor_name'])
PY
```

Real Lumerical authoring smoke instructions are documented here:

```text
docs/real-authoring-smoke.md
```

## Real integration probe

Company-local Lumerical validation is documented here:

```text
docs/company-local-integration.md
```

Detection-only examples:

```bash
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core
python -m fdtd_lab_mcp.integration_probe --adapter lumapi
```

Real open/list validation requires the explicit safety gate and a non-sensitive sample `.fsp`:

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
export FDTD_LAB_SAMPLE_FSP=/path/to/non-sensitive-sample.fsp
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core --open --list
```

## Hermes MCP configuration example

```yaml
mcp_servers:
  fdtd_lab:
    command: "fdtd-lab-mcp"
    env:
      FDTD_LAB_ADAPTER: "ansys_core"
      FDTD_LAB_ENABLE_REAL_LUMERICAL: "1"
      FDTD_LAB_SAMPLE_FSP: "/path/to/non-sensitive-sample.fsp"
      FDTD_LAB_PREIMPORT_ANSYS_CORE: "1"
      # If required by the company license setup:
      # ANSYSLMD_LICENSE_FILE: "1055@your-license-server"
    timeout: 3600
    connect_timeout: 600
```

## Cline MCP configuration example

See:

```text
docs/cline_mcp_setting.json
```

This configuration is intended to:

- Use a longer MCP timeout.
- Select `FDTD_LAB_ADAPTER=ansys_core`.
- Explicitly set `FDTD_LAB_ENABLE_REAL_LUMERICAL=1`.
- Keep `FDTD_LAB_PREIMPORT_ANSYS_CORE=1` so the slow import happens during server startup.

## Safety policy

Default safety policy:

1. Development/CI defaults to the `fake` adapter.
2. Real adapters do not perform real open/run/new project work unless `FDTD_LAB_ENABLE_REAL_LUMERICAL=1` is set.
3. Existing `.fsp` experiments use run-directory copies instead of mutating originals directly.
4. Parameter sweeps preserve dry-run plans and approved value ranges.
5. Authoring primitives are intentionally minimal; arbitrary script execution is not exposed.
6. Tiny smoke projects are plumbing fixtures, not production templates.

## Common developer commands

```bash
# Full test suite
python -m pytest

# Authoring/smoke fake tests only
python -m pytest tests/test_authoring_fake.py -q

# Syntax/bytecode sanity check
python -m compileall src tests

# Git whitespace check
git diff --check
```

## Current scope and non-scope

Implemented:

- Existing `.fsp` inspect/modify/run/sweep/export
- Real adapter detection and safety gate
- `ansys_core` import pre-warm
- Minimal authoring primitives
- Tiny smoke project creation/run fixture
- CI tests based on the fake adapter

Intentionally not implemented:

- Production OLED stack template generation
- Display pixel/cavity or other domain-specific template generation
- Arbitrary Lumerical script executor exposure
- Guessing real company material DB / mesh / boundary / source conventions

Once actual company `.fsp` samples are available, the preferred expansion path is:

- `extract_project_recipe`
- `clone_project_with_changes`
- `compare_project_structure`
- `apply_property_patch`

In short, production expansion should be based on **extracting and safely modifying recipes from validated real projects**, not on imagined templates.
