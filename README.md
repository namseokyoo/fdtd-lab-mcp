# fdtd-lab-mcp

FDTD Experiment Agent MCP for safe Ansys Lumerical `.fsp` workflows. The intended deployment target is a company local-network environment. Adapter priority is `ansys-lumerical-core` first, with direct `lumapi` as fallback. The MVP uses a deterministic fake adapter by default so development and CI do not require a Lumerical license. Real adapter detection is lazy and gated.

## Quick test

```bash
python -m pytest
```

## Real integration probe

Company local-network Lumerical validation is documented in `docs/company-local-integration.md`.

Detection-only examples:

```bash
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core
python -m fdtd_lab_mcp.integration_probe --adapter lumapi
```

Real open/list requires an explicit safety gate and a non-sensitive sample `.fsp`:

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
export FDTD_LAB_SAMPLE_FSP=/path/to/non-sensitive-sample.fsp
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core --open --list
```

## MCP server

By default the MCP server starts in deterministic `fake` mode so CI and normal
development do not consume a company Lumerical license.

```bash
fdtd-lab-mcp
```

For company local-network use with a real Lumerical license, start the MCP server
with both an adapter selection and the explicit safety gate:

```bash
export FDTD_LAB_ADAPTER=ansys_core
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
export FDTD_LAB_SAMPLE_FSP=/path/to/non-sensitive-sample.fsp
fdtd-lab-mcp
```

If `ansys-lumerical-core` is unavailable in the local environment, use the direct
`lumapi` fallback instead:

```bash
export FDTD_LAB_ADAPTER=lumapi
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

The MCP server exposes `active_adapter` and `reset_state` tools. Use
`active_adapter` to verify the server is actually running with `ansys_core` or
`lumapi`; use `reset_state(adapter="ansys_core")` only when deliberately switching
an already-running server session. Real open/run operations still require
`FDTD_LAB_ENABLE_REAL_LUMERICAL=1`.

### Hermes MCP configuration example

```yaml
mcp_servers:
  fdtd_lab:
    command: "fdtd-lab-mcp"
    env:
      FDTD_LAB_ADAPTER: "ansys_core"
      FDTD_LAB_ENABLE_REAL_LUMERICAL: "1"
      FDTD_LAB_SAMPLE_FSP: "/path/to/non-sensitive-sample.fsp"
      # If required by the company license setup:
      # ANSYSLMD_LICENSE_FILE: "1055@your-license-server"
    timeout: 3600
    connect_timeout: 60
```
