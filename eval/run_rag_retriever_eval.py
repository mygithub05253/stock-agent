from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from stock_agent.rag.retriever import retrieve_news


DEFAULT_CASES_PATH = Path("eval/rag_retriever_golden/cases.json")
DEFAULT_REPORT_DIR = Path("eval/reports")


def title_matches(title: str | None, keywords: list[str]) -> bool:
    if not title:
        return False
    normalized_title = title.lower()
    return any(keyword.lower() in normalized_title for keyword in keywords)


def reciprocal_rank(matches: list[bool]) -> float:
    for index, matched in enumerate(matches, start=1):
        if matched:
            return 1.0 / index
    return 0.0


def ndcg_at_k(matches: list[bool], k: int) -> float:
    gains = matches[:k]
    dcg = sum((1.0 / math.log2(index + 2)) for index, matched in enumerate(gains) if matched)
    ideal_matches = sorted(matches, reverse=True)[:k]
    idcg = sum(
        (1.0 / math.log2(index + 2))
        for index, matched in enumerate(ideal_matches)
        if matched
    )
    return dcg / idcg if idcg else 0.0


def evaluate_case(case: dict[str, Any], k: int) -> dict[str, Any]:
    docs = retrieve_news(ticker=case.get("ticker"), query=case["query"], k=k)
    matches = [
        title_matches(doc.get("title"), case.get("relevant_title_keywords", []))
        for doc in docs
    ]

    return {
        "id": case["id"],
        "ticker": case.get("ticker"),
        "query": case["query"],
        "retrieved": len(docs),
        "hit_at_k": bool(any(matches)),
        "mrr": reciprocal_rank(matches),
        "ndcg_at_k": ndcg_at_k(matches, k),
        "titles": [doc.get("title") for doc in docs],
        "methods": [doc.get("retrieval_method") for doc in docs],
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {"case_count": 0, "hit_rate": 0.0, "mrr": 0.0, "ndcg_at_k": 0.0}

    return {
        "case_count": len(results),
        "hit_rate": sum(1 for result in results if result["hit_at_k"]) / len(results),
        "mrr": sum(result["mrr"] for result in results) / len(results),
        "ndcg_at_k": sum(result["ndcg_at_k"] for result in results) / len(results),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Qual news retriever quality.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    results = [evaluate_case(case, args.k) for case in cases]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "k": args.k,
        "summary": summarize(results),
        "results": results,
    }

    args.report_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.report_dir / f"{datetime.now().date().isoformat()}_rag_retriever_eval.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
