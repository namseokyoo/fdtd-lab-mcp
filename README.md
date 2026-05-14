# fdtd-lab-mcp

FDTD Experiment Agent MCP for safe Ansys Lumerical `.fsp` workflows.

Ansys Lumerical FDTD `.fsp` 프로젝트를 MCP(Model Context Protocol) 도구로 안전하게 열람·복제·수정·실행하기 위한 실험용 서버입니다.

## Language / 언어

- [한국어 README](README.ko.md)
- [English README](README.en.md)

## Short summary / 짧은 요약

`fdtd-lab-mcp` is designed for a company local-network Lumerical environment. It starts in a deterministic `fake` adapter by default so development and CI do not require a Lumerical license. Real adapters (`ansys_core`, `lumapi`) are explicitly gated by `FDTD_LAB_ENABLE_REAL_LUMERICAL=1`.

`fdtd-lab-mcp`는 사내 로컬망 Lumerical 환경을 목표로 합니다. 개발/CI에서는 Lumerical 라이선스가 필요 없도록 기본값이 deterministic `fake` adapter이며, 실제 adapter(`ansys_core`, `lumapi`)는 `FDTD_LAB_ENABLE_REAL_LUMERICAL=1` 안전 게이트가 있어야 동작합니다.

Current scope:

- Safe inspection and modification of existing `.fsp` files
- Run directory creation and provenance tracking
- Parameter sweep / simulation / monitor result export
- Minimal Phase A authoring primitives
- Phase B tiny smoke project fixture for authoring/save/inspect/run plumbing

현재 범위:

- 기존 `.fsp` 파일의 안전한 inspect/modify
- run directory 생성 및 provenance 추적
- parameter sweep / simulation / monitor result export
- Phase A 최소 authoring primitive
- Phase B authoring/save/inspect/run 배관 검증용 tiny smoke project fixture

## Quick test / 빠른 테스트

```bash
python -m pytest
```

Expected result / 기대 결과:

```text
25 passed, 1 skipped
```

## Real adapter safety gate / 실제 adapter 안전 게이트

```bash
export FDTD_LAB_ADAPTER=ansys_core
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

Fallback:

```bash
export FDTD_LAB_ADAPTER=lumapi
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

For full documentation, choose a language above.

전체 문서는 위 언어별 README를 참고하세요.
