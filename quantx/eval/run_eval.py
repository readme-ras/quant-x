"""
QuantX - Evaluation Harness
Runs 20 sample queries and scores with RAGAS + LLM-as-judge.
Usage: python eval/run_eval.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import logging
from datetime import datetime
from tools.llm import call_llm_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── 20 Sample evaluation queries ──────────────────────────────────────────────
EVAL_QUERIES = [
    # Large cap tech
    {"query": "Should I invest in NVIDIA stock?", "ticker": "NVDA", "category": "large_cap_tech"},
    {"query": "Analyze Apple stock for long-term investment", "ticker": "AAPL", "category": "large_cap_tech"},
    {"query": "Microsoft stock outlook 2025", "ticker": "MSFT", "category": "large_cap_tech"},
    {"query": "Is Google a good buy right now?", "ticker": "GOOGL", "category": "large_cap_tech"},
    {"query": "Meta platforms investment thesis", "ticker": "META", "category": "large_cap_tech"},

    # EV / Auto
    {"query": "Tesla stock analysis", "ticker": "TSLA", "category": "ev_auto"},
    {"query": "Should I buy or sell Ford stock?", "ticker": "F", "category": "ev_auto"},

    # Finance
    {"query": "JPMorgan Chase investment analysis", "ticker": "JPM", "category": "finance"},
    {"query": "Is Berkshire Hathaway overvalued?", "ticker": "BRK-B", "category": "finance"},

    # Healthcare
    {"query": "Pfizer stock outlook after pandemic", "ticker": "PFE", "category": "healthcare"},
    {"query": "Johnson and Johnson long term investment", "ticker": "JNJ", "category": "healthcare"},

    # Consumer
    {"query": "Amazon AWS growth analysis", "ticker": "AMZN", "category": "consumer_tech"},
    {"query": "Netflix subscriber growth investment case", "ticker": "NFLX", "category": "consumer_tech"},
    {"query": "Walmart vs Amazon for defensive investors", "ticker": "WMT", "category": "consumer"},

    # Semiconductor
    {"query": "AMD vs Intel stock comparison", "ticker": "AMD", "category": "semiconductor"},
    {"query": "TSMC investment thesis for AI", "ticker": "TSM", "category": "semiconductor"},

    # Energy
    {"query": "ExxonMobil stock in energy transition", "ticker": "XOM", "category": "energy"},

    # Small/mid cap
    {"query": "Palantir stock analysis for retail investors", "ticker": "PLTR", "category": "mid_cap"},
    {"query": "CrowdStrike cybersecurity investment", "ticker": "CRWD", "category": "mid_cap"},
    {"query": "Snowflake data cloud growth analysis", "ticker": "SNOW", "category": "mid_cap"},
]

# ── LLM-as-judge rubric ───────────────────────────────────────────────────────
JUDGE_SYSTEM = """You are an expert evaluator of equity research notes.
Score the following research note on these dimensions (0-5 each):

1. FACTUALITY (0-5): Are claims supported by data? Are there obvious hallucinations?
2. COMPLETENESS (0-5): Does it cover: thesis, financials, risks, options, recommendation?
3. CITATION_DENSITY (0-5): Are claims properly cited with source IDs?
4. ACTIONABILITY (0-5): Is the recommendation clear and well-reasoned?
5. RISK_COVERAGE (0-5): Are material risks from filings/news covered?

Respond ONLY in valid JSON:
{
  "factuality": 4,
  "completeness": 3,
  "citation_density": 4,
  "actionability": 3,
  "risk_coverage": 4,
  "total": 18,
  "max_score": 25,
  "percentage": 72,
  "verdict": "Good note with solid factual grounding. Missing options analysis.",
  "top_issue": "Most significant issue with this note"
}"""


def judge_note(note: str, ticker: str) -> dict:
    """Score a research note using LLM-as-judge."""
    prompt = f"""Evaluate this equity research note for {ticker}:

{note[:3000]}

Score it on factuality, completeness, citation density, actionability, and risk coverage."""

    return call_llm_json(
        prompt=prompt,
        system=JUDGE_SYSTEM,
        temperature=0.1,
        fallback={
            "factuality": 0, "completeness": 0, "citation_density": 0,
            "actionability": 0, "risk_coverage": 0,
            "total": 0, "max_score": 25, "percentage": 0,
            "verdict": "Evaluation failed", "top_issue": "LLM judge error",
        },
    )


def run_eval(num_queries: int = 5, output_file: str = "eval/eval_report.json"):
    """
    Run evaluation on a subset of queries (default 5 for speed).
    Set num_queries=20 for full eval.
    """
    from graph.build_graph import run_pipeline

    logger.info(f"Starting QuantX eval — running {num_queries} queries")
    results = []
    queries_to_run = EVAL_QUERIES[:num_queries]

    for i, q in enumerate(queries_to_run):
        logger.info(f"\n[{i+1}/{num_queries}] Query: {q['query']}")
        start = time.time()

        try:
            state = run_pipeline(q["query"], thread_id=f"eval_{i}_{int(time.time())}")
            duration = time.time() - start

            if state.draft and len(state.draft) > 200:
                scores = judge_note(state.draft, q["ticker"])
            else:
                scores = {"percentage": 0, "verdict": "No draft generated", "top_issue": "Pipeline failed"}
                duration = time.time() - start

            result = {
                "query": q["query"],
                "ticker": q["ticker"],
                "category": q["category"],
                "duration_seconds": round(duration, 1),
                "agents_completed": sum(1 for l in state.agent_logs if l.status == AgentStatus.DONE),
                "sources_found": len(state.sources),
                "revision_count": state.revision_count,
                "critique_passed": state.critique_passed,
                "draft_length": len(state.draft),
                "scores": scores,
                "error": state.error,
            }

        except Exception as e:
            logger.error(f"Query {i+1} failed: {e}")
            result = {
                "query": q["query"],
                "ticker": q["ticker"],
                "category": q["category"],
                "duration_seconds": time.time() - start,
                "error": str(e),
                "scores": {"percentage": 0},
            }

        results.append(result)
        logger.info(f"  Score: {result['scores'].get('percentage', 0)}% | Time: {result['duration_seconds']}s")

    # Aggregate stats
    valid = [r for r in results if not r.get("error")]
    avg_score = sum(r["scores"].get("percentage", 0) for r in valid) / len(valid) if valid else 0
    avg_time = sum(r["duration_seconds"] for r in valid) / len(valid) if valid else 0
    avg_sources = sum(r.get("sources_found", 0) for r in valid) / len(valid) if valid else 0
    pass_rate = sum(1 for r in valid if r["scores"].get("percentage", 0) >= 60) / len(valid) * 100 if valid else 0

    report = {
        "eval_timestamp": datetime.now().isoformat(),
        "total_queries": num_queries,
        "successful": len(valid),
        "failed": len(results) - len(valid),
        "aggregate": {
            "avg_score_pct": round(avg_score, 1),
            "avg_time_seconds": round(avg_time, 1),
            "avg_sources_per_query": round(avg_sources, 1),
            "pass_rate_60pct": round(pass_rate, 1),
        },
        "results": results,
    }

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("QUANTX EVALUATION REPORT")
    print("="*60)
    print(f"Queries run:     {num_queries}")
    print(f"Successful:      {len(valid)}")
    print(f"Avg score:       {avg_score:.1f}%")
    print(f"Avg time:        {avg_time:.0f}s")
    print(f"Avg sources:     {avg_sources:.1f}")
    print(f"Pass rate (60%): {pass_rate:.1f}%")
    print(f"\nFull report:     {output_file}")
    print("="*60)

    return report


# Import needed for eval
from schemas.state import AgentStatus

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="QuantX Eval Harness")
    parser.add_argument("--n", type=int, default=5, help="Number of queries to run (default: 5, max: 20)")
    parser.add_argument("--output", type=str, default="eval/eval_report.json", help="Output file path")
    args = parser.parse_args()

    run_eval(num_queries=min(args.n, 20), output_file=args.output)
