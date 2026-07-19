"""
QuantX Agent 5: QuantX-Filing (SEC Filings Agent)
Pulls 10-K/10-Q from SEC EDGAR and extracts risk factors + MD&A.
"""

import logging
from schemas.state import ResearchState, AgentLog, AgentStatus, Source
from tools.llm import call_llm_json
from tools.search import get_latest_filing_text
from tracing.setup import trace_agent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are QuantX-Filing, a regulatory filings analyst.
You read SEC filing excerpts and extract the most material risks and business insights.

Focus on:
- Top 5 material risk factors (be specific, not generic)
- Key management discussion points
- Any forward-looking statements about growth or headwinds
- Regulatory, competitive, or operational risks

Respond ONLY in valid JSON:
{
  "top_risks": [
    {"risk": "Risk title", "detail": "Specific explanation from the filing", "severity": "high/medium/low"},
    ...
  ],
  "mda_insights": "Key points from Management Discussion and Analysis...",
  "filing_summary": "2-3 paragraph summary of the most important filing disclosures",
  "risk_categories": ["regulatory", "competitive", "operational", "financial", "macro"]
}"""


def run_filings_agent(state: ResearchState) -> dict:
    """Pull and analyze SEC filings for risk factors."""
    with trace_agent("filings_agent", {"ticker": state.ticker}):
        log = AgentLog(
            agent_name="QuantX-Filing",
            status=AgentStatus.RUNNING,
            message=f"Pulling SEC 10-K filing for {state.ticker}...",
        )

        # Try 10-K first, fall back to 10-Q
        filing_text = get_latest_filing_text(state.ticker, "10-K")
        form_used = "10-K"

        if "Could not" in filing_text or "No recent" in filing_text:
            filing_text = get_latest_filing_text(state.ticker, "10-Q")
            form_used = "10-Q"

        if not filing_text or len(filing_text) < 100:
            log.status = AgentStatus.SKIPPED
            log.message = "No filing data available from EDGAR"
            return {
                "filing_excerpts": [],
                "filing_risks": f"SEC filing data could not be retrieved for {state.ticker}.",
                "current_agent": "bull",
                "agent_logs": state.agent_logs + [log],
            }

        # Truncate to fit context window comfortably for Phi-4-mini
        filing_excerpt = filing_text[:3500]

        prompt = f"""Company: {state.company_name} ({state.ticker})
Filing type: {form_used}

Filing excerpt:
{filing_excerpt}

Extract the top material risks and key management discussion points."""

        result = call_llm_json(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            temperature=0.1,
            fallback={
                "top_risks": [{"risk": "See filing", "detail": filing_excerpt[:200], "severity": "medium"}],
                "mda_insights": "",
                "filing_summary": filing_excerpt[:500],
                "risk_categories": ["operational"],
            },
        )

        top_risks = result.get("top_risks", [])
        filing_summary = result.get("filing_summary", "")
        mda_insights = result.get("mda_insights", "")

        # Format risk output
        risks_formatted = f"**{state.ticker} {form_used} — Material Risks**\n\n"
        for i, r in enumerate(top_risks, 1):
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(r.get("severity", "medium"), "🟡")
            risks_formatted += f"{i}. {severity_emoji} **{r.get('risk', '')}**\n   {r.get('detail', '')}\n\n"

        if mda_insights:
            risks_formatted += f"**Management Discussion:**\n{mda_insights}\n\n"
        risks_formatted += f"**Summary:**\n{filing_summary}"

        # Add filing as source
        filing_source = Source(
            id=f"FILING-01",
            url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={state.ticker}&type={form_used}",
            title=f"{state.ticker} {form_used} — SEC EDGAR",
            snippet=filing_excerpt[:300],
            source_type="filing",
        )
        existing_urls = {s.url for s in state.sources}
        merged_sources = list(state.sources)
        if filing_source.url not in existing_urls:
            merged_sources.append(filing_source)

        log.status = AgentStatus.DONE
        log.message = f"Extracted {len(top_risks)} risk factors from {form_used}"
        log.output_preview = risks_formatted[:200]

        logger.info(f"[Filing] {log.message}")

        return {
            "filing_excerpts": [filing_excerpt],
            "filing_risks": risks_formatted,
            "sources": merged_sources,
            "current_agent": "bull",
            "agent_logs": state.agent_logs + [log],
        }
