# fdtd-lab-mcp

FDTD Experiment Agent MCP for safe Ansys Lumerical `.fsp` workflows. The intended deployment target is a company local-network environment. Adapter priority is `ansys-lumerical-core` first, with direct `lumapi` as fallback. The MVP uses a deterministic fake adapter by default so development and CI do not require a Lumerical license. Real adapter detection is lazy and gated.

## Quick test

```bash
python -m pytest
```

## MCP server

```bash
fdtd-lab-mcp
```
