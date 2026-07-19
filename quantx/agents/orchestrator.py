"""
QuantX Agent 1: QuantX-Orchestrator
"""

import re
import logging
from schemas.state import ResearchState, AgentLog, AgentStatus
from tools.llm import call_llm_json
from tracing.setup import trace_agent

logger = logging.getLogger(__name__)

# Known company name → ticker mapping (fallback)
COMPANY_TO_TICKER = {
    "nvidia": "NVDA", "apple": "AAPL", "microsoft": "MSFT",
    "google": "GOOGL", "alphabet": "GOOGL", "meta": "META",
    "facebook": "META", "amazon": "AMZN", "tesla": "TSLA",
    "netflix": "NFLX", "amd": "AMD", "intel": "INTC",
    "tsmc": "TSM", "palantir": "PLTR", "snowflake": "SNOW",
    "crowdstrike": "CRWD", "jpmorgan": "JPM", "walmart": "WMT",
    "pfizer": "PFE", "exxon": "XOM", "ford": "F",
}

STOPWORDS = {
    "IS", "THE", "FOR", "BUY", "SELL", "HOLD", "STOCK", "AI",
    "AND", "OR", "IN", "A", "AN", "SHOULD", "INVEST", "ANALYZE",
    "ANALYSIS", "ME", "TELL", "ABOUT", "WHAT", "HOW", "WHY",
    "IT", "DO", "TO", "OF", "ON", "AT", "BY",
}


def extract_ticker(query: str) -> tuple[str, str]:
    """
    Extract ticker and guess company name from query.
    Returns (ticker, company_name).
    Priority: $TICKER > known company names > ALL_CAPS word
    """
    # 1. Explicit $TICKER pattern
    dollar = re.findall(r'\$([A-Z]{1,5})', query.upper())
    if dollar:
        return dollar[0], dollar[0]

    # 2. Known company name in query
    q_lower = query.lower()
    for company, ticker in COMPANY_TO_TICKER.items():
        if company in q_lower:
            return ticker, company.title()

    # 3. ALL CAPS word (2-5 letters) not in stopwords
    words = re.findall(r'\b([A-Z]{2,5})\b', query.upper())
    candidates = [w for w in words if w not in STOPWORDS]
    if candidates:
        return candidates[0], candidates[0]

    # 4. Capitalize first meaningful word as last resort
    clean = re.sub(r'[^a-zA-Z\s]', '', query)
    words = [w for w in clean.split() if len(w) > 3 and w.lower() not in
             {"should", "invest", "analyze", "stock", "about", "tell"}]
    if words:
        # Try to match against known companies
        for word in words:
            if word.lower() in COMPANY_TO_TICKER:
                return COMPANY_TO_TICKER[word.lower()], word.title()
        # Use first word as ticker guess
        return words[0].upper()[:5], words[0].title()

    return "NVDA", "NVIDIA Corporation"


def run_orchestrator(state: ResearchState) -> dict:
    log = AgentLog(
        agent_name="QuantX-Orchestrator",
        status=AgentStatus.RUNNING,
        message="Extracting ticker and planning research...",
    )

    # Extract ticker using pure Python (no LLM dependency)
    ticker, company_guess = extract_ticker(state.query)

    # Use LLM only to get the full company name (lightweight call)
    try:
        result = call_llm_json(
            prompt=f'What is the full official company name for stock ticker "{ticker}"? Example response: {{"company_name": "NVIDIA Corporation"}}',
            system='Return ONLY valid JSON. One field: company_name. Be concise.',
            temperature=0.1,
            fallback={"company_name": company_guess},
        )
        company_name = result.get("company_name", company_guess) or company_guess
    except Exception:
        company_name = company_guess

    # Ensure we never have empty ticker
    if not ticker:
        ticker = "NVDA"
        company_name = "NVIDIA Corporation"

    sub_tasks = [
        f"Research {company_name} business model and competitive position",
        "Analyze recent financial performance and key ratios",
        "Review recent news and market sentiment",
        "Pull SEC filing risk factors",
        "Assess options market sentiment and derivatives positioning",
        "Build bull and bear investment cases",
    ]

    log.status = AgentStatus.DONE
    log.message = f"Identified {company_name} ({ticker})"
    log.output_preview = f"Running {len(sub_tasks)} research tasks"

    logger.info(f"[Orchestrator] Ticker={ticker} | Company={company_name}")

    return {
        "ticker": ticker,
        "company_name": company_name,
        "sub_tasks": sub_tasks,
        "research_plan": f"Comprehensive equity research on {company_name} ({ticker})",
        "current_agent": "web_researcher",
        "agent_logs": state.agent_logs + [log],
    }