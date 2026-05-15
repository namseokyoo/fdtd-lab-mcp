# FDTD Lab MCP Homepage Portfolio Plan

> **For Hermes/Core:** 계획 문서다. 구현 전에 홈페이지 레포/배포 경계 확인, 민감정보 제거, 독립 리뷰 1회 후 반영한다.

**Goal:** `fdtd-lab-mcp`를 형 개인/랩 홈페이지에 포트폴리오 항목으로 올려, 랩의 AI 운영·연구 자동화 역량을 보여준다.

**Architecture:** 홈페이지에는 완성 제품이 아니라 “진행 중인 기술 포트폴리오 / internal tooling project”로 배치한다. 상세 페이지 또는 프로젝트 카드 1개를 만들고, README 기반 기능·아키텍처·현황·다음 마일스톤을 공개 가능한 범위로 재서술한다. 회사 내부망, 실제 회사 데이터, 라이선스 서버, 민감한 `.fsp` 파일 경로/구조는 노출하지 않는다.

**Tech Stack:** 현재 프로젝트는 Python MCP server, Ansys Lumerical FDTD, `ansys-lumerical-core`, `lumapi` fallback, fake adapter/CI 테스트 구조. 홈페이지 스택은 미확인 상태라 구현 전 별도 확인 필요.

---

## 1. 포트폴리오 포지셔닝

### 표시 이름 후보
- **FDTD Lab MCP**
- **AI-assisted FDTD Automation MCP**
- **Lumerical FDTD Automation Adapter for AI Agents**

### 한 줄 소개
> AI 에이전트가 Ansys Lumerical FDTD 프로젝트를 안전하게 열람·수정·실행·결과 추출할 수 있도록 설계한 MCP 서버/어댑터 프로젝트.

### 홈페이지 카드용 짧은 설명
> FDTD 시뮬레이션 워크플로우를 MCP 도구로 추상화해, AI 에이전트가 `.fsp` 프로젝트 inspect, property 수정, run directory 생성, parameter sweep, monitor result 조회, CSV export까지 수행할 수 있도록 만든 연구 자동화 인프라입니다. 현재는 fake adapter 기반 CI와 `ansys-lumerical-core`/`lumapi` 실제 연동 경로를 분리해 안정화 중입니다.

### 공개 상태 라벨
- 권장: **In Progress / Internal Tooling / Research Automation**
- 피해야 함: “상용 완성”, “회사 적용 완료”, “사내망 배포 완료”처럼 검증 전 과장 표현

---

## 2. 공개 가능한 핵심 메시지

1. **전문 시뮬레이션 툴을 AI 에이전트가 다룰 수 있게 하는 MCP화**
   - 단순 챗봇이 아니라 domain tool을 안전한 API로 감싸는 작업.

2. **안전한 실험 실행 구조**
   - 원본 `.fsp` 보호를 위한 run directory 생성.
   - real Lumerical 작업은 explicit safety gate 필요.

3. **Adapter 분리**
   - `fake`: Lumerical 없이 개발/CI 테스트.
   - `ansys_core`: 실제 Lumerical 권장 경로.
   - `lumapi`: direct fallback.

4. **실험 자동화 흐름**
   - inspect → property 변경 → sweep plan → validation → simulation → result export.

5. **현재 안정화 포인트**
   - core/import 로딩 지연과 timeout handling 개선.
   - 실제 Lumerical 환경의 connect timeout, preload, adapter readiness 개선.

---

## 3. 포함할 섹션 구조

### A. Project Card
- Title: `FDTD Lab MCP`
- Tags: `MCP`, `AI Agents`, `FDTD`, `Lumerical`, `Research Automation`, `Python`
- Status: `In Progress`
- CTA: `View case study` 또는 `Technical notes`

### B. Case Study 상세 페이지
1. **Problem**
   - FDTD 시뮬레이션은 반복 설정·실행·결과 수집이 많고, AI 에이전트가 직접 다루기 어렵다.
2. **Approach**
   - Lumerical 작업을 MCP tools로 추상화하고, fake/real adapter를 분리한다.
3. **Capabilities**
   - `.fsp` open/inspect
   - object/property list
   - property get/set
   - run directory 생성
   - simulation / parameter sweep
   - monitor result / CSV export
   - minimal smoke project authoring
4. **Safety & Reliability**
   - 원본 보호
   - real adapter safety gate
   - timeout/connect timeout 설정
   - fake adapter 기반 테스트
5. **Current Status**
   - README 기준 기능 구현됨.
   - 로딩/지연 이슈 1차 수정 완료 전제로, 홈페이지에는 “stabilizing real-adapter startup and timeout behavior”로 표기.
6. **Next Milestones**
   - real Lumerical smoke evidence 정리
   - timeout regression test 추가
   - 홈페이지용 아키텍처 다이어그램 추가
   - 공개 가능한 demo log 또는 synthetic screenshot 추가

---

## 4. 민감정보 제거 규칙

홈페이지에 절대 올리지 않을 것:
- 회사명/부서명/내부 프로젝트명/실제 제품명
- 사내망 주소, 라이선스 서버 주소, 계정명
- 실제 `.fsp` 파일명·경로·설계 구조
- 회사 데이터 기반 결과 그래프
- 내부 보안 정책을 암시하는 구체 정보

대체 표현:
- “enterprise/local-network research environment”
- “licensed simulation environment”
- “synthetic smoke project”
- “representative FDTD workflow”

---

## 5. 구현 전 확인할 경계

- [ ] 홈페이지 레포 위치 확인
- [ ] 홈페이지 배포 방식 확인
- [ ] `projects/fdtd-lab-mcp`와 홈페이지 레포가 별도인지 확인
- [ ] 포트폴리오 데이터가 markdown/content collection인지, React component 직접 수정인지 확인
- [ ] 이미지/다이어그램 asset 저장 경로 확인
- [ ] 공개 링크를 GitHub repo로 연결할지, 현재는 private/internal로 둘지 결정

---

## 6. 구현 작업 단위

### Task 1: 홈페이지 레포/콘텐츠 구조 파악
**Objective:** 실제 수정할 파일 경계를 확정한다.

**Steps:**
1. 홈페이지 레포 root 확인.
2. 포트폴리오/프로젝트 카드가 저장되는 파일 확인.
3. 상세 페이지 라우팅 방식 확인.
4. asset 저장 위치 확인.

**Output:** 수정 대상 파일 목록.

### Task 2: 공개 가능한 프로젝트 카피 작성
**Objective:** 홈페이지 카드와 상세 페이지 문구를 확정한다.

**Draft:**
- 카드 제목: `FDTD Lab MCP`
- 카드 설명: 위 “홈페이지 카드용 짧은 설명” 사용.
- 상세 페이지: Problem / Approach / Capabilities / Safety / Status / Roadmap.

**Output:** 한국어 우선, 필요 시 영어 병기.

### Task 3: 아키텍처 다이어그램 제작
**Objective:** 기술 가치가 한눈에 보이게 한다.

**Recommended diagram:**
```text
AI Agent / Hermes / Cline
        ↓ MCP
FDTD Lab MCP Server
        ↓ adapter layer
fake adapter ─ ansys-lumerical-core ─ lumapi fallback
        ↓
FDTD project / run directory / results CSV
```

**Output:** 홈페이지 asset용 SVG/PNG 또는 inline diagram.

### Task 4: 프로젝트 상세 페이지 추가
**Objective:** 포트폴리오 항목을 실제 홈페이지에 노출한다.

**Scope in:**
- 프로젝트 카드 1개
- 상세 페이지 1개
- 공개 가능한 설명/다이어그램

**Scope out:**
- 실제 Lumerical 실행 demo 공개
- 회사/사내 환경 정보 공개
- 과장된 성과 수치 작성

### Task 5: 검수
**Objective:** 포트폴리오로서 충분히 매력적이고, 민감정보가 없는지 확인한다.

**Verification:**
1. 로컬 홈페이지 실행.
2. 포트폴리오 카드 노출 확인.
3. 상세 페이지 링크 확인.
4. 모바일 폭에서 레이아웃 확인.
5. 민감정보 키워드 검색.
6. 문구가 “진행 중 프로젝트”로 정확히 표현되는지 확인.

---

## 7. LAB_TASK_BRIEF

- Goal: `fdtd-lab-mcp`를 홈페이지 포트폴리오 항목으로 공개 가능한 수준에서 제시한다.
- Success criteria:
  - 홈페이지에 프로젝트 카드/상세 설명이 추가된다.
  - FDTD/Lumerical/MCP/AI agent 자동화 가치가 10초 안에 이해된다.
  - 민감정보가 노출되지 않는다.
  - 현재 상태가 “진행 중/안정화 중”으로 정확히 표현된다.
- Scope in:
  - 카드 문구, 상세 페이지, 아키텍처 다이어그램, 공개 가능한 기술 설명.
- Scope out:
  - 실제 사내 데이터, 회사명, 내부망 정보, 라이선스 정보, 과장 성과.
- Repo/deploy boundary:
  - lab_repo: `/Volumes/external/project/SidequestLab/projects/fdtd-lab-mcp`
  - homepage_repo: `[OPEN] 구현 전 확인 필요`
  - deploy/tracking boundary: `[OPEN] 홈페이지 레포 확인 필요`
  - ignored paths: `[OPEN] 홈페이지 레포 확인 후 확인`
- Inputs/references:
  - `/Volumes/external/project/SidequestLab/projects/fdtd-lab-mcp/README.ko.md`
  - `/Volumes/external/project/SidequestLab/projects/fdtd-lab-mcp/README.en.md`
  - `/Volumes/external/project/SidequestLab/projects/fdtd-lab-mcp/docs/real-authoring-smoke.md`
- Non-negotiables:
  - 민감정보 비공개.
  - 완성 제품처럼 과장하지 않기.
  - 로딩/timeout 안정화는 현재 진행 중 상태로 표현.
- Output/artifact:
  - 홈페이지 PR 또는 수정 파일 diff.
  - 가능하면 아키텍처 다이어그램 asset.
- Verification plan:
  - 로컬 실행 screenshot.
  - 카드/상세 페이지 링크 확인.
  - 민감정보 검색.
  - 모바일 레이아웃 확인.
- Stop conditions:
  - 홈페이지 레포/배포 경계를 찾지 못하면 중단 후 Core에 보고.
  - 공개해도 되는 범위가 애매한 기술 세부사항 발견 시 중단.
  - 실제 회사/사내 환경 정보가 필요한 문구가 생기면 대체 표현으로 재작성.

---

## 8. 추천 최종 카피 초안

### Korean
**FDTD Lab MCP**  
AI 에이전트가 Ansys Lumerical FDTD 워크플로우를 안전하게 다룰 수 있도록 만든 MCP 서버입니다. `.fsp` 프로젝트 inspect, object/property 조회와 수정, 원본 보호용 run directory 생성, parameter sweep, simulation 실행, monitor result 조회, CSV export를 하나의 자동화 흐름으로 연결합니다. 현재는 fake adapter 기반 테스트와 실제 Lumerical adapter 안정화를 병행하며, 로컬/내부망 연구 환경에서의 AI-assisted simulation workflow를 목표로 개발 중입니다.

### English
**FDTD Lab MCP**  
An MCP server that enables AI agents to safely operate Ansys Lumerical FDTD workflows. It abstracts `.fsp` inspection, object/property access, protected run-directory creation, parameter sweeps, simulation execution, monitor result retrieval, and CSV export into agent-callable tools. The project is currently stabilizing real-adapter startup and timeout behavior while maintaining a fake adapter for development and CI.
