# 평가 리포트 — 2026-06-12

- 케이스: 5개
- rule-based 통과율: **40/41**
- RAGAS faithfulness: **0.4096** (목표 ≥ 0.80)

## 케이스별 결과

### ✅ park_minho_hold_review — 박민호 — 40대 보수형 직장인, 삼성전자 장기 보유

- 질문: 삼성전자 계속 가져가도 될까?
- 결과: signal=HOLD, confidence=65, suitability=40, intent=holding_review, urgency=general
- rule-based: 8/8
- RAGAS: {'faithfulness': 0.4667}

### ✅ kim_jiyeon_buy_more — 김지연 — 30대 공격형, SK하이닉스 추가 매수 고민

- 질문: SK하이닉스 비중 늘려도 돼?
- 결과: signal=HOLD, confidence=75, suitability=65, intent=holding_review, urgency=general
- rule-based: 8/8
- RAGAS: {'faithfulness': 0.2857}

### ✅ lee_seojun_portfolio_review — 이서준 — 20대 초보 투자자, 포트폴리오 전반 점검 요청

- 질문: 요즘 내 포트폴리오에서 볼만한 종목 알려줘
- 결과: signal=HOLD, confidence=68, suitability=58, intent=portfolio_review, urgency=general
- rule-based: 7/8 (실패: candidates_present)
- RAGAS: {'faithfulness': 0.5455}

### ✅ choi_eunseo_sell_decision — 최은서 — 50대 보수형, 급락 시 손절 고민

- 질문: 삼성전자 급락했는데 손절해야 해?
- 결과: signal=HOLD, confidence=65, suitability=30, intent=sell_decision, urgency=drop
- rule-based: 9/9
- RAGAS: {'faithfulness': 0.3333}

### ✅ jung_hana_news_check — 정하나 — 30대 중립형, 공시 이슈 확인 요청

- 질문: 삼성전자 공시 이슈 확인해줘
- 결과: signal=HOLD, confidence=68, suitability=60, intent=holding_review, urgency=news
- rule-based: 8/8
- RAGAS: {'faithfulness': 0.4167}
