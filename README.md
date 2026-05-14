# fdtd-lab-mcp

`fdtd-lab-mcp`는 Ansys Lumerical FDTD `.fsp` 프로젝트를 MCP(Model Context Protocol) 도구로 안전하게 열람·복제·수정·실행하기 위한 실험용 서버입니다.

기본 목표는 **사내 로컬망 Lumerical 환경에서 기존 `.fsp` 파일을 안전하게 다루는 것**입니다. 개발/CI 환경에서는 Lumerical 설치나 라이선스가 없어도 테스트할 수 있도록 기본 adapter가 `fake`로 동작합니다.

## 핵심 방향

이 프로젝트는 “처음부터 완성형 업무 템플릿을 자동 생성하는 도구”가 아니라, 다음 순서로 안정성을 쌓는 것을 목표로 합니다.

1. 기존 `.fsp` 파일을 안전하게 열고 구조를 파악한다.
2. 원본을 직접 훼손하지 않고 run directory에 복사해서 실험한다.
3. object/property를 조회하고 제한적으로 수정한다.
4. parameter sweep, simulation run, monitor result export를 수행한다.
5. 필요한 경우에만 최소 CAD authoring primitive로 blank project와 smoke fixture를 만든다.

즉, 현재 authoring 기능은 업무용 OLED/FDTD 템플릿이 아니라 **Lumerical API 연결, 저장, inspect, run 경로를 검증하기 위한 최소 배관**입니다.

## Adapter 구조

지원 adapter는 다음과 같습니다.

| Adapter | 용도 | 라이선스 필요 여부 |
| --- | --- | --- |
| `fake` | 개발/CI용 deterministic adapter | 불필요 |
| `ansys_core` | `ansys-lumerical-core` 기반 실제 Lumerical adapter | 필요 |
| `lumapi` | direct `lumapi` fallback adapter | 필요 |

우선순위는 다음과 같습니다.

1. `ansys_core`
2. `lumapi`
3. `fake`는 개발/테스트 기본값

실제 Lumerical 작업은 항상 명시적 안전 게이트가 필요합니다.

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
```

이 값이 없으면 real adapter의 open/run/new project 계열 작업은 실행되지 않습니다. 이는 실수로 사내 라이선스를 소비하거나 실제 프로젝트를 변형하는 일을 막기 위한 장치입니다.

## 빠른 테스트

개발/CI 기본 검증은 Lumerical 없이 실행됩니다.

```bash
python -m pytest
```

현재 기대 결과 예시:

```text
25 passed, 1 skipped
```

## MCP 서버 실행

기본 실행은 `fake` adapter입니다.

```bash
fdtd-lab-mcp
```

실제 사내 Lumerical 환경에서 `ansys_core`를 사용할 때:

```bash
export FDTD_LAB_ADAPTER=ansys_core
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

`ansys-lumerical-core`가 해당 환경에서 동작하지 않으면 direct `lumapi` fallback을 사용할 수 있습니다.

```bash
export FDTD_LAB_ADAPTER=lumapi
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
fdtd-lab-mcp
```

## import_core 지연 대응

사내 환경에서 `ansys.lumerical.core` import가 오래 걸리면, 첫 `open_fsp` tool call이 timeout될 수 있습니다.

이를 줄이기 위해 MCP 서버는 기본적으로 startup 시점에 `ansys.lumerical.core`를 pre-import합니다.

```bash
export FDTD_LAB_PREIMPORT_ANSYS_CORE=1
```

기본값은 enabled입니다. 비활성화하려면:

```bash
export FDTD_LAB_PREIMPORT_ANSYS_CORE=0
```

의도는 다음과 같습니다.

- 느린 import 비용을 첫 tool call 내부가 아니라 MCP server startup 단계로 이동
- Cline/Hermes 같은 client에서 startup timeout을 길게 잡아 대응 가능
- 첫 `open_fsp` 호출 timeout 가능성 감소

## 제공 MCP tool 개요

### 상태/adapter 관리

| Tool | 설명 |
| --- | --- |
| `active_adapter` | 현재 adapter와 환경 기본값 확인 |
| `reset_state` | in-memory 상태 초기화 및 adapter 선택 |
| `lumerical_status` | fake/real adapter 감지 상태 확인 |

### 기존 `.fsp` 열람/수정

| Tool | 설명 |
| --- | --- |
| `open_fsp` | `.fsp` 파일 열기 |
| `inspect_fsp` | 파일 열기 + object list + project description 반환 |
| `list_objects` | 현재 project object 목록 조회 |
| `list_properties` | object의 property 목록 조회 |
| `get_object_property` | object property 값 조회 |
| `set_object_property` | object property 값 수정 |
| `describe_project` | source/monitor/simulation region/structure 후보 요약 |

### 안전한 실험/run 관리

| Tool | 설명 |
| --- | --- |
| `create_run_dir` | 원본 `.fsp`를 run directory로 복사하고 provenance 생성 |
| `propose_experiment_plan` | parameter sweep dry-run 계획 생성 |
| `validate_experiment_plan` | sweep 계획 검증 |
| `run_parameter_sweep` | 승인된 값 범위 내 parameter sweep 실행 |
| `run_simulation` | simulation 실행 |
| `get_monitor_result` | monitor result 조회 |
| `export_csv` | result row를 CSV로 저장 |

### Phase A: 최소 authoring primitive

다음 tool은 blank project와 최소 CAD primitive 생성을 위한 기능입니다.

| Tool | 설명 |
| --- | --- |
| `new_project` | 빈 FDTD project session 생성 |
| `save_project_as` | project를 `.fsp`로 저장 |
| `add_fdtd_region` | FDTD simulation region 추가 |
| `add_rectangle` | rectangle/structure object 추가 |
| `add_dipole_source` | dipole source 추가 |
| `add_power_monitor` | power monitor 추가 |
| `delete_object` | object 삭제 |

주의사항:

- 이 기능은 업무 템플릿 생성기가 아닙니다.
- object name에는 quote, semicolon, newline 등 script injection 위험 문자를 허용하지 않습니다.
- `.fsp` 저장 경로만 허용합니다.
- `overwrite=True`를 명시하지 않으면 기존 파일을 덮어쓰지 않습니다.
- arbitrary Lumerical script executor는 제공하지 않습니다.

### Phase B: tiny smoke project

| Tool | 설명 |
| --- | --- |
| `create_tiny_smoke_project` | 최소 FDTD/source/monitor/structure로 smoke `.fsp` 생성 |
| `run_tiny_smoke_project` | smoke `.fsp`를 열고 run/result 경로 검증 |

`create_tiny_smoke_project`가 만드는 object는 다음과 같습니다.

```text
FDTD
block
source
T_monitor
```

이 tiny project는 다음을 검증하기 위한 fixture입니다.

- blank project 생성
- primitive object 추가
- `.fsp` 저장
- object list/description 조회
- 선택적 run/result 경로 확인

중요: 이 tiny smoke project는 **production OLED/FDTD template이 아닙니다.** 실제 업무용 stack, material, source, monitor, boundary, mesh 조건은 사내 실제 `.fsp` 샘플을 기준으로 나중에 recipe를 추출해서 다루는 것이 맞습니다.

## Python에서 직접 smoke 확인 예시

Lumerical 없이 fake adapter로 확인:

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

실제 Lumerical 환경에서 확인하는 절차는 다음 문서에 정리되어 있습니다.

```text
docs/real-authoring-smoke.md
```

## Real integration probe

사내 로컬망 Lumerical 검증 문서는 다음을 참고합니다.

```text
docs/company-local-integration.md
```

Detection-only 예시:

```bash
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core
python -m fdtd_lab_mcp.integration_probe --adapter lumapi
```

실제 open/list 검증은 명시적 safety gate와 non-sensitive sample `.fsp`가 필요합니다.

```bash
export FDTD_LAB_ENABLE_REAL_LUMERICAL=1
export FDTD_LAB_SAMPLE_FSP=/path/to/non-sensitive-sample.fsp
python -m fdtd_lab_mcp.integration_probe --adapter ansys_core --open --list
```

## Hermes MCP 설정 예시

```yaml
mcp_servers:
  fdtd_lab:
    command: "fdtd-lab-mcp"
    env:
      FDTD_LAB_ADAPTER: "ansys_core"
      FDTD_LAB_ENABLE_REAL_LUMERICAL: "1"
      FDTD_LAB_SAMPLE_FSP: "/path/to/non-sensitive-sample.fsp"
      FDTD_LAB_PREIMPORT_ANSYS_CORE: "1"
      # 사내 license setup에 필요하면:
      # ANSYSLMD_LICENSE_FILE: "1055@your-license-server"
    timeout: 3600
    connect_timeout: 600
```

## Cline MCP 설정 예시

Cline용 예시는 다음 파일을 참고합니다.

```text
docs/cline_mcp_setting.json
```

이 설정은 다음 목적을 가집니다.

- MCP timeout을 길게 설정
- `FDTD_LAB_ADAPTER=ansys_core` 선택
- `FDTD_LAB_ENABLE_REAL_LUMERICAL=1` 명시
- `FDTD_LAB_PREIMPORT_ANSYS_CORE=1`로 느린 import를 server startup에서 처리

## 안전 정책

이 프로젝트의 기본 안전 정책은 다음과 같습니다.

1. 개발/CI 기본값은 항상 `fake` adapter입니다.
2. real adapter는 `FDTD_LAB_ENABLE_REAL_LUMERICAL=1` 없이는 실제 open/run/new project를 수행하지 않습니다.
3. 기존 `.fsp` 기반 실험은 원본을 직접 수정하지 않고 run directory 복사본을 사용합니다.
4. parameter sweep은 dry-run plan과 approved values 개념을 유지합니다.
5. authoring primitive는 최소 기능만 제공하며 arbitrary script execution은 노출하지 않습니다.
6. tiny smoke project는 업무 템플릿이 아니라 배관 검증용 fixture입니다.

## 개발자가 자주 확인할 명령

```bash
# 전체 테스트
python -m pytest

# authoring/smoke fake 테스트만
python -m pytest tests/test_authoring_fake.py -q

# syntax/bytecode sanity check
python -m compileall src tests

# git whitespace check
git diff --check
```

## 현재 구현 범위와 비범위

현재 구현된 것:

- 기존 `.fsp` inspect/modify/run/sweep/export
- real adapter detection 및 safety gate
- `ansys_core` import pre-warm
- 최소 authoring primitive
- tiny smoke project 생성/run fixture
- fake adapter 기반 CI 테스트

아직 의도적으로 하지 않는 것:

- production OLED stack template 생성
- display pixel/cavity 등 도메인 템플릿 생성
- arbitrary Lumerical script executor 노출
- 실제 사내 material DB/mesh/boundary/source convention 임의 정의

향후 실제 사내 `.fsp` 샘플이 확보되면, 임의 템플릿보다 다음 방향이 적합합니다.

- `extract_project_recipe`
- `clone_project_with_changes`
- `compare_project_structure`
- `apply_property_patch`

즉, 실전 확장은 “상상한 템플릿”이 아니라 **검증된 실제 project에서 recipe를 추출하고 안전하게 변형하는 방식**으로 가는 것이 이 프로젝트의 방향입니다.
