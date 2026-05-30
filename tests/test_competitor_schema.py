from stock_agent.schemas.analysis import CompetitorResult


def test_competitor_result_accepts_a3_optional_fields() -> None:
    result = CompetitorResult(
        score=62,
        peer_summary="Peer 대비 수익성은 중립, 재무 안정성은 우위입니다.",
        peers=[
            {
                "stock_code": "005930",
                "corp_name": "삼성전자",
                "per": 18.4,
                "pbr": 1.35,
                "roe": 7.8,
            }
        ],
        evidence=["PBR은 peer 중앙값과 유사합니다."],
        peer_selection_summary="같은 섹터에서 시가총액과 데이터 완성도를 기준으로 3개 peer를 선정했습니다.",
        metric_definitions={"per": "market_cap / net_income"},
        relative_position={"roe_percentile": 0.55, "valuation_percentile": 0.48},
        data_quality_flags=["peer_count_ok"],
        a1_peer_multiple_payload={"median_per": 18.4, "median_pbr": 1.35},
        warnings=["일부 peer의 성장률 데이터가 제한적입니다."],
    )

    assert result.score == 62
    assert result.peer_selection_summary is not None
    assert result.metric_definitions["per"] == "market_cap / net_income"
    assert result.relative_position["roe_percentile"] == 0.55
    assert result.data_quality_flags == ["peer_count_ok"]
    assert result.a1_peer_multiple_payload == {"median_per": 18.4, "median_pbr": 1.35}
    assert result.warnings == ["일부 peer의 성장률 데이터가 제한적입니다."]


def test_competitor_result_keeps_existing_minimal_contract() -> None:
    result = CompetitorResult(
        score=50,
        peer_summary="기존 최소 필드만으로도 생성됩니다.",
        peers=[],
        evidence=[],
    )

    assert result.score == 50
    assert result.peer_summary == "기존 최소 필드만으로도 생성됩니다."
    assert result.peer_selection_summary is None
    assert result.metric_definitions == {}
    assert result.relative_position == {}
    assert result.data_quality_flags == []
    assert result.a1_peer_multiple_payload is None
    assert result.warnings == []
    assert result.evidence_cards == []
    assert result.bear_case is None


def test_competitor_result_accepts_evidence_cards_and_bear_case() -> None:
    result = CompetitorResult(
        score=70,
        peer_summary="LLM 요약",
        peers=[],
        evidence=["기본 근거"],
        evidence_cards=[
            {
                "finding": "PER 저평가 구간",
                "metric_basis": "PER 18.4x vs peer 중위 22.0x",
                "confidence": "high",
                "flag": "strength",
            }
        ],
        bear_case="ROE 개선 전제 필요",
    )
    assert result.evidence_cards[0]["confidence"] == "high"
    assert result.bear_case == "ROE 개선 전제 필요"
