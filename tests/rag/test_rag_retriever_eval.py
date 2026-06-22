import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "eval" / "run_rag_retriever_eval.py"
SPEC = importlib.util.spec_from_file_location("rag_retriever_eval", MODULE_PATH)
rag_eval = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(rag_eval)


def test_retriever_eval_metrics():
    matches = [False, True, False]

    assert rag_eval.reciprocal_rank(matches) == 0.5
    assert round(rag_eval.ndcg_at_k(matches, 3), 4) == 0.6309


def test_title_matches_any_keyword():
    assert rag_eval.title_matches("삼성전자 반도체 뉴스", ["HBM", "반도체"])
    assert not rag_eval.title_matches("배터리 업황 뉴스", ["반도체"])
