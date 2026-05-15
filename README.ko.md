# fdtd-lab-mcp

Ansys Lumerical FDTD `.fsp` 파일을 MCP 도구로 다루기 위한 서버입니다.

## 기능

- `.fsp` 파일 열기
- 프로젝트 object 목록 조회
- object property 목록 조회
- property 값 읽기/수정
- 원본 보호용 run directory 생성
- simulation 실행
- parameter sweep 실행
- monitor result 조회
- result CSV export
- blank project 생성
- 최소 FDTD authoring smoke project 생성
- 실제 Lumerical application/license 해제를 위한 project/session handle 종료 지원
- `fake`, `ansys_core`, `lumapi` adapter 지원

## Adapter

| Adapter | 설명 | 용도 |
| --- | --- | --- |
| `fake` | Lumerical 없이 동작하는 테스트 adapter | 개발/CI 기본값 |
| `ansys_core` | `ansys-lumerical-core` 기반 adapter | 실제 Lumerical 권장 |
| `lumapi` | direct `lumapi` adapter | fallback |

실제 Lumerical 작업은 safety gate가 필요합니다.

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
```

## 설치/테스트

```bash
python -m pytest
```

예상 결과:

```text
39 passed, 1 skipped
```

## MCP 서버 실행

기본 실행은 `fake` adapter입니다.

```bash
fdtd-lab-mcp
```

실제 Lumerical 환경에서 `ansys_core` 사용:

```bash
export FDTD_LAB_ADAPTER=ansys_core
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

`lumapi` fallback 사용:

```bash
export FDTD_LAB_ADAPTER=lumapi
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

## 주요 MCP Tools

### 상태/adapter

| Tool | 설명 |
| --- | --- |
| `server_info` | server/version metadata와 adapter gate 정보 확인 |
| `active_adapter` | 현재 adapter 확인 |
| `reset_state` | adapter/state 초기화 |
| `lumerical_status` | adapter 감지 상태 확인 |

### 파일/프로젝트 조회

| Tool | 설명 |
| --- | --- |
| `open_fsp` | `.fsp` 열기; 호출자가 `close_project(project_id)`로 닫아야 함 |
| `inspect_fsp` | `.fsp`를 열어 object/description을 조회한 뒤 자동 close |
| `list_objects` | object 목록 조회 |
| `list_properties` | object property 목록 조회 |
| `get_object_property` | property 값 조회 |
| `describe_project` | source/monitor/region/structure 요약 |

### 수정/실행/결과

| Tool | 설명 |
| --- | --- |
| `set_object_property` | property 값 수정 |
| `create_run_dir` | 원본 `.fsp` 복사본과 provenance 생성 |
| `propose_experiment_plan` | sweep 계획 생성 |
| `validate_experiment_plan` | sweep 계획 검증 |
| `run_parameter_sweep` | working copy에서 parameter sweep을 한 번 실행하고 내부 project 자동 close |
| `run_simulation` | simulation 실행 |
| `get_monitor_result` | monitor result 조회 |
| `export_csv` | CSV export |
| `close_project` | `project_id`로 열린 project를 닫고 Lumerical session/license 해제 |
| `close` | 기존 `session_id` 기반 close |

### Authoring

| Tool | 설명 |
| --- | --- |
| `new_project` | blank project 생성; 호출자가 `close_project(project_id)`로 닫아야 함 |
| `save_project_as` | `.fsp` 저장 |
| `add_fdtd_region` | FDTD region 추가 |
| `add_rectangle` | rectangle/structure 추가 |
| `add_dipole_source` | dipole source 추가 |
| `add_power_monitor` | power monitor 추가 |
| `delete_object` | object 삭제 |
| `create_tiny_smoke_project` | 최소 smoke `.fsp`를 생성/저장한 뒤 자동 close |
| `run_tiny_smoke_project` | smoke `.fsp`를 열어 실행/조회한 뒤 자동 close |

## Project lifecycle 계약

- `open_fsp()`와 `new_project()`는 낮은 수준의 handle 생성 API입니다. 의도적으로 project/session을 열린 상태로 두고 `project_id`를 반환하므로, 실제 Lumerical adapter에서는 GUI process와 license 해제를 위해 호출자가 작업 후 `close_project(project_id)`를 실행해야 합니다.
- 내부에서 project를 열거나 생성하는 one-shot high-level helper는 결과를 수집한 뒤 내부 project를 자동으로 닫습니다: `inspect_fsp()`, `create_tiny_smoke_project()`, `run_tiny_smoke_project()`, `run_parameter_sweep()`. 실패 시에도 원래 예외를 가리지 않고 cleanup을 시도합니다.
- `close(session_id)`는 legacy session-id cleanup 용도로 유지되지만, lifecycle API는 `close_project(project_id)`를 권장합니다.

## 기본 사용 예시

### 1. `.fsp` inspect

```python
from fdtd_lab_mcp import tools

tools.reset_state(adapter="fake")
out = tools.inspect_fsp("/path/to/sample.fsp")
print(out["objects"])
print(out["description"])
```

### 2. property 수정

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

# 실제 adapter에서는 작업 후 FDTD app/license 해제를 위해 닫습니다.
tools.close_project(project_id)
```

### 3. parameter sweep

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

### 4. tiny smoke project 생성

```python
from pathlib import Path
from fdtd_lab_mcp import tools

tools.reset_state(adapter="fake")
path = Path("/tmp/fdtd_lab_tiny.fsp")
created = tools.create_tiny_smoke_project(str(path), overwrite=True)
print(created["path"])
print([o["name"] for o in created["objects"]])
```

생성 object:

```text
FDTD
block
source
T_monitor
```

## Hermes MCP 설정 예시

```yaml
mcp_servers:
  fdtd_lab:
    command: "fdtd-lab-mcp"
    env:
      FDTD_LAB_ADAPTER: "ansys_core"
      FDTD_LAB_ENABLE_REAL_LUMERICAL: "1"
      FDTD_LAB_PREIMPORT_ANSYS_CORE: "1"
      # 필요 시:
      # ANSYSLMD_LICENSE_FILE: "1055@your-license-server"
    timeout: 3600
    connect_timeout: 600
```

## Cline 설정

예시 파일:

```text
docs/cline_mcp_setting.json
```

## Real Lumerical 검증

Detection-only:

```bash
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core
python -m fdtd_lab_mcp.integration_probe --adapter lumapi
```

실제 open/list:

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
export FDTD_LAB_SAMPLE_FSP=/path/to/non-sensitive-sample.fsp
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core --open --list
```

수동 mutation/session-close smoke:

1. 쓰기 가능한 non-sensitive project를 `open_fsp(path, readonly=False)`로 엽니다.
2. `set_object_property(project_id, "FDTD", "x span", <new span>)`를 실행합니다.
3. `run_simulation(project_id)`를 실행합니다.
4. `close_project(project_id)`를 실행합니다.
5. system tray/task manager에서 FDTD app 종료와 license 해제를 확인합니다.

Authoring smoke 검증:

```text
docs/real-authoring-smoke.md
```

## 개발 명령

```bash
python -m pytest
python -m pytest tests/test_authoring_fake.py -q
python -m compileall src tests
git diff --check
```
