"""
QuantX Agent 2: QuantX-Scout (Web Researcher)
Searches the web via Tavily and produces a cited summary.
Every claim in the output must reference a Source ID.
"""

import logging
from schemas.state import ResearchState, AgentLog, AgentStatus, Source
from tools.llm import call_llm_json
from tools.search import tavily_search
from tracing.setup import trace_agent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are QuantX-Scout, a financial web research agent.
You receive search results about a company and produce a concise cited summary.

CRITICAL RULES:
- Every factual claim MUST reference a source ID (e.g., [WEB-01], [WEB-02])
- Do not invent facts not present in the search results
- Be factual, not promotional
- Focus on: business model, competitive position, recent developments, analyst views

Respond ONLY in valid JSON:
{
  "summary": "Multi-paragraph summary where every claim cites [SOURCE-ID]...",
  "key_findings": ["Finding 1 [WEB-01]", "Finding 2 [WEB-02]", ...]
}"""


def run_web_researcher(state: ResearchState) -> dict:
    """Search the web and produce a cited research summary."""
    with trace_agent("web_researcher", {"ticker": state.ticker}):
        log = AgentLog(
            agent_name="QuantX-Scout",
            status=AgentStatus.RUNNING,
            message=f"Searching web for {state.company_name} ({state.ticker})...",
        )

        # Run 2 targeted searches
        queries = [
            f"{state.company_name} {state.ticker} stock analysis business model 2024 2025",
            f"{state.ticker} analyst price target earnings outlook competitive position",
        ]

        all_sources: list[Source] = []
        for query in queries:
            results = tavily_search(query, max_results=4)
            # Deduplicate by URL
            seen_urls = {s.url for s in all_sources}
            for r in results:
                if r.url not in seen_urls:
                    # Re-ID sources sequentially
                    r.id = f"WEB-{len(all_sources)+1:02d}"
                    all_sources.append(r)
                    seen_urls.add(r.url)

        if not all_sources:
            log.status = AgentStatus.FAILED
            log.message = "No web results found (check TAVILY_API_KEY)"
            return {
                "web_summary": f"Web research unavailable for {state.ticker}. Check TAVILY_API_KEY.",
                "sources": [],
                "current_agent": "financial_data",
                "agent_logs": state.agent_logs + [log],
            }

        # Format results for LLM
        results_text = "\n\n".join(
            f"[{s.id}] {s.title}\nURL: {s.url}\n{s.snippet}"
            for s in all_sources
        )

        prompt = f"""Company: {state.company_name} ({state.ticker})
Research sub-tasks: {', '.join(state.sub_tasks[:3])}

Search results:
{results_text}

Write a comprehensive cited research summary. Every claim must cite a source ID."""

        result = call_llm_json(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            temperature=0.1,
            fallback={"summary": results_text[:1000], "key_findings": []},
        )

        summary = result.get("summary", "")
        key_findings = result.get("key_findings", [])

        if key_findings:
            summary += "\n\n**Key Findings:**\n" + "\n".join(f"• {f}" for f in key_findings)

        log.status = AgentStatus.DONE
        log.message = f"Found {len(all_sources)} sources"
        log.output_preview = summary[:200]

        # Merge new sources with existing (avoid dupes)
        existing_urls = {s.url for s in state.sources}
        merged = list(state.sources) + [s for s in all_sources if s.url not in existing_urls]

        logger.info(f"[Scout] {len(all_sources)} sources, summary length: {len(summary)}")

        return {
            "web_summary": summary,
            "sources": merged,
            "current_agent": "financial_data",
            "agent_logs": state.agent_logs + [log],
        }
