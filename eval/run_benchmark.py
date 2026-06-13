"""골든셋 기반 평가 하네스.

eval/golden_set/personas.json 의 각 케이스를 Phase 1 파이프라인에 넣어
(1) rule-based 채점 (LLM 비용 0원: 신호 유효성·의도 분류·면책 문구·근거 존재)
(2) RAGAS 채점 (LLM-as-judge: faithfulness, 선택적으로 answer_relevancy)
을 수행하고 eval/reports/ 에 날짜별 리포트(md + json)를 남긴다.

실행 예시:
    python eval/run_benchmark.py                  # rule-based + RAGAS faithfulness
    python eval/run_benchmark.py --skip-ragas     # LLM 비용 없이 rule-based만
    python eval/run_benchmark.py --limit 2        # 케이스 2개만 (비용 절약)
    python eval/run_benchmark.py --with-relevancy # answer_relevancy 추가 (로컬 임베딩 사용)

비용 정책: RAGAS judge는 OPENROUTER_API_KEY 가 설정된 경우에만 동작하며,
키가 없으면 rule-based 결과만 산출하고 RAGAS는 건너뛴다(실패 아님).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

EVAL_DIR = Path(__file__).resolve().parent
GOLDEN_DIR = EVAL_DIR / "golden_set"
REPORTS_DIR = EVAL_DIR / "reports"

# eval/ 을 레포 루트에서 바로 실행해도 src 레이아웃 패키지를 찾도록 경로 주입
SRC_DIR = EVAL_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@dataclass
class CaseRecord:
    """파이프라인 1회 실행 결과를 RAGAS 입력과 채점에 쓰기 좋은 형태로 보관한다."""

    case_id: str
    persona: str
    question: str
    answer: str
    contexts: list[str]
    signal: str | None = None
    confidence: float | None = None
    suitability: float | None = None
    intent: str | None = None
    urgency_reason: str | None = None
    stock_code: str | None = None
    candidates: list[str] = field(default_factory=list)
    disclaimer: str = ""
    error: str | None = None


def load_golden_cases() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    personas = json.loads((GOLDEN_DIR / "personas.json").read_text(encoding="utf-8"))
    expected = json.loads((GOLDEN_DIR / "expected_outputs.json").read_text(encoding="utf-8"))
    return personas["cases"], expected


def run_pipeline_case(case: dict[str, Any]) -> CaseRecord:
    # 무거운 import(임베딩 모델 체인)는 실제 실행 시점으로 미룬다.
    from stock_agent.graph.pipeline import run_phase1_analysis
    from stock_agent.schemas.analysis import Holding, Portfolio, UserProfile

    profile = UserProfile(**case["user_profile"])
    portfolio = Portfolio(
        holdings=[Holding(**h) for h in case["portfolio"]["holdings"]],
        cash_weight=case["portfolio"]["cash_weight"],
    )

    record = CaseRecord(
        case_id=case["case_id"],
        persona=case["persona"],
        question=case["query"],
        answer="",
        contexts=[],
    )

    try:
        output = run_phase1_analysis(case["query"], profile, portfolio)
    except Exception as exc:  # 케이스 하나가 죽어도 전체 벤치마크는 계속 돈다
        record.error = f"{exc.__class__.__name__}: {exc}"
        return record

    state = output.state
    strategist = state.strategist

    # answer = 사용자에게 실제로 보여주는 Tier1 결론 + 핵심 근거
    answer_parts = [output.tier1.headline]
    if strategist is not None:
        answer_parts.extend(strategist.key_reasons)
        answer_parts.extend(strategist.risks)
    record.answer = " ".join(part for part in answer_parts if part)

    # contexts = 각 worker가 수집·계산한 근거 (faithfulness의 검증 대상)
    contexts: list[str] = []
    if state.quant is not None:
        contexts.extend(state.quant.reasons)
    if state.qual is not None:
        contexts.extend(state.qual.evidence)
        contexts.extend(state.qual.risks)
    if state.competitor is not None:
        contexts.extend(state.competitor.evidence)
    record.contexts = [c for c in contexts if c]

    record.signal = output.tier1.signal
    record.confidence = output.tier1.confidence
    record.suitability = output.tier1.suitability
    record.disclaimer = output.tier1.disclaimer
    if state.user_request is not None:
        record.intent = state.user_request.intent
        record.urgency_reason = state.user_request.urgency_reason
    if state.curator is not None:
        record.stock_code = getattr(state.curator, "stock_code", None)
        record.candidates = list(getattr(state.curator, "candidates", []) or [])
    return record


def rule_based_checks(record: CaseRecord, expected: dict[str, Any]) -> dict[str, Any]:
    """LLM 없이 계약(스키마·분류·면책) 준수를 검사한다."""
    common = expected["common"]
    case_expected = expected["cases"].get(record.case_id, {})
    checks: dict[str, Any] = {}

    if record.error is not None:
        checks["pipeline_ran"] = False
        return checks
    checks["pipeline_ran"] = True

    checks["signal_valid"] = record.signal in common["allowed_signals"]
    checks["disclaimer_present"] = common["disclaimer_must_contain"] in record.disclaimer
    lo, hi = common["confidence_range"]
    checks["confidence_in_range"] = record.confidence is not None and lo <= record.confidence <= hi
    lo, hi = common["suitability_range"]
    checks["suitability_in_range"] = record.suitability is not None and lo <= record.suitability <= hi
    checks["evidence_nonempty"] = len(record.contexts) > 0

    if "expected_stock_code" in case_expected:
        checks["stock_code_match"] = record.stock_code == case_expected["expected_stock_code"]
    if "expected_intent" in case_expected:
        expected_intent = case_expected["expected_intent"]
        # LLM 분류의 합리적 변동을 흡수하기 위해 허용 목록(list)도 지원한다
        allowed = expected_intent if isinstance(expected_intent, list) else [expected_intent]
        checks["intent_match"] = record.intent in allowed
    if "expected_urgency" in case_expected:
        checks["urgency_match"] = record.urgency_reason == case_expected["expected_urgency"]
    if case_expected.get("expect_candidates"):
        checks["candidates_present"] = len(record.candidates) > 0

    return checks


def build_ragas_judge():
    """OpenRouter를 OpenAI 호환 endpoint로 사용하는 LLM-as-judge를 만든다."""
    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper

    from stock_agent.config import get_settings

    settings = get_settings()
    if not settings.openrouter_api_key:
        return None
    judge = ChatOpenAI(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=0,
        timeout=settings.openrouter_timeout_seconds,
    )
    return LangchainLLMWrapper(judge)


def run_ragas(records: list[CaseRecord], with_relevancy: bool) -> dict[str, Any] | None:
    """RAGAS faithfulness(기본) + answer_relevancy(선택)를 채점한다. judge 없으면 None."""
    valid = [r for r in records if r.error is None and r.contexts]
    if not valid:
        return None

    judge = build_ragas_judge()
    if judge is None:
        return None

    from ragas import EvaluationDataset, evaluate

    # ragas 0.4의 metrics.collections 경로는 InstructorLLM 전용이라
    # LangchainLLMWrapper(OpenRouter judge)와 호환되는 레거시 경로를 사용한다.
    from ragas.metrics import Faithfulness

    metrics: list[Any] = [Faithfulness(llm=judge)]

    if with_relevancy:
        # answer_relevancy는 임베딩이 필요 → 비용 0원인 로컬 모델(bge-m3, qual과 동일)을 쓴다
        from langchain_huggingface import HuggingFaceEmbeddings
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.metrics import ResponseRelevancy

        embeddings = LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(model_name="BAAI/bge-m3"))
        metrics.append(ResponseRelevancy(llm=judge, embeddings=embeddings))

    dataset = EvaluationDataset.from_list(
        [
            {
                "user_input": r.question,
                "response": r.answer,
                "retrieved_contexts": r.contexts,
            }
            for r in valid
        ]
    )
    result = evaluate(dataset=dataset, metrics=metrics)
    df = result.to_pandas()

    scores: dict[str, Any] = {"cases": {}}
    metric_columns = [c for c in df.columns if c not in {"user_input", "response", "retrieved_contexts"}]
    for record, (_, row) in zip(valid, df.iterrows()):
        scores["cases"][record.case_id] = {col: _to_float(row[col]) for col in metric_columns}
    for col in metric_columns:
        values = [v[col] for v in scores["cases"].values() if v[col] is not None]
        scores[f"mean_{col}"] = round(sum(values) / len(values), 4) if values else None
    return scores


def _to_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if result != result else round(result, 4)  # NaN 방어


def write_reports(
    records: list[CaseRecord],
    checks_by_case: dict[str, dict[str, Any]],
    ragas_scores: dict[str, Any] | None,
) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    json_path = REPORTS_DIR / f"{today}_benchmark.json"
    md_path = REPORTS_DIR / f"{today}_benchmark.md"

    total_checks = sum(len(c) for c in checks_by_case.values())
    passed_checks = sum(sum(bool(v) for v in c.values()) for c in checks_by_case.values())

    payload = {
        "run_date": today,
        "case_count": len(records),
        "rule_based": {
            "passed": passed_checks,
            "total": total_checks,
            "pass_rate": round(passed_checks / total_checks, 4) if total_checks else None,
            "cases": checks_by_case,
        },
        "ragas": ragas_scores,
        "records": [asdict(r) for r in records],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# 평가 리포트 — {today}",
        "",
        f"- 케이스: {len(records)}개",
        f"- rule-based 통과율: **{passed_checks}/{total_checks}**",
    ]
    if ragas_scores:
        for key, value in ragas_scores.items():
            if key.startswith("mean_"):
                lines.append(f"- RAGAS {key.removeprefix('mean_')}: **{value}** (목표 ≥ 0.80)")
    else:
        lines.append("- RAGAS: 건너뜀 (OPENROUTER_API_KEY 미설정 또는 --skip-ragas)")
    lines += ["", "## 케이스별 결과", ""]
    for record in records:
        checks = checks_by_case.get(record.case_id, {})
        status = "❌ 실행 실패" if record.error else "✅"
        lines.append(f"### {status} {record.case_id} — {record.persona}")
        lines.append("")
        if record.error:
            lines.append(f"- 오류: `{record.error}`")
        else:
            lines.append(f"- 질문: {record.question}")
            lines.append(
                f"- 결과: signal={record.signal}, confidence={record.confidence}, "
                f"suitability={record.suitability}, intent={record.intent}, urgency={record.urgency_reason}"
            )
            failed = [name for name, ok in checks.items() if not ok]
            lines.append(f"- rule-based: {sum(bool(v) for v in checks.values())}/{len(checks)}"
                         + (f" (실패: {', '.join(failed)})" if failed else ""))
            if ragas_scores and record.case_id in ragas_scores.get("cases", {}):
                lines.append(f"- RAGAS: {ragas_scores['cases'][record.case_id]}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="골든셋 기반 파이프라인 평가")
    parser.add_argument("--limit", type=int, default=None, help="평가할 케이스 수 제한 (비용 절약)")
    parser.add_argument("--case", type=str, default=None, help="특정 case_id만 실행")
    parser.add_argument("--skip-ragas", action="store_true", help="RAGAS(LLM judge) 채점 생략")
    parser.add_argument("--with-relevancy", action="store_true", help="answer_relevancy 추가 채점")
    args = parser.parse_args()

    cases, expected = load_golden_cases()
    if args.case:
        cases = [c for c in cases if c["case_id"] == args.case]
        if not cases:
            print(f"case_id '{args.case}' 를 골든셋에서 찾지 못했습니다.")
            return 1
    if args.limit:
        cases = cases[: args.limit]

    print(f"골든셋 {len(cases)}개 케이스 실행 중...")
    records = [run_pipeline_case(case) for case in cases]
    checks_by_case = {r.case_id: rule_based_checks(r, expected) for r in records}

    ragas_scores = None
    if not args.skip_ragas:
        print("RAGAS 채점 중 (LLM-as-judge)...")
        try:
            ragas_scores = run_ragas(records, with_relevancy=args.with_relevancy)
        except ImportError as exc:
            print(f"RAGAS 의존성이 없어 건너뜁니다: {exc} → pip install -e .[eval]")
        if ragas_scores is None:
            print("RAGAS 건너뜀 (judge 키 없음 또는 유효 케이스 없음)")

    json_path, md_path = write_reports(records, checks_by_case, ragas_scores)
    print(f"리포트 저장: {md_path}")
    print(f"          : {json_path}")

    failed_cases = [r.case_id for r in records if r.error]
    if failed_cases:
        print(f"실행 실패 케이스: {failed_cases}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
