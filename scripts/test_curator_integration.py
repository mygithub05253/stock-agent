from stock_agent.agents.curator import run_curator
from stock_agent.schemas.analysis import AgentState, UserProfile, Portfolio, Holding, UserRequest


def make_demo_state():
    profile = UserProfile(user_id="demo-test", preferred_sectors=["반도체"])
    portfolio = Portfolio(holdings=[
        Holding(stock_code="005930", corp_name="삼성전자", sector="반도체", weight=0.3, qty=10, current_price=78000, avg_price=72000),
        Holding(stock_code="000660", corp_name="SK하이닉스", sector="반도체", weight=0.2, qty=3, current_price=201000, avg_price=185000),
    ], cash_weight=0.2)

    state = AgentState(
        user_query="삼성전자 좀 봐줘",
        user_request=UserRequest(raw_query="삼성전자 좀 봐줘"),
        user_profile=profile,
        portfolio=portfolio,
    )
    return state


if __name__ == "__main__":
    state = make_demo_state()
    state = run_curator(state)
    print("Curator result:", state.curator.model_dump_json(indent=2, ensure_ascii=False))
