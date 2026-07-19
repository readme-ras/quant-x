"""
QuantX Agent 9: QuantX-Auditor (Critic Agent)
Reviews the draft for unsupported claims, missing risks, factual errors.
Implements the Reflexion loop: sends structured feedback back to the writer.
"""

import logging
from schemas.state import ResearchState, AgentLog, AgentStatus, CritiqueItem
from tools.llm import call_llm_json
from tracing.setup import trace_agent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are QuantX-Auditor, a strict quality-control reviewer for equity research notes.
Your job is to find issues in a draft research note before it goes to a human analyst.

Check for:
1. UNSUPPORTED CLAIMS: Any factual claim without a source citation [SOURCE-ID]
2. MISSING SECTIONS: Executive Summary, Investment Thesis, Financial Analysis, Risk Factors, Options Signal, Recommendation
3. MISSING RISKS: Are there obvious risks the filing/news mentioned that aren't in the note?
4. CONTRADICTIONS: Does the recommendation match the risk factors and bull/bear cases?
5. VAGUENESS: Claims like "strong growth" without specific numbers
6. HALLUCINATIONS: Specific numbers that don't appear in any provided research data

Score 0-100 (100 = publication ready). Notes scoring 80+ pass.

Respond ONLY in valid JSON:
{
  "score": 75,
  "passed": false,
  "issues": [
    {
      "issue": "Specific unsupported claim description",
      "severity": "high",
      "suggestion": "Add citation [WEB-01] or remove this claim",
      "paragraph_ref": "Financial Analysis section"
    }
  ],
  "missing_sections": ["Options Signal"],
  "praise": "What the draft does well",
  "overall_verdict": "Brief verdict on the note quality"
}"""


def run_critic(state: ResearchState) -> dict:
    """Review the draft and decide pass or request revision."""
    with trace_agent("critic", {"ticker": state.ticker, "revision": state.revision_count}):
        log = AgentLog(
            agent_name="QuantX-Auditor",
            status=AgentStatus.RUNNING,
            message=f"Auditing draft (attempt {state.revision_count + 1}/{state.max_revisions})...",
        )

        # Build source reference for the critic to check against
        source_summary = "\n".join(
            f"[{s.id}] {s.title}: {s.snippet[:150]}"
            for s in state.sources[:20]
        )

        prompt = f"""Company: {state.company_name} ({state.ticker})

=== DRAFT RESEARCH NOTE ===
{state.draft[:4000]}

=== AVAILABLE SOURCE DATA (for verifying claims) ===
{source_summary[:1500]}

=== FINANCIAL DATA AVAILABLE ===
{(state.financial_data.summary if state.financial_data else 'None')[:400]}

Review the draft strictly. Flag any unsupported claims, missing sections, contradictions, or vague statements."""

        result = call_llm_json(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            temperature=0.1,
            fallback={
                "score": 60,
                "passed": False,
                "issues": [{"issue": "Review incomplete", "severity": "low", "suggestion": "Manual review needed", "paragraph_ref": None}],
                "missing_sections": [],
                "praise": "",
                "overall_verdict": "Requires manual review",
            },
        )

        score = result.get("score", 60)
        passed = result.get("passed", False) or score >= 80

        # Parse critique items
        raw_issues = result.get("issues", [])
        critique_items = []
        for issue in raw_issues:
            try:
                critique_items.append(
                    CritiqueItem(
                        issue=issue.get("issue", ""),
                        severity=issue.get("severity", "medium"),
                        suggestion=issue.get("suggestion", ""),
                        paragraph_ref=issue.get("paragraph_ref"),
                    )
                )
            except Exception:
                pass

        missing = result.get("missing_sections", [])
        if missing:
            for sec in missing:
                critique_items.append(
                    CritiqueItem(
                        issue=f"Missing section: {sec}",
                        severity="high",
                        suggestion=f"Add the {sec} section to the note",
                        paragraph_ref=None,
                    )
                )

        # Decide: pass to HITL or send back to writer
        if passed or state.revision_count >= state.max_revisions - 1:
            status_msg = "PASSED" if passed else f"MAX REVISIONS REACHED (score: {score})"
            log.status = AgentStatus.DONE
            log.message = f"Audit {status_msg} | Score: {score}/100 | Issues: {len(critique_items)}"
            log.output_preview = result.get("overall_verdict", "")[:200]

            logger.info(f"[Auditor] {log.message}")

            return {
                "critique": critique_items,
                "critique_passed": True,
                "current_agent": "hitl",
                "agent_logs": state.agent_logs + [log],
            }
        else:
            log.status = AgentStatus.DONE
            log.message = f"NEEDS REVISION | Score: {score}/100 | {len(critique_items)} issues"
            log.output_preview = "\n".join(c.issue for c in critique_items[:3])

            logger.info(f"[Auditor] {log.message} — sending back to writer")

            return {
                "critique": critique_items,
                "critique_passed": False,
                "revision_count": state.revision_count + 1,
                "current_agent": "writer",
                "agent_logs": state.agent_logs + [log],
            }
