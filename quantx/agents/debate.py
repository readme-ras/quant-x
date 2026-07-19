"""
QuantX Agents 6 & 7: QuantX-Bull and QuantX-Bear (Debate Agents)
Build the strongest possible bull/bear case from all research gathered so far.
Run independently so they don't influence each other.
"""

import logging
from schemas.state import ResearchState, AgentLog, AgentStatus
from tools.llm import call_llm_json
from tracing.setup import trace_agent

logger = logging.getLogger(__name__)

BULL_SYSTEM = """You are QuantX-Bull, an optimistic equity research analyst.
Your job is to build the STRONGEST possible bullish investment case for a stock.
Use the research data provided. Cite sources by their ID (e.g., [WEB-01], [NEWS-02], [FILING-01]).

Do NOT be balanced — you are the bull in a debate. Argue confidently for the upside.
Focus on: growth catalysts, competitive moats, undervaluation, positive trends.

Respond ONLY in valid JSON:
{
  "thesis": "One-sentence bull thesis",
  "arguments": [
    {"point": "Growth catalyst", "evidence": "Specific evidence [SOURCE-ID]", "strength": "high/medium"},
    ...
  ],
  "price_upside": "Estimated upside % or price target if data supports it",
  "bull_case_summary": "3-4 paragraph bull case with citations..."
}"""

BEAR_SYSTEM = """You are QuantX-Bear, a skeptical equity research analyst.
Your job is to build the STRONGEST possible bearish investment case for a stock.
Use the research data provided. Cite sources by their ID (e.g., [WEB-01], [NEWS-02], [FILING-01]).

Do NOT be balanced — you are the bear in a debate. Argue confidently for the downside.
Focus on: risks, overvaluation, competitive threats, negative trends, management issues.

Respond ONLY in valid JSON:
{
  "thesis": "One-sentence bear thesis",
  "arguments": [
    {"point": "Key risk", "evidence": "Specific evidence [SOURCE-ID]", "strength": "high/medium"},
    ...
  ],
  "price_downside": "Estimated downside % if data supports it",
  "bear_case_summary": "3-4 paragraph bear case with citations..."
}"""


def _build_context(state: ResearchState) -> str:
    """Build research context for debate agents."""
    parts = [f"Company: {state.company_name} ({state.ticker})\n"]

    if state.financial_data and state.financial_data.summary:
        parts.append(f"FINANCIAL DATA:\n{state.financial_data.summary[:800]}")

    if state.options_data and state.options_data.summary:
        parts.append(f"OPTIONS SENTIMENT:\n{state.options_data.summary[:400]}")

    if state.news_summary:
        parts.append(f"NEWS SUMMARY:\n{state.news_summary[:600]}")

    if state.filing_risks:
        parts.append(f"SEC FILING RISKS:\n{state.filing_risks[:600]}")

    if state.web_summary:
        parts.append(f"WEB RESEARCH:\n{state.web_summary[:600]}")

    # Source list for citation reference
    if state.sources:
        source_list = "\n".join(f"[{s.id}] {s.title}" for s in state.sources[:15])
        parts.append(f"AVAILABLE SOURCES:\n{source_list}")

    return "\n\n".join(parts)


def run_bull_agent(state: ResearchState) -> dict:
    """Build the bullish investment case."""
    with trace_agent("bull_agent", {"ticker": state.ticker}):
        log = AgentLog(
            agent_name="QuantX-Bull",
            status=AgentStatus.RUNNING,
            message=f"Building bull case for {state.ticker}...",
        )

        context = _build_context(state)

        result = call_llm_json(
            prompt=f"{context}\n\nBuild the strongest possible bullish case. Cite your sources.",
            system=BULL_SYSTEM,
            temperature=0.2,
            fallback={
                "thesis": f"Bullish on {state.ticker} based on fundamentals",
                "arguments": [],
                "price_upside": "Unknown",
                "bull_case_summary": "Bull case analysis in progress.",
            },
        )

        thesis = result.get("thesis", "")
        arguments = result.get("arguments", [])
        bull_summary = result.get("bull_case_summary", "")
        upside = result.get("price_upside", "")

        # Format output
        bull_case = f"🟢 **BULL CASE: {state.ticker}**\n\n"
        bull_case += f"**Thesis:** {thesis}\n\n"
        if upside:
            bull_case += f"**Estimated Upside:** {upside}\n\n"
        bull_case += f"**Arguments:**\n"
        for i, arg in enumerate(arguments, 1):
            strength_icon = "💪" if arg.get("strength") == "high" else "👍"
            bull_case += f"{i}. {strength_icon} **{arg.get('point', '')}**\n   {arg.get('evidence', '')}\n\n"
        bull_case += f"**Full Bull Case:**\n{bull_summary}"

        log.status = AgentStatus.DONE
        log.message = f"Bull thesis: {thesis[:80]}"
        log.output_preview = bull_case[:200]

        logger.info(f"[Bull] {log.message}")

        return {
            "bull_case": bull_case,
            "current_agent": "bear",
            "agent_logs": state.agent_logs + [log],
        }


def run_bear_agent(state: ResearchState) -> dict:
    """Build the bearish investment case."""
    with trace_agent("bear_agent", {"ticker": state.ticker}):
        log = AgentLog(
            agent_name="QuantX-Bear",
            status=AgentStatus.RUNNING,
            message=f"Building bear case for {state.ticker}...",
        )

        context = _build_context(state)

        result = call_llm_json(
            prompt=f"{context}\n\nBuild the strongest possible bearish case. Cite your sources.",
            system=BEAR_SYSTEM,
            temperature=0.2,
            fallback={
                "thesis": f"Cautious on {state.ticker} given current risks",
                "arguments": [],
                "price_downside": "Unknown",
                "bear_case_summary": "Bear case analysis in progress.",
            },
        )

        thesis = result.get("thesis", "")
        arguments = result.get("arguments", [])
        bear_summary = result.get("bear_case_summary", "")
        downside = result.get("price_downside", "")

        # Format output
        bear_case = f"🔴 **BEAR CASE: {state.ticker}**\n\n"
        bear_case += f"**Thesis:** {thesis}\n\n"
        if downside:
            bear_case += f"**Estimated Downside:** {downside}\n\n"
        bear_case += f"**Arguments:**\n"
        for i, arg in enumerate(arguments, 1):
            strength_icon = "⚠️" if arg.get("strength") == "high" else "⚡"
            bear_case += f"{i}. {strength_icon} **{arg.get('point', '')}**\n   {arg.get('evidence', '')}\n\n"
        bear_case += f"**Full Bear Case:**\n{bear_summary}"

        log.status = AgentStatus.DONE
        log.message = f"Bear thesis: {thesis[:80]}"
        log.output_preview = bear_case[:200]

        logger.info(f"[Bear] {log.message}")

        return {
            "bear_case": bear_case,
            "current_agent": "writer",
            "agent_logs": state.agent_logs + [log],
        }
