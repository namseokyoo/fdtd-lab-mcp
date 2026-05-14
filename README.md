# fdtd-lab-mcp

An MCP server for Ansys Lumerical FDTD `.fsp` workflows.

Ansys Lumerical FDTD `.fsp` 파일을 열고, 구조를 조회하고, 값을 수정하고, 실행/스윕/결과 추출을 수행하는 MCP 서버입니다.

## Language / 언어

- [한국어](README.ko.md)
- [English](README.en.md)

## Features / 기능

- Open and inspect `.fsp` files
- List objects and properties
- Read/write object properties
- Create safe run directories
- Run simulations and parameter sweeps
- Export monitor results to CSV
- Create minimal FDTD authoring smoke projects
- Support `fake`, `ansys_core`, and `lumapi` adapters

## Quick start / 빠른 시작

```bash
python -m pytest
```

```bash
fdtd-lab-mcp
```

Real Lumerical adapter:

```bash
export FDTD_LAB_ADAPTER=ansys_core
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

Fallback adapter:

```bash
export FDTD_LAB_ADAPTER=lumapi
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```
