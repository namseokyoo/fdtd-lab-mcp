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

```bash
fdtd-lab-mcp
```
