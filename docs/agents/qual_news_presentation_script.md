# Qual News RAG 발표 대본

> 발표자: 팀장님  
> 담당 파트: 김도예  
> 같이 열 파일: `docs/agents/qual_news_presentation.html`

## 30초 요약

김도예님 파트는 뉴스 데이터를 단순히 수집하는 데서 끝내지 않고, Qual Agent가 실제 분석 근거로 사용할 수 있게 만드는 역할을 담당했습니다.

전체 흐름은 `raw_news -> rag_documents -> rag_chunks`로 이어집니다. 수집된 뉴스는 검색 가능한 문서로 정리되고, 다시 chunk 단위로 나뉘어 `BAAI/bge-m3` 임베딩으로 저장됩니다. 이후 Qual Agent는 pgvector 의미 검색과 키워드 검색을 함께 수행하고, RRF 방식으로 두 검색 결과를 합쳐 evidence와 risk를 만듭니다.

검색 평가 결과는 Hit@5 1.0, MRR 1.0, nDCG@5 0.9265로 검색 자체는 안정적으로 동작했습니다. 다만 RAGAS faithfulness는 0.4096으로 목표치보다 낮아서, 최종 생성 문장이 검색 근거를 더 충실히 반영하도록 인용 span과 context gating을 강화하는 것이 다음 개선 과제입니다.

## 1분 발표 대본

이 화면은 김도예님이 담당한 뉴스 RAG 기반 Qual Agent 흐름입니다.

먼저 왼쪽부터 보면, `news_collector.py`가 종목별 뉴스를 수집합니다. 이 데이터는 원본 보관용 `raw_news`에 저장되고, 검색에 바로 쓸 수 있도록 `rag_documents`에도 문서 단위로 저장됩니다.

그 다음 `embed_news.py`가 문서를 chunk로 나누고, `BAAI/bge-m3` 모델로 1024차원 임베딩을 생성해서 `rag_chunks`에 저장합니다. 여기까지가 뉴스 데이터를 RAG 검색 가능한 형태로 만드는 준비 단계입니다.

실제 분석 시점에는 Qual Agent가 이 데이터를 검색합니다. 단순 키워드 검색만 쓰는 것이 아니라, pgvector 기반 의미 검색과 키워드 검색을 같이 수행하고, RRF 방식으로 순위를 합칩니다. 그래서 기사 제목이나 키워드가 정확히 일치하지 않아도 의미적으로 관련 있는 근거를 찾을 수 있습니다.

그리고 필요할 경우 CrossEncoder reranker를 켜서 검색 후보를 한 번 더 재정렬할 수 있게 만들었습니다. 기본값은 꺼져 있어서 로컬 실행이나 테스트가 무겁지 않고, 평가나 운영 환경에서 선택적으로 사용할 수 있습니다.

마지막으로 Qual Agent는 검색된 뉴스와 공시 근거를 evidence와 risk로 바꾸고, sentiment와 score를 계산해서 Strategist Agent로 넘깁니다. DB나 검색 단계에서 문제가 생겨도 Agent가 바로 실패하지 않고 fallback evidence와 이유를 남기도록 처리했습니다.

정리하면, 이 파트의 핵심은 뉴스 수집, 임베딩 저장, Hybrid 검색, fallback까지 연결해서 Qual Agent가 실제 근거 기반 정성 분석을 할 수 있게 만든 것입니다. 검색 평가는 Hit@5 1.0, MRR 1.0, nDCG@5 0.9265로 안정적이었고, 앞으로는 RAGAS faithfulness를 올리기 위해 최종 답변의 인용 밀도와 context 반영을 강화할 계획입니다.

## 2분 발표 대본

김도예님 파트는 뉴스 RAG와 Qual Agent 연결입니다. 이 파트에서 해결하려고 한 문제는 "뉴스를 수집했더라도, Agent가 실제 분석 근거로 쓰지 못하면 정성 분석 품질이 올라가지 않는다"는 점이었습니다.

그래서 구현 흐름을 데이터 준비와 Agent 실행으로 나눴습니다.

첫 번째는 데이터 준비입니다. `datas/news/news_collector.py`가 종목별 뉴스를 수집하고, 수집 원본은 `raw_news`에 저장합니다. 이 테이블은 재처리와 디버깅을 위한 원본 보관소 역할입니다. 동시에 Qual Agent가 검색할 수 있도록 `rag_documents`에도 뉴스 제목, 요약, URL, 발행일, 종목 코드 같은 메타데이터를 정리해서 저장합니다.

두 번째는 임베딩 단계입니다. `datas/news/embed_news.py`가 `rag_documents`의 문서를 가져와 chunk로 나누고, `BAAI/bge-m3` 모델로 1024차원 임베딩을 생성합니다. 이 결과는 `rag_chunks`에 저장됩니다. 이 구조 덕분에 뉴스가 단순 텍스트가 아니라 pgvector 검색이 가능한 근거 데이터가 됩니다.

세 번째는 검색 단계입니다. `src/stock_agent/rag/retriever.py`에서 query embedding을 만들고, pgvector의 vector similarity 검색과 PostgreSQL keyword search를 함께 수행합니다. 그리고 RRF, Reciprocal Rank Fusion으로 두 검색 결과를 합칩니다. 이 방식은 의미 검색의 장점과 키워드 검색의 장점을 같이 가져가기 위한 선택입니다.

여기에 선택형 reranker도 추가했습니다. 환경 변수 `RAG_RERANKER_ENABLED`를 켜면 CrossEncoder가 Hybrid 검색 후보를 다시 정렬합니다. 기본값은 꺼져 있어서 일반 실행은 가볍게 유지하고, 발표나 평가 환경에서는 더 정밀한 검색으로 확장할 수 있습니다.

마지막으로 `src/stock_agent/agents/qual.py`가 검색 결과를 받아 정성 분석 결과로 바꿉니다. 뉴스와 공시 근거를 evidence와 risk로 나누고, sentiment, event type, qual score를 계산해서 `QualResult`로 반환합니다. 이 결과는 Strategist Agent가 Quant, Competitor, Macro 결과와 함께 종합하는 입력이 됩니다.

에러 처리도 포함했습니다. DB 연결이나 검색에서 문제가 생기면 전체 파이프라인이 중단되지 않도록 fallback evidence를 만들고, `fallback_reason`을 결과에 남깁니다. 그래서 발표 때는 "Qual Agent가 외부 데이터 의존성을 가지고 있지만 실패를 관리하는 구조로 바뀌었다"고 설명하면 됩니다.

평가 결과도 있습니다. `eval/run_rag_retriever_eval.py` 기준으로 뉴스 RAG 검색은 Hit@5 1.0, MRR 1.0, nDCG@5 0.9265가 나왔습니다. 즉 검색 자체는 근거를 상위에 잘 올리고 있습니다.

다만 전체 생성 결과의 RAGAS faithfulness는 0.4096으로 목표 0.80에는 부족합니다. 이건 검색 실패라기보다는 최종 생성 문장이 검색 근거를 충분히 인용하지 못하는 문제로 해석하고 있습니다. 다음 개선 방향은 인용 span을 강화하고, 검색 context가 최종 답변에 반드시 반영되도록 context gating을 추가하는 것입니다.

마무리 멘트는 이렇게 가져가면 좋습니다.

김도예님 파트는 뉴스 데이터를 Agent가 사용할 수 있는 RAG 근거로 바꾸는 역할을 했습니다. 현재는 수집, 임베딩, Hybrid 검색, fallback, 검색 평가까지 연결되어 있고, 앞으로는 검색된 근거가 최종 답변에 더 충실히 반영되도록 생성 품질을 높이는 단계가 남아 있습니다.

## 질문 대응

### Q. 기존에는 뭐가 문제였나요?

뉴스가 수집되더라도 임베딩 기반 검색까지 안정적으로 이어지지 않으면 Agent가 의미 기반 근거를 찾기 어렵습니다. 이번 작업으로 `rag_documents -> rag_chunks.embedding -> Hybrid/RRF 검색 -> Qual evidence` 흐름을 연결했습니다.

### Q. 왜 vector 검색만 쓰지 않고 keyword 검색도 같이 쓰나요?

금융 뉴스는 종목명, HBM, 실적, 리콜, 수주 같은 키워드가 중요합니다. vector 검색은 의미 유사도에 강하지만 특정 키워드를 놓칠 수 있어서, keyword rank와 합치는 Hybrid/RRF 구조를 사용했습니다.

### Q. Reranker는 항상 켜져 있나요?

아닙니다. 기본값은 꺼져 있습니다. CrossEncoder reranker는 정확도에는 도움이 되지만 모델 로딩 비용이 있으므로, `RAG_RERANKER_ENABLED=true`일 때만 켜지도록 했습니다.

### Q. 평가 결과는 어떻게 봐야 하나요?

검색 자체는 Hit@5 1.0, MRR 1.0, nDCG@5 0.9265로 안정적입니다. 다만 RAGAS faithfulness는 0.4096이라, 검색된 근거를 최종 답변이 더 잘 인용하도록 개선해야 합니다.

### Q. 다음으로 뭘 하면 점수가 더 오르나요?

케이스별 reference를 채워 context_recall을 측정하고, 최종 답변에 evidence 출처를 더 명시적으로 반영하는 context gating을 넣는 것이 가장 직접적입니다.
