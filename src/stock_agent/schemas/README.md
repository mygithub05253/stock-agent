# `src/stock_agent/schemas/` — Pydantic 모델

## 핵심 원칙

> **에이전트 사이를 오가는 모든 데이터는 Pydantic 스키마에 정의된 형식만 허용.**

이유: LLM이 자유 JSON을 만들면 누락/오타가 발생. 스키마 강제로 시스템 안정성 확보.

## 파일 (예정)

| 파일 | 모델 | 사용처 |
|------|------|--------|
| `user.py` | `UserProfile`, `Portfolio`, `Holding` | 회원·포트 입력 |
| `analysis.py` | `AgentState`, `QuantReport`, `QualReport`, `CompetitorReport` | 에이전트 입출력 |
| `reports.py` | `Tier1Output`, `Tier2Output`, `Tier3Output` | 화면·다운로드 |
| `decision.py` | `ActionRecommendation` (BUY/HOLD/SELL + MoS + 신뢰도 + 적합도) | Action Engine |
