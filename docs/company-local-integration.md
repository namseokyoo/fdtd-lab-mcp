# Company Local-Network Lumerical Integration Guide

This project is intended to run inside the company local-network environment where Ansys Lumerical and its license are available.

## Adapter priority

1. `ansys-lumerical-core` (`ansys_core` adapter)
2. direct `lumapi` (`lumapi` adapter) fallback

## Safety gate

Real Lumerical operations are disabled unless explicitly enabled:

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
```

Normal tests and MCP use remain fake-adapter safe by default.

## Detection only

```bash
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core
python -m fdtd_lab_mcp.integration_probe --adapter lumapi
```

## First real open/list smoke

Use a non-sensitive sample `.fsp` copied to a safe local path.

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
export FDTD_LAB_SAMPLE_FSP=/path/to/non-sensitive-sample.fsp
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core --fsp "$FDTD_LAB_SAMPLE_FSP" --open --list
```

If `ansys_core` cannot import/open/list, try fallback:

```bash
python -m fdtd_lab_mcp.integration_probe --adapter lumapi --fsp "$FDTD_LAB_SAMPLE_FSP" --open --list
```

## Gated integration tests

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
export FDTD_LAB_ADAPTER=ansys_core
export FDTD_LAB_SAMPLE_FSP=/path/to/non-sensitive-sample.fsp
python -m pytest -m lumerical
```

## Stop conditions

Stop and report instead of guessing if:

- imports work but opening consumes license unexpectedly or hangs;
- object listing script fails because the company Lumerical version has different tree APIs;
- object/property names are not discoverable through scripts;
- sample `.fsp` contains sensitive project data that should not be copied into repo/logs;
- monitor result shape differs from the current normalized schema.
