# 기능 명세서 v0.1

| 항목 | 값 |
|------|-----|
| 작성자 | PM |
| 작성일 | 2026-05-10 |
| 버전 | v0.1 |
| 상위 문서 | `docs/prd/PRD_v0.6.md` |
| 대상 독자 | 개발팀 + 다른 PM |

---

## 0. 이 문서의 위치 / 양식

본 문서는 PRD에서 정의한 11개 기능(B1~B5 기본 + A1~A6 고급) 각각의 *상세 동작* 을 정의합니다. 양식은 다음 7개 항목 고정:

| 항목 | 의미 |
|------|------|
| **트리거** | 이 기능이 시작되는 사용자 행동 또는 이벤트 |
| **전제조건** | 이 기능이 동작하려면 미리 만족돼야 할 조건 (로그인 여부 등) |
| **입력** | 사용자/시스템이 제공하는 데이터 |
| **처리 흐름** | 1단계씩 무엇이 일어나는지 |
| **출력** | 사용자에게 보이는 것 + 시스템에 저장되는 것 |
| **예외 처리** | 잘못된 입력·실패·경계 케이스 시 동작 |
| **담당** | 어느 에이전트·테이블·UI 영역 |

---

# 🟢 [기본 기능] B1~B5 (Phase 1 — 7~8주차)

## B1. 회원가입 / 로그인

### 트리거
- 신규 유저: 홈 화면 "회원가입" 버튼 클릭
- 기존 유저: "로그인" 버튼 클릭

### 전제조건
- Postgres `users` 테이블 존재
- 이메일 중복 체크 기능

### 입력
| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| email | string | ✅ | 형식 검증 |
| password | string | ✅ | 8자 이상 |
| name | string | ✅ | 한글 가능 |
| birth_date | date | ✅ | YYYY-MM-DD |
| risk_profile | enum | ✅ | 보수/중립/공격 |
| investment_horizon | enum | ✅ | 단기/중기/장기 |
| target_return | float | ✅ | 0.05~0.30 |
| max_drawdown_tolerance | float | ✅ | -0.05 ~ -0.30 |
| interest_sectors | list | ✅ | [반도체, 금융, 소비재] 중 1개 이상 |

### 처리 흐름
1. 입력 검증 (이메일 형식, 비밀번호 길이, 비중 합 ≤1.0)
2. 가드레일: 이름·생년월일 PII 마스킹 후 로그
3. 비밀번호 bcrypt 해싱 (salt round 12)
4. Postgres `users` 테이블에 INSERT
5. 세션 토큰 발급 (Streamlit `st.session_state`)
6. 홈 화면 리다이렉트

### 출력
| 대상 | 내용 |
|------|------|
| 사용자 | "환영합니다, OOO님" + 다음 단계 안내 |
| DB | `users` 한 행 추가 |
| 로그 | 회원가입 이벤트 (PII 마스킹) |

### 예외 처리
- 이메일 중복 → "이미 가입된 이메일입니다"
- 비밀번호 8자 미만 → "비밀번호는 8자 이상" + 입력 폼 유지
- 투자성향 미선택 → "투자성향을 선택해주세요"
- DB 연결 실패 → "잠시 후 다시 시도해주세요" + 에러 로그

### 담당
- UI: `streamlit_app.py` (회원가입·로그인 폼은 진입점 홈에 위치)
- 에이전트: Guardrail (PII 마스킹)
- DB: `users` 테이블

---

## B2. 보유 종목 등록 / 조회

### 트리거
- 로그인 후 "보유 종목 관리" 메뉴 클릭

### 전제조건
- 로그인 완료
- 종목 마스터(`company` 테이블) 적재 완료 — 데이터팀 7주차 작업

### 입력 (등록 시)
| 필드 | 타입 | 필수 | 비고 |
|------|------|------|------|
| stock_code | string(6) | ✅ | 자동완성 검색 |
| avg_price | int | ✅ | 평균 매수가 (원) |
| qty | int | ✅ | 수량 |
| bought_at | date | ⚪ | 매수일 (선택) |
| memo | text | ⚪ | 본인 메모 |

또는 CSV 업로드 (헤더: stock_code, avg_price, qty, bought_at, memo)

### 처리 흐름
1. 입력 검증 (종목코드 6자리, 양수 가격·수량)
2. `company` 테이블에서 stock_code 존재 여부 확인 → 없으면 "지원 안 함" 에러
3. **MVP 섹터 검증**: 종목의 sector가 [반도체, 금융, 소비재] 외면 경고 표시 (저장은 가능)
4. Postgres `holdings` 테이블에 INSERT (또는 BULK INSERT for CSV)
5. 비중 자동 계산: `weight = (avg_price × qty) / total_value`
6. 화면 갱신

### 출력
| 대상 | 내용 |
|------|------|
| 사용자 | 보유 종목 표 + 비중 파이 차트 + 평가손익 (실시간 시세 적용) |
| DB | `holdings` 행 추가/갱신 |

### 예외 처리
- 존재하지 않는 종목코드 → "종목 없음" + 자동완성 제안
- 비중 합 > 100% → "비중 초과 — 정규화 처리됨" 경고
- CSV 형식 오류 → 어느 줄이 잘못됐는지 표시

### 담당
- UI: `streamlit_app.py` (홈 화면 포트 입력 섹션) + 별도 `pages/4_보유종목_관리.py` 가능
- 에이전트: 없음 (단순 CRUD)
- DB: `holdings`, `company`

---

## B3. 종목 검색

### 트리거
- 검색창에 종목명 또는 티커 입력 (2글자 이상)

### 전제조건
- `company` 테이블 적재

### 입력
| 필드 | 타입 | 비고 |
|------|------|------|
| query | string | "삼성", "005930", "삼전" 등 자유 입력 |

### 처리 흐름
1. 입력 정제 (공백 제거, 소문자 통일)
2. `company` 테이블에서 LIKE 검색 (corp_name, stock_code, 별칭)
3. 시총 내림차순 정렬, 상위 10개 표시
4. **MVP 섹터 종목 우선** (반도체·금융·소비재) → 그 외는 회색 표시

### 출력
| 대상 | 내용 |
|------|------|
| 사용자 | 자동완성 드롭다운 (종목명·티커·섹터·시총·현재가·등락률) |

### 예외 처리
- 검색 결과 0건 → "검색 결과 없음 — 다른 키워드를 시도해보세요"
- 1글자 입력 → 검색 안 함 (성능 보호)

### 담당
- UI: 검색 컴포넌트 (`ui/components/search_box.py`)
- 에이전트: Quant Worker (시세·재무 단순 조회)
- Tool: `pykrx_tool.py` (시세)
- DB: `company`, `stock_price`

---

## B4. 종목 기본 정보 조회

### 트리거
- 검색 결과에서 종목 클릭 또는 보유 종목 표에서 종목명 클릭

### 전제조건
- 종목 코드 확정
- 시세·뉴스 데이터 적재 (또는 캐시)

### 입력
| 필드 | 타입 | 비고 |
|------|------|------|
| stock_code | string(6) | |

### 처리 흐름
1. Postgres에서 종목 메타·재무·시세 조회
2. Postgres `rag_documents`/`rag_chunks`에서 최근 7일 뉴스 헤드라인 검색
3. 1년 차트 데이터 가공 (matplotlib·plotly)
4. PER/PBR/ROE/배당수익률 계산 (Python)
5. 기관·외국인 매매 동향 (pykrx)
6. 화면 렌더링

### 출력
| 대상 | 내용 |
|------|------|
| 사용자 | (1) 1년 주가 차트 (2) 핵심 재무지표 카드 (3) 매매 동향 표 (4) 최근 7일 뉴스 헤드라인 5건 |

### 예외 처리
- 시세 데이터 결손 (휴장·신규상장) → "데이터 부족 표시" + 가용 기간만 표시
- 재무 데이터 미보고 (신규상장) → "공시 전" 표기
- 뉴스 0건 → "최근 뉴스 없음" 표기

### 담당
- UI: `streamlit_app.py` 내 모달 또는 `pages/0_종목_상세.py`
- 에이전트: Quant Worker (재무·시세) + Qual Worker (뉴스 캐시)
- DB: `company`, `financial_data`, `stock_price`, `rag_documents`, `rag_chunks`

---

## B5. 포트폴리오 일괄 안내

### 트리거
- 홈 화면 진입 시 자동 표시
- 또는 "포트폴리오 보기" 메뉴 클릭

### 전제조건
- 로그인
- `holdings` 테이블에 1개 이상 종목

### 입력
| 필드 | 타입 | 비고 |
|------|------|------|
| user_id | uuid | 세션에서 가져옴 |

### 처리 흐름
1. `holdings` 테이블 user_id로 조회
2. 각 종목 현재가 조회 (`stock_price.close_price`)
3. 평가손익 계산: `(현재가 − avg_price) × qty`
4. 섹터별 그룹핑 → 파이 차트 데이터 가공
5. 전체 평가액 / 총 손익 / 평균 수익률 집계
6. 화면 렌더링

### 출력
| 대상 | 내용 |
|------|------|
| 사용자 | (1) 종목별 평가손익 표 (2) 섹터 비중 파이 차트 (3) 전체 요약 카드 (총 평가액·총 손익·평균 수익률) |

### 예외 처리
- 보유 종목 0개 → "보유 종목을 추가해주세요" 빈 상태 화면
- 시세 결손 종목 → 평가손익 계산에서 제외 + "데이터 갱신 중" 표시

### 담당
- UI: `streamlit_app.py` (포트폴리오 섹션) + `ui/components/portfolio_summary.py`
- 에이전트: Quant Worker (시세·집계 — 단순 SQL)
- DB: `holdings`, `stock_price`, `company`

---

# 🔵 [고급 기능] A1~A6 (Phase 2 — 9~11주차)

## A1. 5개년 밸류에이션

### 트리거
- "이 종목 분석하기" 버튼 클릭 (B4 화면에서)

### 전제조건
- DART 5년 재무 적재 완료
- pykrx 시세 적재 완료
- Quant Worker 구현 완료

### 입력
| 필드 | 타입 | 비고 |
|------|------|------|
| stock_code | string(6) | |
| user_id | uuid | (가정 슬라이더 사용 이력 추적) |

### 처리 흐름
1. **데이터 수집** (Python, LLM 호출 X)
   - Postgres에서 5y 손익·BS·CF 조회
   - 시세·시총 조회
2. **재무 모델링** (Python — Quant Worker)
   - 매출·OPM·EPS·FCF 5y 추정 (보수/기본/낙관 3 시나리오)
   - DCF: WACC + g 가정 → 미래 FCF 할인 → 적정가 산출
   - 상대가치: Peer PER/PBR 평균 × EPS/BPS → 적정가 산출
   - DDM: 배당주만 (배당성향 안정 시) → 적정가 산출
   - 가중평균: 3 방법론 평균 → 시나리오별 적정가
3. **자연어 설명 생성** (LLM 호출 1회 — Quant Worker)
   - "5y 가정과 시나리오별 결과를 한 문단으로 요약"
4. **Excel 8시트 생성** (Python — openpyxl)
   - Sheet 1 가정·Sheet 2~4 IS/BS/CF·Sheet 5 DCF·Sheet 6 상대가치·Sheet 7 시나리오·Sheet 8 민감도
5. **Pydantic 스키마 검증** (`QuantReport`)

### 출력
| 대상 | 내용 |
|------|------|
| 사용자 (Tier 2) | 시나리오별 적정가 표 + 가중평균 + MoS |
| 사용자 (다운로드) | `valuation_workbook.xlsx` 8시트 |
| LangGraph State | `QuantReport` (Strategist 입력) |

### 예외 처리
- 5년 데이터 결손 (3년 이상 있어야 진행) → 가용 기간 명시 + 분석은 진행
- 음(-) 영업이익 누적 → DCF 계산 불가 → 상대가치만 사용
- 무배당 → DDM 제외 (DCF + 상대가치 가중평균)

### 담당
- 에이전트: **Quant Worker ⭐**
- Tool: `dart_tool.py`, `pykrx_tool.py`
- DB: `financial_data`, `stock_price`, `company`
- 출력: Excel 다운로드 (`scripts/generate_excel.py`)

---

## A2. 산업·정성 분석

### 트리거
- A1과 동시 실행 (LangGraph Send API)

### 전제조건
- 데이터팀 뉴스 수집 완료 (네이버·한경·매경)
- Sanitizer 통과한 본문이 Postgres `rag_documents`와 `rag_chunks`에 적재

### 입력
| 필드 | 타입 | 비고 |
|------|------|------|
| stock_code | string(6) | |
| analysis_period_days | int | 기본 30일 |

### 처리 흐름
1. **뉴스 RAG** (LLM 호출 1회 — Qual Worker)
   - Postgres `rag_chunks`에서 stock_code 필터로 Hybrid Search (keyword + pgvector)
   - Reranker로 상위 30개 청크 정렬
2. **호재/악재 분류** (LLM 호출 1회)
   - 9 이벤트 유형으로 분류 (실적·수주·신사업·규제·소송·M&A·경영진·산업·증권사 리포트)
   - 감성 라벨 (positive/negative/neutral)
3. **DART 사업보고서 RAG** (LLM 호출 1회)
   - Postgres `rag_chunks`에서 공시 청크 검색
   - 사업의 내용·MD&A·중대공시 추출
4. **출처 부착 검증** (Source Tracker — 자동)
   - 모든 주장에 [출처: URL + 크롤링시각] 강제
   - 미부착 시 ValueError → 재시도
5. **HTML 생성** (Jinja2 템플릿)
   - 8섹션 (산업/사업구조/뉴스 타임라인/공시 RAG/경쟁사/매크로/ESG/Glossary)

### 출력
| 대상 | 내용 |
|------|------|
| 사용자 (Tier 2) | 호재/악재 카드 + 최근 7일 타임라인 |
| 사용자 (다운로드) | `analysis_report.html` 인터랙티브 뷰어 |
| LangGraph State | `QualReport` |

### 예외 처리
- 뉴스 0건 → "최근 30일 뉴스 없음" 카드 표시
- DART 공시 0건 → "공시 데이터 없음" 표시
- 출처 부착률 95% 미만 → 부족분만 재검색 (1회 재시도)
- LLM 응답 스키마 위반 → 1회 재시도 후 부분 결과로 진행

### 담당
- 에이전트: **Qual Worker ⭐ (W1+W3 핵심)**
- Tool: `news_tool.py`, `dart_tool.py`
- DB: Postgres `rag_documents`, `rag_chunks`, `disclosure`
- 출력: HTML 다운로드

---

## A3. 동종업계 횡비교

### 트리거
- A1·A2와 동시 실행

### 전제조건
- `company.sector` 적재
- Peer 종목들도 `financial_data`·`stock_price` 적재

### 입력
| 필드 | 타입 | 비고 |
|------|------|------|
| stock_code | string(6) | |

### 처리 흐름
1. **Peer 추출** (Python)
   - `company.sector` GROUP BY → 같은 섹터 종목 리스트
   - 시총 상위 ≥3개 선정
2. **재무 비교** (LLM 호출 1회)
   - 각 Peer의 PER/PBR/ROE/매출성장 조회
   - Heatmap 형태 표 생성
3. **해석** (LLM 호출 1회)
   - "이 종목이 Peer 대비 어떤 위치인가" 자연어 요약
4. **포터 5 Forces 정리** (Phase 2 후반 옵션)

### 출력
| 대상 | 내용 |
|------|------|
| 사용자 (Tier 2) | Peer Heatmap + 위치 요약 |
| LangGraph State | `CompetitorReport` |

### 예외 처리
- Peer 데이터 부족 (3개 미만) → 가용 Peer만 비교 + "Peer 부족" 표시
- MVP 섹터 외 종목 → 분석 진행하되 "Peer 데이터 제한적" 경고

### 담당
- 에이전트: **Competitor Agent**
- Tool: `dart_tool.py` (KSIC), `pykrx_tool.py` (시총)
- DB: `company`, `financial_data`, `stock_price`

---

## A4. BUY / HOLD / SELL 권유

### 트리거
- A1·A2·A3 모두 완료 후 자동 실행

### 전제조건
- A1·A2·A3의 `QuantReport`, `QualReport`, `CompetitorReport` 완료
- 사용자 프로필 + 포트 조회 완료

### 입력 (LangGraph State)
- `QuantReport` (적정가·MoS·시나리오)
- `QualReport` (호재/악재 가중치)
- `CompetitorReport` (Peer 위치)
- `UserProfile` (성향·목표·집중도)
- `Macro context` (금리·환율·CPI)

### 처리 흐름 (Strategist & Synthesizer Agent)
1. **종합 합성** (LLM 호출 1회)
   - 4 입력 통합 → 1차 BUY/HOLD/SELL 결정
   - 신뢰도 계산 (Pydantic 강제)
2. **자체 검증 — 5 시각 자체 검토** (LLM 호출 1회)
   - 회계 보수/매크로 비관/경쟁 회의/규제ESG/모멘텀
   - 약점 발견 시 결론·신뢰도 다운그레이드
3. **포트폴리오 적합도 매칭** (Python)
   - 사용자 보유 비중·섹터 집중도 비교
   - ★1~★5 적합도 산정
4. **3축 트리거 적용** (Python — Action Engine)
   - 축 A: MoS 임계치
   - 축 B: 신뢰도 임계치 (60% 미만 시 HOLD 강제)
   - 축 C: 적합도 (★1 시 HOLD 강제)
5. **4슬롯 설명 자동 생성** (LLM 호출 1회)
   - WHAT (액션·신뢰도·적합도)
   - HOW MUCH (적정가·MoS·권유 비중)
   - WHY (5개 차원 근거)
   - RISK (Critic 발견 약점)
6. **Pydantic 스키마 검증** (`ActionRecommendation`)

### 출력
| 대상 | 내용 |
|------|------|
| 사용자 (Tier 1) | "BUY 78% · ★★★★ · 현금 30% 중 5%p 매수 권장" |
| 사용자 (Tier 2) | 4슬롯 설명 (WHAT/HOW MUCH/WHY/RISK) |
| DB | `analysis_history` 한 행 추가 |
| LangGraph State | `ActionRecommendation` |

### 예외 처리
- 4 입력 중 1개 결손 → 부분 결정 + "근거 부족" 신뢰도 강제 60% 미만
- 모든 시나리오에서 손실 예상 → "매수 비추천" 명확 표시
- BUY 결정인데 신뢰도 60% 미만 → HOLD 다운그레이드
- BUY인데 적합도 ★1 → HOLD 강제

### 담당
- 에이전트: **Strategist & Synthesizer ⭐**
- DB: `users`, `holdings`, `analysis_history`

---

## A5. 종목 추천 (Curator)

### 트리거
- 사용자가 종목 미지정으로 "오늘 뭐 사지?" 입력
- Curator Agent가 의도 파싱에서 "종목 미지정" 판단

### 전제조건
- `company` 테이블 + `stock_price` 시총 데이터
- 사용자 프로필 (관심 섹터)

### 입력
| 필드 | 타입 | 비고 |
|------|------|------|
| user_query | string | 자연어 |
| user_id | uuid | 관심 섹터 가져오기 |

### 처리 흐름
1. **의도 파싱** (LLM 호출 1회 — Curator)
   - 종목 명시 여부 판단
   - 시나리오 추출 (단기·장기·배당·성장 등)
2. **종목 universe 필터링** (Python)
   - MVP 섹터 (반도체·금융·소비재) 한정
   - 시총 상위 + 거래대금 ≥ 임계치
   - 사용자 관심 섹터 우선
3. **후보 큐레이션** (LLM 호출 1회)
   - 5~10 종목 + 각각 추천 사유 한 줄
4. **카드 UI 렌더링**

### 출력
| 대상 | 내용 |
|------|------|
| 사용자 | 5~10 후보 카드 (종목명·섹터·현재가·등락률·추천 사유) |
| LangGraph State | 사용자 선택 종목 → A1~A4 진입 |

### 예외 처리
- 사용자 관심 섹터 미설정 → 3섹터 균등 추천
- 모든 종목 거래정지 → "오늘 추천 가능 종목 없음" 안내

### 담당
- 에이전트: **Curator Agent**
- Tool: `pykrx_tool.py`, `dart_tool.py`
- DB: `company`, `stock_price`, `users.interest_sectors`

---

## A6. PB 리포트 다운로드

### 트리거
- A4 완료 후 사용자가 "PB 리포트 받기" 버튼 클릭

### 전제조건
- A1·A2·A3·A4 모두 완료
- WeasyPrint·python-docx 설치

### 입력 (LangGraph State)
- `QuantReport`, `QualReport`, `CompetitorReport`, `ActionRecommendation`
- `UserProfile`

### 처리 흐름
1. **7페이지 본문 생성** (LLM 호출 1회 — Strategist)
   - P1 Cover (목표가·투자의견·요약)
   - P2 Executive Summary (Thesis 3줄)
   - P3 Industry (산업·CAGR·Mermaid)
   - P4 Company (사업·실적·지배구조)
   - P5 Points & Risks (초록·빨강 박스)
   - P6 Valuation (보수/기본/낙관 표)
   - P7 Conclusion + Disclaimer + 평가지표
2. **PDF 생성** (WeasyPrint, HTML+CSS)
3. **DOCX 생성** (python-docx, 동일 본문)
4. **표준 푸터 자동 부착** (Disclaimer + 책임 고지)
5. **Guardrail 마지막 검증**

### 출력
| 대상 | 내용 |
|------|------|
| 사용자 | `report_<ticker>_<YYYYMMDD>.pdf` 다운로드 |
| 사용자 | `report_<ticker>_<YYYYMMDD>.docx` 다운로드 |

### 예외 처리
- WeasyPrint 한글 폰트 누락 → Pretendard 임베드 fallback
- A4 결과 없음 → "분석 먼저 실행해주세요" 안내
- 본문 생성 실패 → 1회 재시도 후 부분 리포트 (Cover + Summary 만)

### 담당
- 에이전트: **Strategist** (본문 생성) + **Guardrail** (최종 검증)
- 라이브러리: `weasyprint`, `python-docx`, `jinja2`
- 출력: 다운로드

---

# 부록 — 기능 ↔ 에이전트 ↔ DB 매핑 (한눈)

| 기능 | 메인 에이전트 | 보조 에이전트 | 사용 DB | LLM 호출 |
|------|----------------|----------------|---------|----------|
| B1 회원가입 | — | Guardrail (PII) | `users` | 0 |
| B2 보유종목 | — | — | `holdings`, `company` | 0 |
| B3 검색 | Quant (단순 조회) | — | `company`, `stock_price` | 0 |
| B4 기본정보 | Quant + Qual (캐시) | — | `company`, `financial_data`, `stock_price`, `rag_chunks` | 0 (캐시) |
| B5 포트 일괄 | Quant (집계) | — | `holdings`, `stock_price` | 0 |
| A1 5y 밸류 | **Quant ⭐** | — | `financial_data`, `stock_price` | 1 |
| A2 정성 분석 | **Qual ★** | — | `rag_chunks`, `disclosure` | 3 |
| A3 Peer | Competitor | Quant | `company`, `financial_data` | 2 |
| A4 BUY/HOLD/SELL | **Strategist ⭐** | Curator (입력 파싱) | `users`, `holdings`, `analysis_history` | 3 |
| A5 종목 추천 | Curator | — | `company`, `stock_price` | 2 |
| A6 PB 리포트 | Strategist | Guardrail | (위 모두) | 1 |
| 횡단 | Guardrail (RAGAS) | — | `eval/golden_set` | 1 (백그라운드) |

**1회 분석 (A1+A2+A3+A4+A6) 총 LLM 호출: ~13회 → 약 36원 (gpt-4o-mini 기준)**

---

## 변경 이력

| 날짜 | 버전 | 변경 |
|------|------|------|
| 2026-05-10 | v0.1 | 초안 — 11 기능 (B1~B5 + A1~A6) 7항목 양식 |
