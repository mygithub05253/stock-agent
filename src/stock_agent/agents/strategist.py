from stock_agent.schemas.analysis import AgentState, StrategistResult

# 워커별 종합 가중치. Macro 유무에 따라 두 세트를 유지(PR #49 기준값 보존).
# 부분 실패 시 가용 워커만 남겨 재정규화하므로, 전 워커가 있을 때 결과는 기존과 동일하다.
_WEIGHTS_WITH_MACRO = {"quant": 0.40, "qual": 0.25, "competitor": 0.20, "macro": 0.15}
_WEIGHTS_NO_MACRO = {"quant": 0.45, "qual": 0.30, "competitor": 0.25}

# 종합 신호를 내기 위해 최소 1개는 있어야 하는 핵심 워커.
_FUNDAMENTAL_WORKERS = ("quant", "qual", "competitor")


def _detect_price_event(query: str) -> str | None:
    if any(keyword in query for keyword in ("급등", "상승", "올랐")):
        return "surge"
    if any(keyword in query for keyword in ("급락", "하락", "떨어졌")):
        return "drop"
    return None


def _first(items: list[str], default: str) -> str:
    """리스트 첫 항목을 안전하게 꺼낸다(부분 실패로 비어 있어도 크래시 방지)."""
    return items[0] if items else default


def run_strategist(state: AgentState) -> AgentState:
    workers = {
        "quant": state.quant,
        "qual": state.qual,
        "competitor": state.competitor,
        "macro": state.macro,
    }
    available = {name: result for name, result in workers.items() if result is not None}

    # 핵심 워커가 하나도 없으면 종합 자체가 불가능 → 명시적 실패.
    if not any(name in available for name in _FUNDAMENTAL_WORKERS):
        raise ValueError("quant/qual/competitor 결과가 모두 없어 종합 판단을 생성할 수 없습니다.")

    # 가용 워커만으로 가중치를 재정규화한다(멀티에이전트 부분 실패 허용).
    base = _WEIGHTS_WITH_MACRO if "macro" in available else _WEIGHTS_NO_MACRO
    active_weights = {name: base[name] for name in base if name in available}
    total_weight = sum(active_weights.values())
    aggregate_score = round(
        sum(available[name].score * (weight / total_weight) for name, weight in active_weights.items())
    )

    missing = [name for name in _FUNDAMENTAL_WORKERS if name not in available]
    degraded = bool(missing)
    contributing_agents = [name for name in workers if name in available]

    # 누락 워커 수만큼 신뢰도를 보수적으로 차감(불완전 입력을 신뢰도에 반영).
    confidence = max(0, aggregate_score - 10 * len(missing))

    signal = "BUY" if aggregate_score >= 76 else "SELL" if aggregate_score <= 44 else "HOLD"

    holding_weight = 0.0
    if state.curator is not None:
        holding_weight = sum(
            holding.weight or 0
            for holding in state.portfolio.holdings
            if holding.stock_code == state.curator.stock_code
        )
    suitability = aggregate_score - round(holding_weight * 20)
    if state.user_profile.risk_tolerance == "low":
        suitability -= 8 if holding_weight >= 0.3 else 3
    elif state.user_profile.risk_tolerance == "high":
        suitability += 5

    if state.user_profile.liquidity_need_level == "high":
        suitability -= 5
    if state.user_profile.max_drawdown_tolerance is not None and state.user_profile.max_drawdown_tolerance > -0.08:
        suitability -= 4
    if state.user_profile.investment_horizon_months < 6:
        suitability -= 3

    suitability = max(30, min(90, suitability))
    raw_query = state.user_request.raw_query if state.user_request else state.user_query
    price_event = (
        state.user_request.urgency_reason
        if state.user_request and state.user_request.urgency_reason in {"surge", "drop"}
        else _detect_price_event(raw_query)
    )

    next_actions = [
        "보유 비중이 이미 높다면 추가 매수보다 실적 발표와 업황 지표 확인을 우선합니다.",
        "신규 진입은 단일 가격보다 분할 매수 기준가와 손실 허용 범위를 먼저 정합니다.",
    ]
    if state.user_profile.risk_tolerance == "low" and holding_weight >= 0.3:
        next_actions.insert(0, "안정형 성향 대비 보유 비중이 높아 비중 확대보다 리밸런싱 기준을 먼저 정합니다.")
    if price_event == "surge":
        next_actions.append("급등 이후에는 추격 매수보다 목표 비중과 이익 실현 기준을 먼저 확인합니다.")
    elif price_event == "drop":
        next_actions.append("급락 이후에는 손실 허용 범위와 추가 하락 시 대응 기준을 먼저 확인합니다.")

    # 근거·리스크는 가용 워커에서만 안전하게 수집한다(누락 워커 인덱싱 크래시 방지).
    key_reasons: list[str] = []
    if state.quant is not None:
        key_reasons.append(_first(state.quant.reasons, "정량 분석 근거 없음"))
    if state.qual is not None:
        key_reasons.append(_first(state.qual.evidence, "정성 분석 근거 없음"))
    if state.competitor is not None:
        key_reasons.append(state.competitor.peer_summary)
    if state.macro is not None:
        key_reasons.append(_first(state.macro.reasons, "거시경제 근거 없음"))

    risks: list[str] = []
    if state.quant is not None:
        risks.append(_first(state.quant.risks, "정량 리스크 정보 없음"))
    if state.qual is not None:
        risks.append(_first(state.qual.risks, "정성 리스크 정보 없음"))
    risks.append(
        "투자성향, 보유 비중, 현금 필요도가 맞지 않으면 종목 신호가 양호해도 포트폴리오 적합도는 낮아질 수 있습니다."
    )
    if degraded:
        risks.insert(
            0,
            "일부 분석 에이전트(" + ", ".join(missing) + ")가 결과를 내지 못해 가용 결과만으로 종합했습니다. "
            "신뢰도를 보수적으로 해석하세요.",
        )

    headline = "종목 분석 신호와 사용자 포트폴리오 적합도를 분리해 보면 보유 유지 검토가 우세합니다."
    if degraded:
        headline = "[부분 분석] " + headline

    state.strategist = StrategistResult(
        signal=signal,
        confidence=confidence,
        suitability=suitability,
        headline=headline,
        key_reasons=key_reasons,
        risks=risks,
        next_actions=next_actions,
        degraded=degraded,
        contributing_agents=contributing_agents,
    )
    return state
