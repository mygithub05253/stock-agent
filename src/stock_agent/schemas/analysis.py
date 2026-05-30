from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


Signal = Literal["BUY", "HOLD", "SELL"]
RiskTolerance = Literal["low", "medium", "high"]
InvestmentGoal = Literal["wealth_preservation", "growth", "short_term_profit", "dividend"]
ExperienceLevel = Literal["beginner", "intermediate", "advanced"]
LiquidityNeedLevel = Literal["low", "medium", "high"]
RequestIntent = Literal[
    "holding_review",
    "new_recommendation",
    "risk_review",
    "sell_decision",
    "portfolio_review",
]
AnalysisScope = Literal["single_stock", "portfolio", "sector"]
UrgencyReason = Literal["surge", "drop", "earnings", "news", "general"]
RequestedDepth = Literal["summary", "standard", "deep"]


class Holding(BaseModel):
    stock_code: str
    corp_name: str
    sector: str | None = None
    weight: float | None = Field(default=None, ge=0, le=1)
    avg_price: int | None = Field(default=None, ge=0)
    qty: int | None = Field(default=None, ge=0)
    bought_at: date | None = None
    current_price: int | None = Field(default=None, ge=0)

    @property
    def cost_basis(self) -> int | None:
        if self.avg_price is None or self.qty is None:
            return None
        return self.avg_price * self.qty

    @property
    def market_value(self) -> int | None:
        if self.current_price is None or self.qty is None:
            return None
        return self.current_price * self.qty


class UserProfile(BaseModel):
    user_id: str = "demo-user"
    risk_tolerance: RiskTolerance = "medium"
    investment_horizon_months: int = Field(default=12, ge=1)
    target_return_rate: float | None = Field(default=None, ge=0, le=1)
    max_drawdown_tolerance: float | None = Field(default=None, ge=-1, le=0)
    investment_goal: InvestmentGoal = "growth"
    experience_level: ExperienceLevel = "beginner"
    cash_source: str = "surplus_cash"
    preferred_sectors: list[str] = Field(default_factory=list)
    excluded_sectors: list[str] = Field(default_factory=list)
    liquidity_need_level: LiquidityNeedLevel = "medium"


class Portfolio(BaseModel):
    holdings: list[Holding] = Field(default_factory=list)
    cash_weight: float = Field(default=0.2, ge=0, le=1)
    as_of_date: date | None = None

    @property
    def total_market_value(self) -> int | None:
        values = [holding.market_value for holding in self.holdings]
        if any(value is None for value in values):
            return None
        return sum(value for value in values if value is not None)

    def sector_weights(self) -> dict[str, float]:
        valued_holdings = [
            holding for holding in self.holdings if holding.sector and holding.market_value is not None
        ]
        total_value = sum(holding.market_value or 0 for holding in valued_holdings)
        if total_value <= 0:
            return {}

        weights: dict[str, float] = {}
        for holding in valued_holdings:
            sector = holding.sector or "기타"
            weights[sector] = weights.get(sector, 0.0) + (holding.market_value or 0) / total_value
        return weights


class UserRequest(BaseModel):
    raw_query: str
    intent: RequestIntent | None = None
    target_stock_code: str | None = None
    target_corp_name: str | None = None
    target_sector: str | None = None
    analysis_scope: AnalysisScope | None = None
    urgency_reason: UrgencyReason | None = None
    requested_depth: RequestedDepth = "summary"


class CuratorResult(BaseModel):
    intent: str
    corp_name: str
    stock_code: str
    corp_code: str | None = None
    sector: str
    candidates: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class QuantResult(BaseModel):
    score: int = Field(ge=0, le=100)
    valuation_signal: Signal
    metrics: dict[str, float | int | str]
    reasons: list[str]
    risks: list[str]


class QualResult(BaseModel):
    score: int = Field(ge=0, le=100)
    sentiment: Literal["positive", "neutral", "negative"]
    event_types: list[str]
    evidence: list[str]
    risks: list[str]


class CompetitorResult(BaseModel):
    score: int = Field(ge=0, le=100)
    peer_summary: str
    peers: list[dict[str, float | int | str | None]]
    evidence: list[str]
    peer_selection_summary: str | None = None
    metric_definitions: dict[str, str] = Field(default_factory=dict)
    relative_position: dict[str, float | int | str | None] = Field(default_factory=dict)
    data_quality_flags: list[str] = Field(default_factory=list)
    a1_peer_multiple_payload: dict[str, float | int | str | None] | None = None
    warnings: list[str] = Field(default_factory=list)


class StrategistResult(BaseModel):
    signal: Signal
    confidence: int = Field(ge=0, le=100)
    suitability: int = Field(ge=0, le=100)
    headline: str
    key_reasons: list[str]
    risks: list[str]
    next_actions: list[str]


class GuardrailResult(BaseModel):
    passed: bool
    warnings: list[str] = Field(default_factory=list)
    revised_headline: str
    disclaimer: str


class Tier1Result(BaseModel):
    signal: Signal
    confidence: int
    suitability: int
    headline: str
    disclaimer: str


class AgentState(BaseModel):
    user_query: str
    user_request: UserRequest | None = None
    user_profile: UserProfile
    portfolio: Portfolio
    as_of_date: str | None = None  # 백테스트 기준일
    curator: CuratorResult | None = None
    quant: QuantResult | None = None
    qual: QualResult | None = None
    competitor: CompetitorResult | None = None
    strategist: StrategistResult | None = None
    guardrail: GuardrailResult | None = None


class AnalysisOutput(BaseModel):
    tier1: Tier1Result
    tier2: dict[str, list[str] | str]
    tier3: dict[str, str]
    state: AgentState
