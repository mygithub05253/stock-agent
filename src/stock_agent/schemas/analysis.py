from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Signal = Literal["BUY", "HOLD", "SELL"]
RiskTolerance = Literal["low", "medium", "high"]


class Holding(BaseModel):
    stock_code: str
    corp_name: str
    weight: float = Field(ge=0, le=1)
    avg_price: int | None = None


class UserProfile(BaseModel):
    user_id: str = "demo-user"
    risk_tolerance: RiskTolerance = "medium"
    investment_horizon_months: int = Field(default=12, ge=1)
    cash_source: str = "surplus_cash"
    preferred_sectors: list[str] = Field(default_factory=list)


class Portfolio(BaseModel):
    holdings: list[Holding] = Field(default_factory=list)
    cash_weight: float = Field(default=0.2, ge=0, le=1)


class CuratorResult(BaseModel):
    intent: str
    corp_name: str
    stock_code: str
    corp_code: str | None = None
    sector: str
    candidates: list[str] = Field(default_factory=list)


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
    user_profile: UserProfile
    portfolio: Portfolio
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
