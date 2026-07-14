"""
QuantX Agent 1: QuantX-Orchestrator
Plans the research sub-tasks and extracts the ticker from the user query.
"""

import logging
import re
from schemas.state import ResearchState, AgentLog, AgentStatus
from tools.llm import call_llm_json
from tools.financial import extract_ticker_from_query
from tracing.setup import trace_agent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are QuantX-Orchestrator, the planning agent for an AI equity research system.
Your job is to:
1. Extract the company ticker from the user's query
2. Identify the company name
3. Break the query into 4-6 specific research sub-tasks

You must respond ONLY in valid JSON with this exact structure:
{
  "ticker": "NVDA",
  "company_name": "NVIDIA Corporation",
  "sub_tasks": [
    "Analyze recent financial performance and key ratios",
    "Research recent news and market sentiment",
    "Pull SEC 10-K risk factors",
    "Search for analyst opinions and price targets",
    "Assess competitive positioning",
    "Review options market sentiment"
  ],
  "research_plan": "Brief 2-3 sentence summary of the research approach"
}"""


def run_orchestrator(state: ResearchState) -> dict:
    """Plan the research and extract ticker from the query."""
    with trace_agent("orchestrator", {"query": state.query}):
        log = AgentLog(agent_name="QuantX-Orchestrator", status=AgentStatus.RUNNING,
                       message="Planning research sub-tasks...")

        prompt = f"""User query: "{state.query}"

Extract the ticker, company name, and break this into specific research sub-tasks.
If no ticker is obvious from the query, make your best guess based on the company name mentioned."""

        result = call_llm_json(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            temperature=0.1,
            fallback={
                "ticker": extract_ticker_from_query(state.query) or "UNKNOWN",
                "company_name": state.query,
                "sub_tasks": [
                    "Research fundamentals and financial ratios",
                    "Gather recent news and sentiment",
                    "Review SEC filings for risks",
                    "Analyze options market signals",
                    "Build bull and bear investment cases",
                ],
                "research_plan": f"Conducting equity research on: {state.query}",
            },
        )

        ticker = result.get("ticker", "").upper().strip()
        company_name = result.get("company_name", ticker)
        sub_tasks = result.get("sub_tasks", [])
        research_plan = result.get("research_plan", "")

        # Fallback ticker extraction if LLM missed it
        if not ticker or ticker == "UNKNOWN":
            ticker = extract_ticker_from_query(state.query) or "UNKNOWN"

        log.status = AgentStatus.DONE
        log.message = f"Identified {company_name} ({ticker})"
        log.output_preview = f"Plan: {research_plan[:150]}"

        logger.info(f"[Orchestrator] Ticker: {ticker}, Tasks: {len(sub_tasks)}")

        return {
            "ticker": ticker,
            "company_name": company_name,
            "sub_tasks": sub_tasks,
            "research_plan": research_plan,
            "current_agent": "web_researcher",
            "agent_logs": state.agent_logs + [log],
        }