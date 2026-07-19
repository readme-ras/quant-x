"""
QuantX Agent 8: QuantX-Scribe (Writer Agent)
Synthesizes all research into a professional 4-6 page equity research note.
Uses a strict template so Phi-4-mini fills sections rather than free-writing structure.
"""

import logging
from schemas.state import ResearchState, AgentLog, AgentStatus, Citation
from tools.llm import call_llm_json
from tracing.setup import trace_agent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are QuantX-Scribe, a senior equity research writer at a top-tier investment bank.
You synthesize research from multiple agents into a professional equity research note.

CRITICAL RULES:
- Every factual claim MUST have a citation in format [SOURCE-ID]
- The note must have ALL sections: Executive Summary, Investment Thesis, Financial Analysis, Risk Factors, Options Market Signal, Recommendation
- Be specific with numbers — use actual data from the research
- Do NOT make up data that was not provided
- Use analyst-level language (not retail-friendly fluff)

Respond ONLY in valid JSON:
{
  "executive_summary": "2-3 sentence overview with key stats [CITE]...",
  "investment_thesis": "The core reason to own or avoid this stock [CITE]...",
  "financial_analysis": "Detailed analysis of fundamentals and valuation [CITE]...",
  "bull_bear_synthesis": "What the bull and bear cases agree/disagree on [CITE]...",
  "risk_factors": "Top risks that could invalidate the thesis [CITE]...",
  "options_signal": "What derivatives positioning tells us [CITE]...",
  "comparable_companies": "Brief peer comparison if data available...",
  "recommendation": "BUY / HOLD / SELL with price target if determinable",
  "conviction": "High / Medium / Low",
  "citations": [
    {"claim": "exact claim text", "source_id": "WEB-01", "confidence": 0.9}
  ],
  "full_note": "Complete formatted research note combining all sections..."
}"""


def run_writer(state: ResearchState) -> dict:
    """Synthesize all research into the equity research note."""
    with trace_agent("writer", {"ticker": state.ticker, "revision": state.revision_count}):
        log = AgentLog(
            agent_name="QuantX-Scribe",
            status=AgentStatus.RUNNING,
            message=f"Writing research note (revision {state.revision_count + 1})...",
        )

        # Include critique feedback if this is a revision
        critique_context = ""
        if state.critique and state.revision_count > 0:
            issues = "\n".join(
                f"- [{c.severity.upper()}] {c.issue}: {c.suggestion}"
                for c in state.critique
            )
            critique_context = f"\n\nCRITIQUE FEEDBACK TO ADDRESS IN THIS REVISION:\n{issues}"

        prompt = f"""Company: {state.company_name} ({state.ticker})
Research Query: {state.query}

=== FINANCIAL DATA ===
{(state.financial_data.summary if state.financial_data else 'Not available')[:700]}

=== OPTIONS/DERIVATIVES ===
{(state.options_data.summary if state.options_data else 'Not available')[:400]}

=== NEWS SENTIMENT ===
{state.news_summary[:600]}

=== SEC FILING RISKS ===
{state.filing_risks[:600]}

=== WEB RESEARCH ===
{state.web_summary[:600]}

=== BULL CASE ===
{state.bull_case[:500]}

=== BEAR CASE ===
{state.bear_case[:500]}

=== AVAILABLE SOURCES ===
{chr(10).join(f'[{s.id}] {s.title}' for s in state.sources[:20])}
{critique_context}

Write a comprehensive, cited equity research note using ALL the sections specified.
Every claim must cite a source ID. Be specific with numbers."""

        result = call_llm_json(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            temperature=0.15,
            fallback={
                "executive_summary": f"Research note for {state.company_name} ({state.ticker}).",
                "investment_thesis": "Analysis pending.",
                "financial_analysis": state.financial_data.summary if state.financial_data else "",
                "bull_bear_synthesis": f"Bull: {state.bull_case[:200]}\nBear: {state.bear_case[:200]}",
                "risk_factors": state.filing_risks[:400],
                "options_signal": state.options_data.summary if state.options_data else "",
                "comparable_companies": "",
                "recommendation": "HOLD",
                "conviction": "Low",
                "citations": [],
                "full_note": "",
            },
        )

        # Build the full formatted note
        rec = result.get("recommendation", "HOLD")
        if isinstance(rec, dict):
            rec = rec.get("rating", rec.get("value", "HOLD"))
        rec = str(rec).upper().strip()
        if rec not in ("BUY", "SELL", "HOLD"):
            rec = "HOLD"
        conviction = result.get("conviction", "Medium")
        rec_icon = {"BUY": "🟢", "HOLD": "🟡", "SELL": "🔴"}.get(rec.upper(), "🟡")

        full_note = result.get("full_note", "")
        if not full_note or len(full_note) < 200:
            # Build it from sections
            full_note = f"""# {state.company_name} ({state.ticker}) — Equity Research Note
**QuantX Research | AlphaDesk**
{rec_icon} **Recommendation: {rec}** | Conviction: {conviction}

---

## Executive Summary
{result.get('executive_summary', '')}

---

## Investment Thesis
{result.get('investment_thesis', '')}

---

## Financial Analysis
{result.get('financial_analysis', '')}

---

## Bull vs. Bear Synthesis
{result.get('bull_bear_synthesis', '')}

---

## Risk Factors
{result.get('risk_factors', '')}

---

## Options & Derivatives Signal
{result.get('options_signal', '')}

---

## Comparable Companies
{result.get('comparable_companies', 'Peer comparison not available.')}

---

## Recommendation
{rec_icon} **{rec}** (Conviction: {conviction})

*This note was generated by QuantX AlphaAgents and is subject to human analyst review.*
"""

        # Parse citations
        raw_citations = result.get("citations", [])
        citations = []
        for c in raw_citations:
            try:
                citations.append(
                    Citation(
                        claim=c.get("claim", ""),
                        source_id=c.get("source_id", "UNKNOWN"),
                        confidence=float(c.get("confidence", 0.7)),
                    )
                )
            except Exception:
                pass

        log.status = AgentStatus.DONE
        log.message = f"Draft written | Recommendation: {rec} | Citations: {len(citations)}"
        log.output_preview = full_note[:250]

        logger.info(f"[Scribe] {log.message}")

        return {
            "draft": full_note,
            "citations": citations,
            "current_agent": "critic",
            "agent_logs": state.agent_logs + [log],
        }
