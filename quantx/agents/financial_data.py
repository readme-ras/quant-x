"""
QuantX Agent 3: QuantX-Ledger (Financial Data + Derivatives)
Pulls fundamentals, ratios, and options sentiment via yfinance.
This agent is mostly deterministic Python — LLM only interprets the numbers.
"""

import logging
from schemas.state import ResearchState, AgentLog, AgentStatus
from tools.llm import call_llm_json
from tools.financial import get_fundamentals, get_options_sentiment
from tracing.setup import trace_agent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are QuantX-Ledger, a financial data interpretation agent.
You receive structured financial data and write a clear analyst-style interpretation.

Focus on:
- Is the valuation cheap or expensive vs historical norms?
- Are margins improving or deteriorating?
- Is the balance sheet healthy (debt levels, current ratio)?
- What does the options market signal about near-term sentiment?
- Any red flags or standout strengths?

Respond ONLY in valid JSON:
{
  "interpretation": "Multi-paragraph analyst interpretation of the numbers...",
  "valuation_verdict": "Cheap / Fair / Expensive / Cannot determine",
  "financial_health": "Strong / Adequate / Weak / Cannot determine",
  "options_signal": "Bullish / Bearish / Neutral / No data"
}"""


def run_financial_data(state: ResearchState) -> dict:
    """Pull and interpret financial fundamentals and options data."""
    with trace_agent("financial_data", {"ticker": state.ticker}):
        log = AgentLog(
            agent_name="QuantX-Ledger",
            status=AgentStatus.RUNNING,
            message=f"Pulling financials and options data for {state.ticker}...",
        )

        # --- Deterministic data pull (no LLM) ---
        fin_data = get_fundamentals(state.ticker)
        options_data = get_options_sentiment(state.ticker)

        if fin_data.error:
            log.status = AgentStatus.FAILED
            log.message = f"Financial data error: {fin_data.error}"
            return {
                "financial_data": fin_data,
                "options_data": options_data,
                "current_agent": "news",
                "agent_logs": state.agent_logs + [log],
            }

        # --- LLM interprets the numbers ---
        prompt = f"""Company: {state.company_name} ({state.ticker})

FUNDAMENTALS:
{fin_data.summary}

OPTIONS SENTIMENT:
{options_data.summary}

Write an analyst-style interpretation of these numbers.
Be specific — reference actual values, not vague generalities."""

        result = call_llm_json(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            temperature=0.1,
            fallback={
                "interpretation": fin_data.summary + "\n\n" + options_data.summary,
                "valuation_verdict": "Cannot determine",
                "financial_health": "Cannot determine",
                "options_signal": options_data.sentiment_signal.capitalize(),
            },
        )

        # Attach interpretation to summaries
        interpretation = result.get("interpretation", "")
        fin_data.summary = fin_data.summary + "\n\n**Interpretation:**\n" + interpretation

        log.status = AgentStatus.DONE
        log.message = (
            f"Valuation: {result.get('valuation_verdict')} | "
            f"Health: {result.get('financial_health')} | "
            f"Options: {result.get('options_signal')}"
        )
        log.output_preview = interpretation[:200]

        logger.info(f"[Ledger] {log.message}")

        return {
            "financial_data": fin_data,
            "options_data": options_data,
            "current_agent": "news",
            "agent_logs": state.agent_logs + [log],
        }
