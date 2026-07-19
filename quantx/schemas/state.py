"""
QuantX - Shared State Schema
The single Pydantic model that flows through every agent node.
Every agent reads from this and writes a partial update back.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class Source(BaseModel):
    id: str
    url: str
    title: str
    snippet: str
    source_type: str  # "web", "news", "filing", "financial"


class NewsItem(BaseModel):
    headline: str
    url: str
    published_at: str
    sentiment: str  # "positive", "negative", "neutral"
    sentiment_reason: str
    source: str


class Citation(BaseModel):
    claim: str
    source_id: str
    confidence: float = Field(ge=0.0, le=1.0)


class CritiqueItem(BaseModel):
    issue: str
    severity: str  # "high", "medium", "low"
    suggestion: str
    paragraph_ref: Optional[str] = None


class OptionsData(BaseModel):
    ticker: str
    put_call_ratio: Optional[float] = None
    iv_skew: Optional[float] = None
    implied_volatility: Optional[float] = None
    open_interest: Optional[int] = None
    sentiment_signal: str = "neutral"  # "bullish", "bearish", "neutral"
    summary: str = ""


class FinancialData(BaseModel):
    ticker: str
    company_name: str = ""
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    price_to_book: Optional[float] = None
    debt_to_equity: Optional[float] = None
    revenue_growth: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    current_ratio: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    analyst_target: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    summary: str = ""
    error: Optional[str] = None


class AgentLog(BaseModel):
    agent_name: str
    status: AgentStatus = AgentStatus.PENDING
    message: str = ""
    output_preview: str = ""
    duration_seconds: float = 0.0


class ResearchState(BaseModel):
    # Input
    query: str = ""
    ticker: str = ""
    company_name: str = ""

    # Orchestrator plan
    sub_tasks: list[str] = []
    research_plan: str = ""

    # Research agent outputs
    sources: list[Source] = []
    web_summary: str = ""
    financial_data: Optional[FinancialData] = None
    options_data: Optional[OptionsData] = None
    news_items: list[NewsItem] = []
    news_summary: str = ""
    filing_excerpts: list[str] = []
    filing_risks: str = ""

    # Debate outputs
    bull_case: str = ""
    bear_case: str = ""

    # Writer outputs
    draft: str = ""
    citations: list[Citation] = []

    # Critic outputs
    critique: list[CritiqueItem] = []
    critique_passed: bool = False
    revision_count: int = 0
    max_revisions: int = 3

    # HITL
    human_approved: bool = False
    human_edits: str = ""
    final_note: str = ""

    # Agent tracking (for UI)
    agent_logs: list[AgentLog] = []
    current_agent: str = ""
    error: Optional[str] = None
    is_complete: bool = False
