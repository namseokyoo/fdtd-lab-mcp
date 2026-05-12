# FDTD Lab MCP PRD

**Date:** 2026-05-12  
**Owner:** SidequestLab  
**Working name:** `fdtd-lab-mcp`  
**Target user:** OLED/Display/FDTD engineers and AI agents operating Ansys Lumerical workflows  
**Status:** Draft PRD for Core implementation

---

## 1. Product Summary

`fdtd-lab-mcp` is an MCP server that lets AI agents inspect, plan, safely modify, run, and analyze FDTD simulation projects, starting with Ansys Lumerical `.fsp` files.

The goal is not to build another thin Lumerical session wrapper. The goal is to create an **FDTD Experiment Agent MCP**: a tool layer that understands simulation project structure, identifies objects/variables/monitors, proposes safe sweep candidates, manages run folders without overwriting originals, and produces results in CSV/plot/summary form.

Initial domain focus: **OLED/Display optical stack simulation**.

---

## 2. Background

FDTD is a numerical method, not a standalone program. In practical workflows, engineers use tools such as Ansys Lumerical FDTD to create `.fsp` project files containing geometry, materials, sources, monitors, boundary conditions, mesh, and solver settings.

Python automation usually works by controlling Lumerical through APIs such as `lumapi` or newer Ansys packages. The Python script does not directly edit `.fsp` like a text file. Instead, it launches or connects to Lumerical, opens the `.fsp`, modifies named objects/properties, runs the solver, and extracts results.

Existing organizations often already have `.fsp` templates, naming rules, sweep scripts, and post-processing notebooks. The pain point is that AI agents need a safe and semantic interface to inspect those assets and operate them without relying entirely on GUI inspection.

---

## 3. Existing Reference

Reference repo:

- `SheepWangZz/ansys-lumerical-mcp`
- URL: https://github.com/SheepWangZz/ansys-lumerical-mcp
- Description: MCP server for automating Ansys Lumerical through `ansys-lumerical-core`
- Implemented tools at review time:
  - `lumerical_status`
  - `list_available_products`
  - `open_session`
  - `list_sessions`
  - `close_session`
  - `run_script`
  - `put_variable`
  - `get_variable`

This repo is useful as a baseline MCP/session-control reference, but `fdtd-lab-mcp` must differentiate itself at the experiment-management layer.

---

## 4. Differentiation

### Existing baseline approach

```text
AI → open Lumerical session
AI → run script
AI → put/get variables
```

This is a generic remote-control layer.

### Our product approach

```text
AI → inspect .fsp project
AI → classify objects/sources/monitors/materials
AI → discover editable parameters
AI → propose experiment plan
AI → create safe run directory
AI → copy original .fsp
AI → modify only approved variables
AI → run simulation
AI → extract monitor results
AI → export CSV/plot/summary.md
```

This is an FDTD experiment workflow layer.

### Core differentiation pillars

1. **Project Inspector**
   - Summarizes `.fsp` structure without forcing the user to inspect every object in GUI.

2. **Semantic Naming Layer**
   - Maps generic names such as `rect1`, `monitor_2`, `source_1` to likely roles such as ETL, EML, transmission monitor, reflection monitor, plane wave source.

3. **Experiment Plan Generator**
   - Produces an explicit plan before modifying or running simulations.

4. **Safe Run Manager**
   - Never overwrites original `.fsp` files.
   - Creates run folders and copied case files.

5. **OLED/Display Domain Pack**
   - Provides OLED stack-specific helpers and analysis routines.

---

## 5. Target Users

### Primary

- OLED/display optical simulation engineers
- Photonics/FDTD engineers using Ansys Lumerical
- AI agents assisting with simulation automation

### Secondary

- Researchers doing optical stack, cavity, grating, metasurface, or photonic device sweeps
- Teams wanting reproducible FDTD batch workflows

---

## 6. User Problems

1. `.fsp` files are not readable/editable like source code in VSCode.
2. Existing automation requires knowing exact object names and property names.
3. GUI inspection is slow and not agent-friendly.
4. Parameter sweeps are easy to run unsafely and overwrite project files.
5. Results often end up scattered across scripts, folders, screenshots, and manual notes.
6. Existing MCP wrappers expose low-level session operations but do not understand FDTD experiment workflows.

---

## 7. Product Goals

### MVP Goals

- Open or attach to a Lumerical FDTD session.
- Open a `.fsp` project.
- Inspect objects, sources, monitors, and basic properties.
- Read and write named object properties safely.
- Run simulation.
- Extract monitor results.
- Execute a basic parameter sweep.
- Export CSV and summary markdown.
- Preserve the original `.fsp` file.

### Non-Goals for MVP

- Full replacement for Lumerical GUI.
- Full physics validation engine.
- Cloud/HPC scheduling.
- Automatic license management beyond basic status checks.
- Universal support for all Lumerical products.
- Perfect semantic inference of every object role.

---

## 8. Key User Stories

### Story 1: Inspect a project

As an engineer, I want the MCP to summarize a `.fsp` file so that I can understand available objects and candidate sweep variables without manually clicking every object in GUI.

Acceptance criteria:

- Given a valid `.fsp`, the tool returns:
  - object list
  - likely sources
  - likely monitors
  - likely simulation region
  - material/object names if accessible
  - common editable properties

### Story 2: Read existing values

As an engineer, I want to query values such as ETL thickness or source wavelength so that I know the baseline before modifying anything.

Acceptance criteria:

- `get_object_property(object_name, property_name)` returns value and unit if possible.
- If object/property does not exist, return a clear error and suggest available alternatives.

### Story 3: Modify one variable safely

As an engineer, I want to change one parameter in a copied run file so that the original `.fsp` stays untouched.

Acceptance criteria:

- Original file is never overwritten.
- Run directory is created.
- Copied `.fsp` file is used for modification.
- Tool records what changed.

### Story 4: Run a parameter sweep

As an engineer, I want to sweep layer thickness values and collect monitor results automatically.

Acceptance criteria:

- Sweep accepts object, property, values, monitor, result name.
- Each case gets a separate run folder or copied project file.
- Results are exported as CSV.
- A markdown summary is generated.

### Story 5: OLED-focused report

As an OLED/display engineer, I want a summary explaining how transmission/reflection/peak wavelength changed across stack variants.

Acceptance criteria:

- Tool outputs `summary.md` with:
  - parameter list
  - result table
  - best case by configured metric
  - warnings/failed cases
  - basic interpretation

---

## 9. MVP Tool Specification

### 9.1 `lumerical_status`

Purpose: Check local Lumerical/Ansys integration availability.

Returns:

```json
{
  "ok": true,
  "installation_detected": true,
  "products": ["FDTD"],
  "api": "ansys-lumerical-core or lumapi",
  "notes": []
}
```

---

### 9.2 `open_fsp`

Purpose: Open a `.fsp` project in a Lumerical session.

Inputs:

```json
{
  "path": "/path/to/base.fsp",
  "readonly": true
}
```

Behavior:

- Validates file exists.
- Opens session.
- Loads `.fsp`.
- If `readonly=true`, does not save modifications.

---

### 9.3 `list_objects`

Purpose: Return object names from the project tree.

Returns:

```json
{
  "objects": [
    {"name": "FDTD", "type": "simulation_region"},
    {"name": "source", "type": "source"},
    {"name": "ETL", "type": "structure"},
    {"name": "T_monitor", "type": "monitor"}
  ]
}
```

---

### 9.4 `list_properties`

Purpose: Return readable/editable properties for an object.

Inputs:

```json
{
  "object_name": "ETL"
}
```

Returns:

```json
{
  "object_name": "ETL",
  "properties": ["x", "y", "z", "x span", "y span", "z span", "material"]
}
```

---

### 9.5 `get_object_property`

Purpose: Read a property value.

Inputs:

```json
{
  "object_name": "ETL",
  "property_name": "z span"
}
```

Returns:

```json
{
  "object_name": "ETL",
  "property_name": "z span",
  "value": 3e-8,
  "unit_guess": "m"
}
```

---

### 9.6 `set_object_property`

Purpose: Set a property value in the active project/session.

Inputs:

```json
{
  "object_name": "ETL",
  "property_name": "z span",
  "value": 3e-8
}
```

Requirements:

- Must verify object exists.
- Must verify property exists or return clear error.
- Must record before/after values.

---

### 9.7 `describe_project`

Purpose: High-level semantic summary.

Returns:

```json
{
  "project_type_guess": "OLED stack or planar optical stack",
  "simulation_regions": ["FDTD"],
  "sources": ["source"],
  "monitors": ["T_monitor", "R_monitor"],
  "structures": ["HTL", "EML", "ETL"],
  "sweep_candidates": [
    {"object": "ETL", "property": "z span", "reason": "layer thickness"},
    {"object": "source", "property": "wavelength start", "reason": "spectral range"}
  ],
  "warnings": []
}
```

---

### 9.8 `create_run_dir`

Purpose: Create a safe run folder and copy source `.fsp`.

Inputs:

```json
{
  "base_fsp": "/path/to/base.fsp",
  "run_name": "etl_thickness_sweep"
}
```

Output example:

```json
{
  "run_dir": "runs/2026-05-12_etl_thickness_sweep",
  "working_fsp": "runs/2026-05-12_etl_thickness_sweep/base_working.fsp"
}
```

---

### 9.9 `run_simulation`

Purpose: Run active Lumerical simulation.

Inputs:

```json
{
  "timeout_sec": 3600
}
```

Returns:

```json
{
  "status": "completed",
  "elapsed_sec": 123.4,
  "warnings": []
}
```

---

### 9.10 `get_monitor_result`

Purpose: Extract monitor result.

Inputs:

```json
{
  "monitor_name": "T_monitor",
  "result_name": "T"
}
```

Returns structured arrays where possible.

---

### 9.11 `run_parameter_sweep`

Purpose: Execute a safe parameter sweep.

Inputs:

```json
{
  "base_fsp": "/path/to/base.fsp",
  "run_name": "etl_thickness_sweep",
  "object_name": "ETL",
  "property_name": "z span",
  "values": [2e-8, 3e-8, 4e-8, 5e-8],
  "monitor_name": "T_monitor",
  "result_name": "T"
}
```

Outputs:

- `runs/<run_name>/results.csv`
- `runs/<run_name>/summary.md`
- optional `runs/<run_name>/plot.png`

---

### 9.12 `export_csv`

Purpose: Save structured sweep/result data to CSV.

---

## 10. OLED/Display Domain Pack

Initial helper functions:

- `sweep_layer_thickness(layer_name, thickness_nm_list)`
- `analyze_transmission()`
- `analyze_reflection()`
- `find_peak_wavelength()`
- `detect_resonance_shift()`
- `generate_oled_optical_report()`

Initial OLED parameters:

- HTL thickness
- EML thickness
- ETL thickness
- electrode thickness
- source wavelength range
- transmission/reflection monitor outputs

---

## 11. Safety Requirements

1. Never overwrite the original `.fsp`.
2. All run operations must happen in a generated run directory.
3. Before mutation, read and log original value.
4. After mutation, read and log new value.
5. If object/property/monitor is missing, fail clearly.
6. If simulation run fails, preserve logs and continue/stop based on config.
7. Default mode should be dry-run/plan-first for destructive or expensive operations.
8. Output files must include provenance:
   - base file path
   - timestamp
   - changed variables
   - tool version
   - run status

---

## 12. Architecture

```text
MCP Client / AI Agent
        ↓
fdtd-lab-mcp server
        ↓
Session Adapter
        ↓
Ansys Lumerical API
        ↓
.fsp project / simulation engine
        ↓
Result Extractor
        ↓
CSV / plot / summary.md
```

### Modules

```text
src/fdtd_lab_mcp/
  server.py              # MCP server entrypoint
  tools/status.py        # lumerical_status
  tools/session.py       # open/close/list sessions
  tools/project.py       # open_fsp, list_objects, describe_project
  tools/properties.py    # get/set/list properties
  tools/run.py           # run_simulation
  tools/results.py       # monitor extraction, CSV export
  tools/sweep.py         # parameter sweep
  domain/oled.py         # OLED helper layer
  adapters/lumerical.py  # API adapter: ansys-lumerical-core/lumapi
  safety/run_manager.py  # copy files, run dirs, provenance
  reporting/summary.py   # summary.md generation
  reporting/plots.py     # plot generation
  tests/
```

---

## 13. Implementation Phases

### Phase 1: Research and baseline review

Tasks:

1. Clone and inspect `SheepWangZz/ansys-lumerical-mcp`.
2. Document API structure and implemented tools.
3. Check whether `ansys-lumerical-core` can discover local Lumerical.
4. Produce `docs/research/ansys-lumerical-mcp-review.md`.

Deliverable:

- Baseline review document.

---

### Phase 2: MCP scaffold

Tasks:

1. Create Python package scaffold.
2. Add MCP server entrypoint.
3. Add `lumerical_status` tool.
4. Add tests with mocked Lumerical adapter.

Deliverable:

- Installable local MCP server with status tool.

---

### Phase 3: Project Inspector

Tasks:

1. Implement `open_fsp`.
2. Implement `list_objects`.
3. Implement `list_properties`.
4. Implement `get_object_property`.
5. Implement `describe_project`.

Deliverable:

- Agent can inspect `.fsp` structure and values.

---

### Phase 4: Safe mutation and run manager

Tasks:

1. Implement run directory creation.
2. Implement `.fsp` copy behavior.
3. Implement `set_object_property` with before/after logging.
4. Implement provenance log.
5. Implement `run_simulation`.

Deliverable:

- Agent can safely modify copied `.fsp` and run it.

---

### Phase 5: Result extraction and sweep

Tasks:

1. Implement `get_monitor_result`.
2. Implement `export_csv`.
3. Implement `run_parameter_sweep`.
4. Implement summary generation.
5. Add simple plot export.

Deliverable:

- End-to-end sweep from base `.fsp` to CSV/summary.

---

### Phase 6: OLED domain pack

Tasks:

1. Implement `sweep_layer_thickness`.
2. Implement transmission/reflection analysis helpers.
3. Implement `find_peak_wavelength`.
4. Implement `generate_oled_optical_report`.

Deliverable:

- OLED/Display-flavored FDTD workflow.

---

## 14. Testing Strategy

### Unit tests

Use mocked Lumerical adapter.

Test cases:

- status returns healthy/unhealthy states
- missing `.fsp` path fails clearly
- object list parsing
- property read/write before/after record
- run directory creation
- original file preservation
- sweep produces expected case count
- CSV/summary generated

### Integration tests

Only run when Lumerical is installed and license is available.

Suggested marker:

```bash
pytest -m lumerical
```

### Safety tests

- Verify base `.fsp` checksum is unchanged after sweep.
- Verify all writes happen under `runs/`.

---

## 15. Success Metrics

MVP is successful when:

1. An agent can open a `.fsp` file and list objects without GUI inspection.
2. An agent can read and modify a property in a copied working file.
3. An agent can run at least one simulation through Lumerical.
4. An agent can extract monitor data.
5. An agent can run a 3-value parameter sweep and generate:
   - copied case files
   - `results.csv`
   - `summary.md`
6. Original `.fsp` remains unchanged.

---

## 16. Risks and Mitigations

### Risk: Lumerical API availability varies by OS/version

Mitigation:

- Adapter abstraction.
- Support `ansys-lumerical-core` first, `lumapi` fallback if needed.
- Clear status diagnostics.

### Risk: Object/property discovery is incomplete

Mitigation:

- Provide raw script execution fallback.
- Return partial results with warnings.
- Encourage project naming conventions.

### Risk: Semantic role inference is wrong

Mitigation:

- Mark inferred roles as `likely`, never certain.
- Require confirmation before mutation in interactive mode.
- Allow user-provided mapping file.

### Risk: Simulation runs are expensive/slow

Mitigation:

- Plan-first mode.
- Dry-run mode.
- Explicit run confirmation in UI/agent layer.
- Timeout controls.

---

## 17. Future Extensions

- Support Meep FDTD workflows.
- Support Tidy3D cloud simulation workflows.
- Add experiment database.
- Add DOE/optimization algorithms.
- Add automatic report comparison across `.fsp` versions.
- Add Obsidian export for simulation notes.
- Add LLM-assisted troubleshooting of source/monitor/boundary settings.
- Add company template/naming-rule validator.

---

## 18. MVP Hardening Addendum

### 18.1 Session and State Model

All stateful tools must identify their target explicitly. The server should not rely on ambiguous hidden global state when multiple projects or runs are open.

Required identifiers:

- `session_id`: Lumerical process/session handle managed by the adapter.
- `project_id`: opened `.fsp` project handle associated with a base path and session.
- `run_id`: safe run directory / experiment execution handle.
- `plan_id`: dry-run experiment plan that can be inspected before mutation/run.

Lifecycle:

1. `lumerical_status` checks availability without opening a project.
2. `open_fsp` returns `session_id` and `project_id`.
3. Read-only inspection tools require `project_id`.
4. Mutation/run tools require either `run_id` or explicit `base_fsp` plus safe-run creation.
5. Sweep tools must create or reuse a `run_id` and return artifact paths.

### 18.2 Safety and Approval Model

Default behavior for destructive or expensive operations is `dry_run=true` / plan-first.

Mutation tools must enforce:

- original `.fsp` checksum captured before copy;
- writes only under generated run directory;
- before/after value log;
- object/property existence validation;
- explicit approved changes for sweeps or batch mutations;
- clear failure when monitor/result/object/property is missing.

Suggested approved-change shape:

```json
{
  "approved_changes": [
    {
      "object_name": "ETL",
      "property_name": "z span",
      "allowed_values": [2e-8, 3e-8, 4e-8]
    }
  ]
}
```

### 18.3 Adapter Contract

Implement a stable adapter interface first, then back it with fake and real adapters.

Required adapters:

- `FakeLumericalAdapter`: deterministic in-memory project tree and monitor fixtures for unit tests and CI.
- `AnsysCoreAdapter`: primary real adapter if `ansys-lumerical-core` is available and viable.
- `LumapiAdapter`: fallback real adapter if direct `lumapi` is available.

Minimum adapter methods:

```text
status()
open_project(path, readonly=True)
list_objects(project_id)
list_properties(project_id, object_name)
get_property(project_id, object_name, property_name)
set_property(project_id, object_name, property_name, value)
run(project_id, timeout_sec)
get_monitor_result(project_id, monitor_name, result_name)
close(session_id)
```

### 18.4 Result Data Contract

Monitor extraction must return a predictable structure. If the real adapter can only provide partial metadata, return partial data with warnings rather than silently changing shape.

```json
{
  "monitor_name": "T_monitor",
  "result_name": "T",
  "axes": {
    "wavelength_m": {"values": [4.5e-7, 4.6e-7], "unit": "m"}
  },
  "values": [0.41, 0.42],
  "shape": [2],
  "metadata": {
    "project_id": "...",
    "run_id": "...",
    "source": "getresult"
  },
  "warnings": []
}
```

Recommended MVP CSV long-form columns:

```csv
run_id,case_id,object,property,value,monitor,result,wavelength_m,result_value,status
```

### 18.5 Run Directory Layout

Safe runs should use collision-resistant directories:

```text
runs/YYYYMMDD-HHMMSS_<slug>/
  base/
    original_copy.fsp
  cases/
    case_0001/
      working.fsp
      change_log.json
      run.log
    case_0002/
      working.fsp
      change_log.json
      run.log
  results/
    results.csv
    plot.png
  provenance.json
  summary.md
```

`provenance.json` must include base path, original checksum, timestamp, changed variables, tool version, adapter name, and run status.

### 18.6 Phase 0-3 Scope Contract

Phase 0 hardens this PRD and copies it into the product repo.
Phase 1 reviews the reference repo and documents baseline gaps.
Phase 2 creates an installable MCP scaffold with fake adapter and tests.
Phase 3 spikes real adapter detection and gated integration tests, without requiring Lumerical/license for normal CI.

---

## 19. Core Handoff Prompt

```text
Build `fdtd-lab-mcp`, an MCP server differentiated from existing `ansys-lumerical-mcp`. Do not build only a thin Lumerical session wrapper. Build an FDTD Experiment Agent MCP that can inspect `.fsp` files, list objects/properties, infer likely sources/monitors/layers, propose sweep candidates, safely copy projects into run directories, modify selected object properties, run simulations, extract monitor results, and export CSV/plot/summary.md.

Start by reviewing https://github.com/SheepWangZz/ansys-lumerical-mcp and documenting the baseline. Then implement Phase 0-3: hardened PRD, baseline review, Python MCP scaffold with mocked tests first, and real Lumerical adapter detection spike. Initial domain focus is OLED/Display stack optimization. Original `.fsp` files must never be overwritten.
```
