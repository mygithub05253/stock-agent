"""Competitor peer 비교 품질 회귀 평가 하네스.

`peer_tool`의 peer 선정·상대위치 점수 엔진(`select_peer_rows`·`calculate_relative_position`)은
DB·LLM 없이 입력만으로 결정되는 **순수 함수**다. 이 하네스는 고정된 peer 비교 시나리오
(`eval/competitor_golden/cases.json`)를 그 엔진에 그대로 흘려, 출력(선정 peer 순서·종합 score·
핵심 데이터 품질 플래그)이 기대 스냅샷과 일치하는지 검사한다. LLM judge·네트워크·과금이 전혀
없으므로 CI에서 매번 돌려 peer 비교 "품질 회귀"를 차단할 수 있다.

검사 대상(케이스별 `expect`):
- `selected`        : 선정된 peer stock_code의 **정렬 순서**(복합 유사도 #62 회귀 고정)
- `score`           : 종합 score(0~100, 결정적 스냅샷)
- `must_have_flags` : 반드시 존재해야 하는 data_quality_flag(예: peer_count_below_minimum)
- `must_not_have_flags` : 존재하면 안 되는 flag
- `peer_outlier_flags`  : 선정 peer들의 metric_flags에 존재해야 하는 outlier_* 플래그

실행 예시:
    python eval/run_competitor_eval.py            # 비교 모드(불일치 시 exit 1)
    python eval/run_competitor_eval.py --update    # 현재 엔진 출력을 기대 스냅샷으로 재기록(베이스라인)
    python eval/run_competitor_eval.py --quiet      # 요약만 출력
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

EVAL_DIR = Path(__file__).resolve().parent
GOLDEN_DIR = EVAL_DIR / "competitor_golden"
CASES_PATH = GOLDEN_DIR / "cases.json"
REPORTS_DIR = EVAL_DIR / "reports"

# eval/ 을 레포 루트에서 바로 실행해도 src 레이아웃 패키지를 찾도록 경로 주입
SRC_DIR = EVAL_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@dataclass
class CaseOutcome:
    case_id: str
    description: str
    selected: list[str]
    score: int
    data_quality_flags: list[str]
    peer_outlier_flags: list[str]
    relative_position: dict[str, Any]
    expect: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


def _build_rows(case: dict[str, Any]):
    """케이스 dict의 target/peers를 PeerMetricRow 목록으로 만든다(target이 첫 행)."""
    from stock_agent.tools.peer_tool import PeerMetricRow

    target = PeerMetricRow(**case["target"])
    peers = [PeerMetricRow(**row) for row in case["peers"]]
    return target, peers


def evaluate_case(case: dict[str, Any]) -> CaseOutcome:
    """build_peer_comparison의 핵심 경로(outlier 표기→peer 선정→상대위치)를 DB 없이 재현한다."""
    from stock_agent.tools.peer_tool import (
        _mark_outliers,
        calculate_relative_position,
        select_peer_rows,
    )

    target, peers = _build_rows(case)
    max_peer_count = case.get("max_peer_count", 8)

    rows = [target, *peers]
    rows = _mark_outliers(rows, target.stock_code)
    target_row = next(r for r in rows if r.stock_code == target.stock_code)
    selected = select_peer_rows(target_row, rows, max_peer_count=max_peer_count)
    position = calculate_relative_position([target_row, *selected], target_row.stock_code)

    peer_outlier_flags = sorted(
        {flag for row in selected for flag in row.metric_flags if flag.startswith("outlier_")}
    )

    return CaseOutcome(
        case_id=case["case_id"],
        description=case.get("description", ""),
        selected=[row.stock_code for row in selected],
        score=position.score,
        data_quality_flags=list(position.data_quality_flags),
        peer_outlier_flags=peer_outlier_flags,
        relative_position=position.relative_position,
        expect=case.get("expect", {}),
    )


def _check(outcome: CaseOutcome) -> None:
    expect = outcome.expect
    if not expect:
        outcome.failures.append("기대 스냅샷(expect)이 비어 있습니다. --update로 베이스라인을 만드세요.")
        return

    if "selected" in expect and outcome.selected != expect["selected"]:
        outcome.failures.append(
            f"선정 peer 순서 불일치: 실제 {outcome.selected} != 기대 {expect['selected']}"
        )
    if "selected_first" in expect:
        first = outcome.selected[0] if outcome.selected else None
        if first != expect["selected_first"]:
            outcome.failures.append(
                f"최우선 peer 불일치: 실제 {first} != 기대 {expect['selected_first']}"
            )
    if "score" in expect and outcome.score != expect["score"]:
        outcome.failures.append(f"score 불일치: 실제 {outcome.score} != 기대 {expect['score']}")
    for flag in expect.get("must_have_flags", []):
        if flag not in outcome.data_quality_flags:
            outcome.failures.append(f"필수 flag 누락: {flag} (실제 {outcome.data_quality_flags})")
    for flag in expect.get("must_not_have_flags", []):
        if flag in outcome.data_quality_flags:
            outcome.failures.append(f"금지 flag 존재: {flag}")
    if "peer_outlier_flags" in expect and outcome.peer_outlier_flags != sorted(expect["peer_outlier_flags"]):
        outcome.failures.append(
            f"peer outlier flag 불일치: 실제 {outcome.peer_outlier_flags} != 기대 {sorted(expect['peer_outlier_flags'])}"
        )


def run_all() -> list[CaseOutcome]:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    outcomes = [evaluate_case(case) for case in cases]
    for outcome in outcomes:
        _check(outcome)
    return outcomes


def update_baseline() -> list[CaseOutcome]:
    """현재 엔진 출력을 cases.json의 expect로 재기록한다(스냅샷 베이스라인)."""
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    by_id = {case["case_id"]: case for case in payload["cases"]}
    outcomes = [evaluate_case(case) for case in payload["cases"]]
    for outcome in outcomes:
        case = by_id[outcome.case_id]
        # 기존 expect의 invariant 의도(must_*) 키는 보존하고, 스냅샷 값만 갱신한다.
        expect = dict(case.get("expect", {}))
        expect["selected"] = outcome.selected
        expect["score"] = outcome.score
        if outcome.peer_outlier_flags:
            expect["peer_outlier_flags"] = outcome.peer_outlier_flags
        case["expect"] = expect
    CASES_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return outcomes


def write_reports(outcomes: list[CaseOutcome]) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    json_path = REPORTS_DIR / f"{today}_competitor_eval.json"
    md_path = REPORTS_DIR / f"{today}_competitor_eval.md"

    passed = sum(o.passed for o in outcomes)
    total = len(outcomes)

    payload = {
        "run_date": today,
        "suite": "competitor_peer_quality_regression",
        "passed": passed,
        "total": total,
        "cases": [
            {
                "case_id": o.case_id,
                "description": o.description,
                "passed": o.passed,
                "selected": o.selected,
                "score": o.score,
                "data_quality_flags": o.data_quality_flags,
                "peer_outlier_flags": o.peer_outlier_flags,
                "relative_position": o.relative_position,
                "failures": o.failures,
            }
            for o in outcomes
        ],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Competitor peer 비교 품질 회귀 리포트 — {today}",
        "",
        f"- 스위트: peer 선정·상대위치 점수 엔진(LLM·DB·네트워크 미사용)",
        f"- 통과: **{passed}/{total}**",
        "",
        "## 케이스별 결과",
        "",
    ]
    for o in outcomes:
        status = "✅" if o.passed else "❌"
        lines.append(f"### {status} {o.case_id} — {o.description}")
        lines.append("")
        lines.append(f"- 선정 peer: `{o.selected}`")
        lines.append(f"- score: **{o.score}**")
        if o.peer_outlier_flags:
            lines.append(f"- outlier 플래그: {o.peer_outlier_flags}")
        lines.append(f"- data_quality_flags: {o.data_quality_flags}")
        if o.failures:
            for failure in o.failures:
                lines.append(f"- ❌ {failure}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Competitor peer 비교 품질 회귀 평가")
    parser.add_argument("--update", action="store_true", help="현재 엔진 출력을 기대 스냅샷으로 재기록")
    parser.add_argument("--quiet", action="store_true", help="케이스별 상세 출력 생략")
    args = parser.parse_args()

    if args.update:
        outcomes = update_baseline()
        print(f"베이스라인 갱신 완료: {len(outcomes)}개 케이스 → {CASES_PATH}")
        write_reports(outcomes)
        return 0

    outcomes = run_all()
    json_path, md_path = write_reports(outcomes)
    passed = sum(o.passed for o in outcomes)
    total = len(outcomes)

    if not args.quiet:
        for o in outcomes:
            status = "✅" if o.passed else "❌"
            print(f"{status} {o.case_id}: selected={o.selected} score={o.score}")
            for failure in o.failures:
                print(f"    - {failure}")

    print(f"\n통과 {passed}/{total} · 리포트: {md_path}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
