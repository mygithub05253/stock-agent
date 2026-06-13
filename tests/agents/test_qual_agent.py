import os
import sys

# 💡 프로젝트 루트 및 src 폴더 경로를 파이썬 검색 경로에 주입
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, os.path.join(project_root, "src"))

from stock_agent.schemas.analysis import AgentState
from stock_agent.agents import qual
from stock_agent.agents.guardrail import run_guardrail
from stock_agent.schemas.analysis import StrategistResult

class MockCurator:
    def __init__(self, stock_code, corp_code, corp_name):
        self.stock_code = stock_code
        self.corp_code = corp_code
        self.corp_name = corp_name

def test_qual_isolation(monkeypatch):
    print("🚀 [TEST] Qual Agent 공시 원문 데이터 마이닝 테스트 가동...")
    monkeypatch.setattr(
        qual,
        "retrieve_news_with_fallback",
        lambda ticker: [
            {
                "title": "삼성전자 반도체 업황 개선",
                "body": "AI 반도체 수요와 실적 개선 기대가 있습니다.",
                "publisher": "test",
            }
        ],
    )
    monkeypatch.setattr(
        qual,
        "retrieve_disclosures_with_fallback",
        lambda corp_code: [
            {
                "report_nm": "사업보고서",
                "body": "업황 둔화와 투자 리스크를 함께 공시했습니다.",
                "source_url": "test",
            }
        ],
    )

    # 삼성전자 타깃 오브젝트 모킹
    mock_curator = MockCurator(
        stock_code="005930",
        corp_code="00126380",
        corp_name="삼성전자"
    )

    state = AgentState.model_construct(
        user_query="삼성전자 최신 공시 분석해줘",
        user_profile=None,
        portfolio=None
    )
    state.curator = mock_curator
    
    # 💡 5월 22일 분석을 위해 5월 21일로 시점 족쇄 채우기
    state.as_of_date = "2026-05-21"  

    try:
        result_state = qual.run_qual(state)
        qual_res = result_state.qual

        print("\n==================================================")
        print("✅ [TEST SUCCESS] Qual Agent 정성 분석 연동 완료!")
        print("==================================================")
        print(f"📊 [공시 정성 점수] : {qual_res.score} 점")
        print(f"🚦 [공시 센티멘트] : {qual_res.sentiment}")
        print(f"🔍 [포착된 이벤트] : {qual_res.event_types}")
        
        print("\n🟢 [공시 원문 기반 호재 근거 (Evidence)]")
        for ev in qual_res.evidence:
            print(f"  - {ev}")
            
        print("\n🔴 [공시 원문 기반 리스크 (Risks)]")
        for risk in qual_res.risks:
            print(f"  - {risk}")
        print("==================================================\n")

    except Exception as e:
        print(f"\n❌ 테스트 구동 실패: {e}")
        raise e

def test_qual_uses_fallback_docs_when_rag_fails(monkeypatch):
    monkeypatch.setattr(
        qual,
        "retrieve_news_with_fallback",
        lambda ticker: qual.fallback_news_docs(ticker, "ConnectionError: news db down"),
    )
    monkeypatch.setattr(
        qual,
        "retrieve_disclosures_with_fallback",
        lambda corp_code: qual.fallback_disclosure_docs(corp_code, "TimeoutError: dart rag down"),
    )

    state = AgentState.model_construct(
        user_query="삼성전자 뉴스랑 공시 확인해줘",
        user_profile=None,
        portfolio=None,
        curator=MockCurator("005930", "00126380", "삼성전자"),
    )

    result_state = qual.run_qual(state)

    assert result_state.qual is not None
    assert result_state.qual.score >= 0
    assert any("fallback_reason" in item for item in result_state.qual.evidence)
    assert any("fallback" in item.lower() for item in result_state.qual.evidence)


def test_guardrail_warns_when_qual_used_fallback(monkeypatch):
    monkeypatch.setattr(
        qual,
        "retrieve_news_with_fallback",
        lambda ticker: qual.fallback_news_docs(ticker, "ConnectionError: news db down"),
    )
    monkeypatch.setattr(
        qual,
        "retrieve_disclosures_with_fallback",
        lambda corp_code: qual.fallback_disclosure_docs(corp_code, "TimeoutError: dart rag down"),
    )

    state = AgentState.model_construct(
        user_query="삼성전자 뉴스랑 공시 확인해줘",
        user_profile=None,
        portfolio=None,
        curator=MockCurator("005930", "00126380", "삼성전자"),
    )
    state = qual.run_qual(state)
    state.strategist = StrategistResult(
        signal="HOLD",
        confidence=55,
        suitability=55,
        headline="보유 유지 검토가 우세합니다.",
        key_reasons=[],
        risks=[],
        next_actions=[],
    )

    guarded_state = run_guardrail(state)

    assert guarded_state.guardrail is not None
    assert any("fallback" in warning for warning in guarded_state.guardrail.warnings)
