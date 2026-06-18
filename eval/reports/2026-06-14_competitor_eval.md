# Competitor peer 비교 품질 회귀 리포트 — 2026-06-14

- 스위트: peer 선정·상대위치 점수 엔진(LLM·DB·네트워크 미사용)
- 통과: **6/6**

## 케이스별 결과

### ✅ C1_normal_comparison — 정상 비교 — 시총·지표가 가까운 peer 3개, 충분한 데이터 품질

- 선정 peer: `['DDD001', 'CCC001', 'BBB001']`
- score: **54**
- data_quality_flags: []

### ✅ C2_market_cap_band_filter — 시총 band 거름 — 4배 초과 대형 peer는 비교군에서 제외되어 peer 부족 경고 발생

- 선정 peer: `['CCC002', 'BBB002']`
- score: **61**
- data_quality_flags: ['peer_count_below_minimum']

### ✅ C3_outlier_metric_flag — 이상치 표기 — peer 중앙값 10배 초과 PER 후보에 outlier_per 플래그 부여

- 선정 peer: `['OUTL03', 'CCC003', 'BBB003']`
- score: **64**
- outlier 플래그: ['outlier_per']
- data_quality_flags: []

### ✅ C4_no_comparable_peers — 비교군 없음 — peer 후보가 전혀 없어 score 0, no_comparable_peers

- 선정 peer: `[]`
- score: **0**
- data_quality_flags: ['no_comparable_peers', 'peer_count_below_minimum']

### ✅ C5_low_quality_target_cap — 저품질 타깃 캡 — 타깃 데이터 완성도 60 미만이면 score 55로 상한

- 선정 peer: `['DDD005', 'CCC005', 'BBB005']`
- score: **49**
- data_quality_flags: ['target_data_quality_low']

### ✅ C6_similarity_ordering — 복합 유사도 정렬(#62) — 시총·사업경제성이 동일한 peer가 데이터완성도만 높은 peer보다 우선

- 선정 peer: `['SIZEMATCH', 'MIDPEER', 'QUALONLY']`
- score: **61**
- data_quality_flags: []
