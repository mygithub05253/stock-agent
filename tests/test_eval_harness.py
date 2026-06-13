"""eval 하네스의 골든셋 무결성과 rule-based 채점 로직 검증.

파이프라인 실행이나 LLM 호출 없이(비용 0원, DB 불필요) CI에서 돈다.
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_benchmark_module():
    spec = importlib.util.spec_from_file_location("run_benchmark", REPO_ROOT / "eval" / "run_benchmark.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_benchmark"] = module
    spec.loader.exec_module(module)
    return module


def test_golden_set_cases_have_matching_expected_outputs():
    bench = _load_benchmark_module()
    cases, expected = bench.load_golden_cases()

    assert len(cases) >= 5
    case_ids = [case["case_id"] for case in cases]
    assert len(case_ids) == len(set(case_ids)), "case_id는 중복되면 안 된다"
    for case_id in case_ids:
        assert case_id in expected["cases"], f"{case_id}의 기대값이 expected_outputs.json에 없다"

    for case in cases:
        assert case["query"].strip()
        assert case["user_profile"]["risk_tolerance"] in {"low", "medium", "high"}
        assert case["portfolio"]["holdings"], "골든셋 케이스는 보유 종목이 1개 이상이어야 한다"


def test_rule_based_checks_pass_for_contract_compliant_record():
    bench = _load_benchmark_module()
    _, expected = bench.load_golden_cases()

    record = bench.CaseRecord(
        case_id="choi_eunseo_sell_decision",
        persona="테스트",
        question="삼성전자 급락했는데 손절해야 해?",
        answer="HOLD 신호입니다.",
        contexts=["근거 1"],
        signal="HOLD",
        confidence=0.7,
        suitability=0.4,
        intent="sell_decision",
        urgency_reason="drop",
        stock_code="005930",
        disclaimer="본 결과는 투자 권유가 아니라 분석 신호입니다.",
    )

    checks = bench.rule_based_checks(record, expected)

    assert checks["pipeline_ran"] is True
    assert all(checks.values()), f"실패한 체크: {[k for k, v in checks.items() if not v]}"


def test_rule_based_checks_fail_for_broken_record():
    bench = _load_benchmark_module()
    _, expected = bench.load_golden_cases()

    record = bench.CaseRecord(
        case_id="choi_eunseo_sell_decision",
        persona="테스트",
        question="질문",
        answer="답",
        contexts=[],
        signal="MOON",          # 허용되지 않는 신호
        confidence=150,          # 범위(0~100) 밖
        suitability=0.5,
        intent="holding_review",  # 기대값(sell_decision)과 불일치
        urgency_reason="drop",
        stock_code="005930",
        disclaimer="면책 없음",  # '투자 권유' 문구 누락
    )

    checks = bench.rule_based_checks(record, expected)

    assert checks["signal_valid"] is False
    assert checks["disclaimer_present"] is False
    assert checks["confidence_in_range"] is False
    assert checks["evidence_nonempty"] is False
    assert checks["intent_match"] is False


def test_pipeline_error_short_circuits_checks():
    bench = _load_benchmark_module()
    _, expected = bench.load_golden_cases()

    record = bench.CaseRecord(
        case_id="park_minho_hold_review",
        persona="테스트",
        question="질문",
        answer="",
        contexts=[],
        error="RuntimeError: DB down",
    )

    checks = bench.rule_based_checks(record, expected)
    assert checks == {"pipeline_ran": False}
