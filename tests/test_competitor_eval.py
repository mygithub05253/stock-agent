"""Competitor peer 비교 품질 회귀 골든셋 검증.

`eval/run_competitor_eval.py`의 순수 점수 엔진 스냅샷 스위트를 CI에서 그대로 돌려,
peer 선정 순서·종합 score·데이터 품질 플래그가 베이스라인에서 드리프트하면 실패시킨다.
LLM·DB·네트워크 미사용(비용 0원).
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_eval_module():
    spec = importlib.util.spec_from_file_location(
        "run_competitor_eval", REPO_ROOT / "eval" / "run_competitor_eval.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_competitor_eval"] = module
    spec.loader.exec_module(module)
    return module


def test_competitor_golden_cases_all_pass():
    """골든셋 6개 케이스가 모두 기대 스냅샷·불변식과 일치해야 한다."""
    evaler = _load_eval_module()
    outcomes = evaler.run_all()

    assert len(outcomes) >= 6, "회귀 커버리지가 줄어들면 안 된다"
    failed = {o.case_id: o.failures for o in outcomes if not o.passed}
    assert not failed, f"회귀 발생: {failed}"


def test_competitor_golden_locks_similarity_ordering():
    """#62 복합 유사도: 시총·사업경제성이 동일한 peer가 데이터완성도만 높은 peer보다 우선."""
    evaler = _load_eval_module()
    outcomes = {o.case_id: o for o in evaler.run_all()}

    c6 = outcomes["C6_similarity_ordering"]
    assert c6.selected[0] == "SIZEMATCH"
    assert "QUALONLY" in c6.selected
    assert c6.selected.index("SIZEMATCH") < c6.selected.index("QUALONLY")


def test_competitor_golden_market_cap_band_excludes_giant():
    """시총 4배 초과 대형 peer는 비교군에서 제외된다."""
    evaler = _load_eval_module()
    outcomes = {o.case_id: o for o in evaler.run_all()}

    c2 = outcomes["C2_market_cap_band_filter"]
    assert "GIANT9" not in c2.selected
    assert "peer_count_below_minimum" in c2.data_quality_flags


def test_competitor_golden_low_quality_target_score_capped():
    """타깃 데이터 완성도 60 미만이면 score가 55 이하로 제한된다."""
    evaler = _load_eval_module()
    outcomes = {o.case_id: o for o in evaler.run_all()}

    c5 = outcomes["C5_low_quality_target_cap"]
    assert c5.score <= 55
    assert "target_data_quality_low" in c5.data_quality_flags
