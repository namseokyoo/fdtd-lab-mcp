# ansys-lumerical-mcp Baseline Review

Reviewed reference: `SheepWangZz/ansys-lumerical-mcp` cloned under `references/ansys-lumerical-mcp`.

## Summary

The reference project is a useful MCP/session-control baseline, but it intentionally stays at a generic Lumerical remote-control layer. It does not implement FDTD experiment management, project inspection semantics, safe copied run directories, sweep provenance, OLED/display helpers, or result reporting.

## Package and server shape

- Python package name: `ansys-lumerical-mcp`
- Source package: `src/ansys_lumerical_mcp`
- MCP implementation: `mcp.server.fastmcp.FastMCP`
- Runtime dependency: `ansys-lumerical-core>=0.2.0`, `mcp>=1.27.0`
- CLI entrypoint: `ansys-lumerical-mcp = ansys_lumerical_mcp.server:main`

## Implemented tools

The server registers these tools:

1. `lumerical_status`
2. `list_available_products`
3. `open_session`
4. `list_sessions`
5. `close_session`
6. `run_script`
7. `put_variable`
8. `get_variable`

## Important implementation details

- Product class map: `fdtd -> FDTD`, `mode -> MODE`, `interconnect -> INTERCONNECT`, `device -> DEVICE`.
- Status checks lazily import `ansys.lumerical.core` and expose package/install path diagnostics.
- Optional environment variables:
  - `LUMERICAL_MCP_INSTALL_DIR`
  - `LUMERICAL_INSTALL_DIR`
- Sessions are process-local in `_SESSIONS` with UUID `session_id`.
- Long script execution supports optional timeout via `ThreadPoolExecutor`.
- JSON conversion handles numpy arrays/scalars.

## Gaps versus fdtd-lab-mcp PRD

| Area | Reference | fdtd-lab-mcp need |
| --- | --- | --- |
| Project inspection | none beyond opening a project | list objects, properties, sources, monitors, materials |
| Semantics | none | likely OLED stack roles and sweep candidates |
| Safe mutation | generic scripts/variables only | copy `.fsp`, never overwrite original, before/after logs |
| Run management | none | collision-resistant run directories and provenance |
| Sweep workflow | none | case folders, approved changes, CSV/summary/plot |
| Result contract | raw variable read only | monitor result schema and CSV shape |
| Test strategy | server/tool basics | FakeLumericalAdapter for CI plus gated real integration |
| Domain pack | none | OLED/display helpers |

## Reusable patterns

- Use `FastMCP` server scaffold and explicit tool registration.
- Lazy-import Lumerical packages so status tools work even without local installation.
- Keep real Lumerical session calls behind adapter methods.
- Return clear validation errors for missing files, unsupported products, busy sessions, and import failures.
- Convert numpy outputs to JSON-safe values before returning MCP responses.

## Design decision for fdtd-lab-mcp

`fdtd-lab-mcp` should not fork the reference architecture blindly. It should borrow the MCP server/entrypoint style and lazy status diagnostics, but place all Lumerical operations behind the PRD adapter contract:

- `FakeLumericalAdapter` for deterministic unit tests.
- `AnsysCoreAdapter` as first real adapter candidate.
- `LumapiAdapter` as fallback candidate.

The product-level tools should expose experiment semantics (`inspect_fsp`, `propose_experiment_plan`, `run_parameter_sweep`) rather than only low-level session controls.
