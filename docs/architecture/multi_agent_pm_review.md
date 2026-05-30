# PR #20 PM Alignment Review

| 항목 | 내용 |
|------|------|
| 대상 PR | PR #20 Multi-Agent Architecture |
| 상태 | Merged |
| 작성자 관점 | Lead PM post-merge alignment review |
| 리뷰 톤 | 방향성은 승인하되, 구현 전 결정사항은 명확히 요구 |
| 목적 | “이 구조로 가자”와 “아직 정해야 할 것”을 팀이 같은 언어로 이해하게 만들기 |

---

## 1. 내가 이 PR을 어떻게 보는가

내 의견은 명확하다.

> PR #20의 큰 방향은 맞다.  
> 다만 이 PR은 “구현해도 된다”는 허가가 아니라, “우리 MVP는 이 구조를 기준선으로 삼자”는 합의 문서다.

즉, 나는 이 PR을 **architecture baseline 승인**으로 본다. 이제 바로 LLM, RAG, DB, LangGraph 구현으로 뛰어들기 전에 팀이 먼저 닫아야 할 결정들이 있다.

내가 승인하는 MVP 구조는 다음이다.

```text
Curator
-> Quant / Qual / Competitor 병렬 실행
-> Strategist
-> Guardrail
-> Tier 1 / Tier 2 / Tier 3 결과
```

쉽게 말하면 이렇다.

| 구성 | 쉬운 설명 |
|------|-----------|
| Curator | 사용자의 질문을 “시스템이 처리할 수 있는 주문서”로 바꾸는 역할 |
| Quant | 숫자를 계산하는 역할. PER, PBR, ROE, valuation은 여기서 처리 |
| Qual | 뉴스, 공시, 리포트에서 근거를 찾는 역할 |
| Competitor | 같은 업종 회사들과 비교하는 역할 |
| Strategist | 여러 분석 결과를 모아 최종 signal을 정리하는 역할 |
| Guardrail | 위험한 표현, 출처 없는 단정, 수익 보장 문구를 막는 최종 검수 역할 |

이 구조는 어렵게 말하면 LangGraph central supervisor pattern이고, 쉽게 말하면 **작업반장 한 명이 일을 나눠주고 결과를 모아 검수하는 구조**다.

---

## 2. 내가 동의하는 것

### 2.1 MVP는 central supervisor 구조로 가는 것이 맞다

현재 우리 프로젝트는 Streamlit, Postgres, pgvector, 단일 Python repo 안에서 돌아간다. 이 상황에서는 agent들이 자유롭게 서로 대화하는 구조보다, 실행 순서와 책임이 보이는 구조가 더 안전하다.

내 판단은 다음과 같다.

- MVP에서는 복잡한 자율성보다 **통제 가능성**이 더 중요하다.
- 금융 분석에서는 “어떤 근거로 이런 결론이 나왔는지”를 추적할 수 있어야 한다.
- 비용이 제한되어 있으므로 LLM 호출 흐름이 예측 가능해야 한다.
- 문제가 생겼을 때 어느 agent에서 실패했는지 바로 찾아야 한다.

따라서 MVP에서는 LangGraph 기반 central supervisor pattern을 기준으로 삼는 것이 맞다.

### 2.2 A2A/full decentralized agents는 MVP에서 막아야 한다

나는 MVP에서 A2A 또는 full decentralized agents를 도입하는 것에 반대한다.

이유는 기술이 나쁘기 때문이 아니다. 지금 우리 상황에 비해 너무 이르기 때문이다.

| 질문 | 현재 답 |
|------|---------|
| 외부 vendor agent와 통신해야 하는가? | 아니다 |
| agent가 별도 서버로 나뉘어 있는가? | 아니다 |
| agent 간 인증/권한 경계가 필요한가? | 아직 아니다 |
| Streamlit process 밖에서 장기 실행 agent가 필요한가? | 아직 아니다 |

그래서 내 의견은 이렇다.

> A2A는 v2 후보로 남긴다.  
> MVP에서는 쓰지 않는다.  
> 지금은 “멋진 구조”보다 “끝까지 구현 가능한 구조”가 더 중요하다.

### 2.3 Specialist boundary가 잘 잡혀 있다

PR #20의 가장 좋은 점은 agent별 책임이 비교적 선명하다는 점이다.

| 영역 | 내가 동의하는 기준 |
|------|-------------------|
| 계산 | LLM이 하지 않고 tools/DB가 한다 |
| 정성 근거 | RAG로 찾은 source에 기반한다 |
| 종합 판단 | Strategist가 담당한다 |
| 안전 검수 | Guardrail이 담당한다 |
| 최종 출력 | Tier 1/2/3가 서로 일관되어야 한다 |

이 원칙은 꼭 유지해야 한다. 특히 Quant가 숫자를 “그럴듯하게 말하는 agent”가 되면 안 된다. Quant는 계산 결과를 가져오고, LLM은 그 결과를 설명하는 데만 써야 한다.

---

## 3. 내가 우려하는 것

이 PR은 방향성은 좋지만, 그대로 구현에 들어가기에는 아직 비어 있는 결정들이 있다.

### 3.1 AgentState가 아직 “보고서-ready”인지 불명확하다

AgentState는 단순히 agent들이 주고받는 임시 메모가 아니다. 우리 제품에서는 나중에 Tier 1 카드, Tier 2 근거, Tier 3 PB report까지 만드는 재료가 된다.

그래서 AgentState는 처음부터 report-ready하게 설계해야 한다.

내가 요구하는 필드는 다음이다.

| 필드 | 왜 필요한가 |
|------|-------------|
| `request_id` | 분석 요청 하나를 추적하기 위해 필요 |
| `as_of_date` | 어느 날짜 기준 분석인지 표시하기 위해 필요 |
| `data_version` | 어떤 데이터 스냅샷을 썼는지 재현하기 위해 필요 |
| `mode` | cache, live, backtest, debug 실행 모드를 구분하기 위해 필요 |
| `evidence_bundle` | 최종 결론에 쓰인 출처 묶음을 남기기 위해 필요 |
| `cost_trace` | agent별 LLM 비용을 보기 위해 필요 |
| `errors` | 실패한 agent를 숨기지 않기 위해 필요 |
| `warnings` | 데이터 부족, 근거 부족을 사용자에게 보여주기 위해 필요 |

내 의견:

> AgentState는 개발자용 내부 객체가 아니라, PM이 최종 보고서 품질을 검수할 수 있는 계약이어야 한다.

### 3.2 Guardrail이 아직 구호처럼 보일 수 있다

“투자권유 표현을 막는다”, “수익 보장을 차단한다”는 방향은 맞다. 하지만 구현 전에는 더 구체화해야 한다.

팀이 답해야 할 질문은 이것이다.

- 어떤 문구가 금지 표현인가?
- 어떤 문구는 완화해서 통과시킬 수 있는가?
- 어떤 경우에는 아예 사용자에게 보여주면 안 되는가?
- disclaimer는 언제 붙이는가?
- Guardrail이 실패하면 결과를 block할 것인가, warning만 붙일 것인가?

내 의견:

> Guardrail은 마지막에 문장만 예쁘게 바꾸는 기능이 아니다.  
> 금융 분석 결과가 사용자에게 나가기 전에 “출고 검수”를 하는 단계다.

### 3.3 Evidence contract가 없으면 PB report가 약해진다

우리 제품의 설득력은 “BUY/HOLD/SELL” 자체가 아니라 “왜 그렇게 판단했는지”에서 나온다.

따라서 모든 정성 근거는 source와 연결되어야 한다.

최소한 다음 정보는 필요하다.

| 필드 | 설명 |
|------|------|
| `source_type` | news, disclosure, report, financial, macro |
| `title` | 출처 제목 |
| `url` 또는 `document_id` | 외부 링크 또는 내부 문서 ID |
| `published_at` | 출처 날짜 |
| `chunk_id` | RAG chunk 추적용 ID |
| `retrieval_score` | 검색 점수 |

내 의견:

> 출처 없는 정성 근거는 PB report에 들어가면 안 된다.  
> 출처가 부족하면 “근거 부족”이라고 말해야지, 그럴듯하게 채우면 안 된다.

### 3.4 Partial failure 정책이 필요하다

멀티 에이전트 구조에서는 일부 agent가 실패할 수 있다. 이때 모든 분석을 중단할지, 가능한 결과만 보여줄지 정해야 한다.

내 제안은 **Partial Success with Warnings**다.

| 상황 | 내 제안 |
|------|---------|
| Quant 실패, Qual/Competitor 성공 | 분석은 진행하되 정량 근거 부족 warning 표시 |
| Qual RAG 실패 | 정성 요약을 만들지 말고 source 부족 warning 표시 |
| Competitor 실패 | Peer 비교만 제외하고 진행 |
| Strategist 실패 | 최종 signal 생성 불가이므로 block |
| Guardrail 실패 | 사용자-facing 결과 block |

이유는 단순하다.

> 일부 데이터가 부족하다고 전체 경험을 죽이면 MVP 시연 안정성이 떨어진다.  
> 대신 부족한 부분을 솔직하게 보여주면 사용자도 결과를 더 잘 이해할 수 있다.

---

## 4. 내가 팀에 요구하는 결정 티켓

아래 항목들은 “나중에 구현하면서 정하자”로 두면 안 된다. 바로 GitHub/Jira issue로 분리해야 한다.

### NEED-DECISION-001

**Issue title:** `[Architecture] AgentState와 report-ready result schema 확정`

**내가 요구하는 결정:**

- AgentState에 `request_id`, `as_of_date`, `data_version`, `mode`, `evidence_bundle`, `cost_trace`, `errors`, `warnings`를 포함할지 결정한다.
- Tier 1/2/3 UI와 PB report를 만들 수 있는 result schema를 먼저 정의한다.

**쉬운 설명:**  
AgentState는 agent들의 공용 작업일지다. 작업일지가 부실하면 나중에 보고서도 부실해진다.

### NEED-DECISION-002

**Issue title:** `[Architecture] Evidence bundle과 source attachment contract 확정`

**내가 요구하는 결정:**

- source metadata 형식을 확정한다.
- Tier 2와 Tier 3의 핵심 문장은 source와 연결되게 한다.
- 출처 없는 주장은 Guardrail warning 또는 block 대상으로 둔다.

**쉬운 설명:**  
Evidence bundle은 보고서에 붙는 영수증이다. 영수증 없는 주장은 사용자에게 보여주면 안 된다.

### NEED-DECISION-003

**Issue title:** `[Guardrail] Input/Tool/Output Guardrail enforcement plan 확정`

**내가 요구하는 결정:**

- Input Guardrail이 막을 입력을 정한다.
- Tool Guardrail이 비용, DB 조회, 외부 API 호출을 어떻게 통제할지 정한다.
- Output Guardrail이 투자권유 표현, 수익 보장, 출처 없는 단정을 어떻게 막을지 정한다.
- disclaimer 부착 시점을 정한다.

**쉬운 설명:**  
Guardrail은 결과물이 사용자에게 나가기 전 마지막 검수대다.

### NEED-DECISION-004

**Issue title:** `[LLM] Cost trace와 월 5만원 상한 정책 구현 기준 확정`

**내가 요구하는 결정:**

- agent별 token/cost를 기록한다.
- 3만원, 4만원, 5만원 도달 시 동작을 정한다.
- cache hit 여부도 기록한다.

**쉬운 설명:**  
비용 추적은 가계부다. 가계부가 없으면 5만원 상한은 말뿐인 약속이 된다.

### NEED-DECISION-005

**Issue title:** `[Architecture] Partial Success with Warnings 정책 채택 여부 결정`

**내가 요구하는 결정:**

- 일부 agent 실패 시 전체 block하지 않고 warning과 함께 진행할 조건을 정한다.
- Strategist와 Guardrail 실패처럼 반드시 block해야 하는 조건을 정한다.

**쉬운 설명:**  
재료 하나가 부족하다고 식사를 전부 취소할지, 부족한 재료를 표시하고 가능한 메뉴를 낼지 정하는 문제다.

### NEED-DECISION-006

**Issue title:** `[Evaluation] MVP evaluation gate 확정`

**내가 요구하는 결정:**

MVP gate는 최소한 다음을 포함해야 한다.

| Gate | 내 제안 |
|------|---------|
| Schema Valid Rate | 95%+ |
| Source Attachment Rate | 95%+ |
| RAG Faithfulness | 0.80+ |
| Guardrail Block Rate | 금지 표현 100% 차단 |
| Tier Consistency | Tier 1과 Tier 3 결론 90%+ 일치 |
| Cost Per Run | 월 5만원 상한 내 |
| Latency | cache 5초, live 60초 목표 |

특히 Ragas metrics 중에서 내가 가장 중요하게 보는 것은 **Faithfulness(충실성)**이다.

쉬운 말로 하면:

> Qual agent가 RAG에서 찾은 근거 안에 있는 말만 해야 한다.  
> 검색 결과에 없는 내용을 만들어내면, 그것이 가장 위험한 hallucination이다.

---

## 5. 내가 참고한 외부 기준

이 리뷰는 단순히 개인 취향으로 쓴 것이 아니다. 현재 문서 방향이 업계의 일반적인 agent 설계 기준과 맞는지 확인했다.

| 기준 | 내가 가져온 판단 |
|------|------------------|
| LangGraph overview | stateful workflow와 tracing이 필요한 MVP에는 LangGraph가 적합하다. |
| LangGraph Send | Quant/Qual/Competitor 병렬 fan-out 구조와 잘 맞는다. |
| OpenAI Agents orchestration | manager가 specialist output을 모으는 방식이 우리 구조와 맞다. |
| OpenAI Agents guardrails | input/tool/output guardrail을 나누는 방향이 맞다. |
| Ragas metrics | RAG 품질은 Faithfulness를 우선 gate로 봐야 한다. |
| 금융분야 AI 보안 가이드라인 | 금융 AI는 데이터, 보안, 책임, 운영 통제가 중요하다. |
| FINRA Regulatory Notice 24-09 | model risk, data privacy, reliability, accuracy를 관리해야 한다. |

참고 링크:

- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- LangGraph Send: https://langchain-ai.github.io/langgraphjs/reference/classes/langgraph.Send.html
- OpenAI Agents orchestration: https://openai.github.io/openai-agents-python/multi_agent/
- OpenAI Agents guardrails: https://openai.github.io/openai-agents-python/guardrails/
- Ragas metrics: https://docs.ragas.io/en/latest/concepts/metrics/
- 금융분야 AI 보안 가이드라인: https://www.korea.kr/archive/expDocView.do?docId=40456
- FINRA Regulatory Notice 24-09: https://www.finra.org/rules-guidance/notices/24-09

---

## 6. 회의에서 내가 말할 문장

팀 회의에서는 길게 말하기보다 이렇게 말하면 된다.

```text
저는 PR #20의 큰 방향에는 동의합니다.
MVP에서는 Curator -> Quant/Qual/Competitor 병렬 -> Strategist -> Guardrail 구조를 기준선으로 잡는 게 맞다고 봅니다.

다만 이것은 구현 승인이라기보다는 architecture baseline 승인입니다.
구현 전에 AgentState, evidence contract, Guardrail enforcement, cost trace, partial failure policy, evaluation gate는 별도 이슈로 닫고 가야 합니다.

특히 MVP에서 A2A/full decentralized agents는 제외했으면 합니다.
지금 우리 구조는 Streamlit + Postgres + 단일 repo이기 때문에 central supervisor가 더 안전합니다.

또 하나 중요한 건 RAG Faithfulness입니다.
Qual agent가 검색된 근거에 없는 내용을 만들어내면 금융 분석 제품에서는 가장 위험한 문제가 됩니다.
그래서 Ragas Faithfulness를 MVP 최우선 evaluation gate로 두는 것을 제안합니다.
```

---

## 7. Copy-ready PR Comment

```text
PR #20 방향성에 동의합니다. MVP에서는 `Curator -> Quant/Qual/Competitor 병렬 fan-out -> Strategist -> Guardrail` 구조를 architecture baseline으로 삼는 것이 가장 안전하다고 봅니다.

다만 이 PR은 구현 승인이라기보다는 기준선 승인으로 보는 것이 좋겠습니다. 실제 구현 전에 아래 항목은 별도 이슈로 닫고 가는 것을 제안합니다.

1. `AgentState`와 result schema를 Tier 3 PB report/UI 렌더링까지 고려한 report-ready contract로 확정
2. source/evidence bundle 계약 확정
3. Guardrail의 input/tool/output enforcement 방식과 disclaimer 부착 시점 확정
4. agent별 cost_trace와 월 5만원 상한 정책 구현 기준 확정
5. partial failure는 "Partial Success with Warnings"로 진행할지 합의
6. Ragas Faithfulness를 Qual RAG hallucination 방지의 최우선 MVP evaluation gate로 설정

특히 MVP에서는 A2A/full decentralized agents는 제외했으면 합니다. 현재 시스템은 Streamlit + Postgres + 단일 repo 구조이므로 LangGraph central supervisor pattern이 비용, 디버깅, 재현성 측면에서 더 적합하다고 판단합니다.
```

