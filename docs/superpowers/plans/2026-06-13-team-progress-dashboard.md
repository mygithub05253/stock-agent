# Team Progress Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 루브릭 대시보드를 2026-06-13 강사 재검토 결과와 팀원·에이전트별 실행 계획을 함께 보여주는 팀 공용 작업 현황 대시보드로 확장한다.

**Architecture:** 기존 단일 HTML/CSS/JS 구조와 시각 토큰을 유지한다. 강사 공식 점수, GitHub 기여 이력 기반 팀원 파트, 실제 코드 근거 기반 에이전트 구현도, 집중 피드백과 미배정 과제를 각각 데이터 배열로 선언하고 브라우저에서 카드로 렌더링한다.

**Tech Stack:** 정적 HTML, CSS, 바닐라 JavaScript, GitHub CLI, pytest, Codex Browser

---

### Task 1: 피드백 원문과 기준점 보존

**Files:**
- Create: `docs/feedback/2026-06-13_강사재검토리포트_93487d3.md`
- Modify: `docs/feedback/README.md`

- [ ] 새 강사 재검토 원문을 수정 없이 `docs/feedback/`에 보존한다.
- [ ] 피드백 인덱스에 공식 `32/70(D)` 재검토 결과를 추가한다.

### Task 2: 팀 공용 대시보드 확장

**Files:**
- Modify: `docs/roadmap/2026-06-12/progress_dashboard.html`

- [ ] 공식 점수 흐름을 `20/70 → 32/70 → 46/70`으로 교체한다.
- [ ] GitHub 협업자 5명의 파트 구현도와 집중 피드백을 추가한다.
- [ ] 에이전트 10개와 Graph 오케스트레이션의 구현도·근거·다음 DoD를 추가한다.
- [ ] 공식 루브릭 10항목 점수를 재검토 결과와 일치시킨다.
- [ ] P0~P3 우선순위와 미배정 과제 3개를 시각화한다.
- [ ] 에이전트 카드 상태 필터를 추가한다.

### Task 3: 검증 및 GitHub 반영

**Files:**
- Test: `docs/roadmap/2026-06-12/progress_dashboard.html`

- [ ] 필수 섹션과 공식 점수 문자열을 검사한다.
- [ ] `python -m pytest tests -q`와 `python -m compileall`을 실행한다.
- [ ] Codex Browser에서 데스크톱·모바일 렌더링, 콘솔, 필터 상호작용을 확인한다.
- [ ] 변경 파일만 스테이징하고 협업 규칙에 맞춰 커밋한다.
- [ ] PR을 생성하고 auto-merge를 활성화한 뒤 로컬 `main`을 pull한다.
