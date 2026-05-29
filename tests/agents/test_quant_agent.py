import os
import sys
from pprint import pprint

# 💡 [경로 수정] test/ 폴더에서 상위 디렉토리의 src/ 폴더를 명확히 바라보도록 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, os.path.join(project_root, "src"))

from stock_agent.schemas.analysis import AgentState
from stock_agent.agents.quant import run_quant

# Pydantic 모델을 우회하기 위한 가짜(Mock) 큐레이터 클래스
class MockCurator:
    def __init__(self, stock_code, corp_code, corp_name):
        self.stock_code = stock_code
        self.corp_code = corp_code
        self.corp_name = corp_name

def test_quant_isolation():
    print("🚀 [TEST] Quant Agent 단독 테스트 가동 (test/ 환경)...")

    # 1. 가짜 초입 데이터 생성 (큐레이터 역할 모킹)
    mock_curator = MockCurator(
        stock_code="005930",
        corp_code="00126380",
        corp_name="삼성전자"
    )

    # 2. AgentState 메모리장부 생성 및 세팅
    # 💡 Pydantic 검증을 우회하고 가짜 State를 강제로 띄웁니다.
    state = AgentState.model_construct(
        user_query="삼성전자 퀀트 테스트",
        user_profile=None,
        portfolio=None
    )
    state.curator = mock_curator
    state.as_of_date = "2026-05-26" # 백테스트 타깃 날짜 고정

    try:
        # 3. Quant Agent 단독 슛!
        print(f"🤖 Quant Agent에게 {mock_curator.corp_name} 분석을 지시합니다...\n")
        result_state = run_quant(state)
        quant_result = result_state.quant

        # 4. 결과 출력
        print("==================================================")
        print("✅ [TEST SUCCESS] Quant Agent 실행 완료!")
        print("==================================================")
        print(f"📊 [종합 점수] : {quant_result.score} 점")
        print(f"🚦 [투자 신호] : {quant_result.valuation_signal}")
        
        print("\n📈 [산출된 정량 메트릭스]")
        pprint(quant_result.metrics)
        
        print("\n🟢 [긍정적 요인 (Reasons)]")
        for reason in quant_result.reasons:
            print(f"  - {reason}")
            
        print("\n🔴 [리스크 요인 (Risks)]")
        for risk in quant_result.risks:
            print(f"  - {risk}")
        print("==================================================")

    except Exception as e:
        print(f"\n❌ [TEST FAILED] 에러 발생: {e}")
        raise e  # pytest가 에러를 정확히 캐치할 수 있도록 예외를 던집니다.

if __name__ == "__main__":
    test_quant_isolation()