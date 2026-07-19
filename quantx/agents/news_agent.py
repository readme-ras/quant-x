"""
QuantX Agent 4: QuantX-Pulse (News Agent)
Pulls last-7-days news, classifies sentiment, identifies catalysts.
"""

import logging
from schemas.state import ResearchState, AgentLog, AgentStatus, NewsItem, Source
from tools.llm import call_llm_json
from tools.search import tavily_news_search
from tracing.setup import trace_agent

logger = logging.getLogger(__name__)

SENTIMENT_SYSTEM = """You are QuantX-Pulse, a financial news sentiment analyst.
You classify news headlines and snippets for an equity research system.

For each news item, determine:
- sentiment: exactly one of "positive", "negative", "neutral"
- sentiment_reason: one sentence explaining why (be specific to the content)
- is_catalyst: true if this could move the stock (earnings, guidance, M&A, regulation, etc.)
- catalyst_type: "earnings", "guidance", "ma", "regulatory", "product", "macro", "analyst", "other", or null

Respond ONLY in valid JSON:
{
  "items": [
    {
      "index": 0,
      "sentiment": "positive",
      "sentiment_reason": "Revenue beat consensus by 8%, guiding above street estimates",
      "is_catalyst": true,
      "catalyst_type": "earnings"
    }
  ],
  "overall_sentiment": "positive/negative/neutral/mixed",
  "key_catalysts": ["Upcoming earnings on [date]", "Regulatory review in EU"],
  "news_summary": "2-3 paragraph summary of the news landscape with key themes"
}"""


def run_news_agent(state: ResearchState) -> dict:
    """Fetch recent news and classify sentiment + catalysts."""
    with trace_agent("news_agent", {"ticker": state.ticker}):
        log = AgentLog(
            agent_name="QuantX-Pulse",
            status=AgentStatus.RUNNING,
            message=f"Scanning last 7 days of news for {state.ticker}...",
        )

        raw_results = tavily_news_search(state.ticker, state.company_name, days=7)

        if not raw_results:
            log.status = AgentStatus.SKIPPED
            log.message = "No news results (check TAVILY_API_KEY)"
            return {
                "news_items": [],
                "news_summary": f"No recent news found for {state.ticker}.",
                "current_agent": "filings",
                "agent_logs": state.agent_logs + [log],
            }

        # Format for LLM
        items_text = "\n\n".join(
            f"[{i}] {r.get('title', '')}\n{r.get('content', '')[:300]}"
            for i, r in enumerate(raw_results[:8])
        )

        prompt = f"""Company: {state.company_name} ({state.ticker})

Recent news items (last 7 days):
{items_text}

Classify the sentiment and identify catalysts for each item.
Then write an overall news summary."""

        result = call_llm_json(
            prompt=prompt,
            system=SENTIMENT_SYSTEM,
            temperature=0.1,
            fallback={
                "items": [],
                "overall_sentiment": "neutral",
                "key_catalysts": [],
                "news_summary": f"News data processed for {state.ticker}.",
            },
        )

        # Build NewsItem objects
        news_items = []
        classified = {item["index"]: item for item in result.get("items", []) if "index" in item}
        new_sources = []

        for i, raw in enumerate(raw_results[:8]):
            cls = classified.get(i, {})
            item = NewsItem(
                headline=raw.get("title", ""),
                url=raw.get("url", ""),
                published_at=raw.get("published_date", ""),
                sentiment=cls.get("sentiment", "neutral"),
                sentiment_reason=cls.get("sentiment_reason", ""),
                source=raw.get("source", ""),
            )
            news_items.append(item)
            new_sources.append(
                Source(
                    id=f"NEWS-{i+1:02d}",
                    url=raw.get("url", ""),
                    title=raw.get("title", ""),
                    snippet=raw.get("content", "")[:400],
                    source_type="news",
                )
            )

        overall = result.get("overall_sentiment", "neutral")
        key_catalysts = result.get("key_catalysts", [])
        news_summary = result.get("news_summary", "")

        # Enrich summary with sentiment counts
        pos = sum(1 for n in news_items if n.sentiment == "positive")
        neg = sum(1 for n in news_items if n.sentiment == "negative")
        neu = sum(1 for n in news_items if n.sentiment == "neutral")

        full_summary = (
            f"**News Sentiment ({state.ticker}):** {overall.upper()} "
            f"({pos} positive / {neg} negative / {neu} neutral)\n\n"
            f"{news_summary}"
        )
        if key_catalysts:
            full_summary += "\n\n**Key Catalysts:**\n" + "\n".join(f"• {c}" for c in key_catalysts)

        # Merge sources
        existing_urls = {s.url for s in state.sources}
        merged_sources = list(state.sources) + [s for s in new_sources if s.url not in existing_urls]

        log.status = AgentStatus.DONE
        log.message = f"{len(news_items)} articles | Overall: {overall}"
        log.output_preview = full_summary[:200]

        logger.info(f"[Pulse] {log.message}")

        return {
            "news_items": news_items,
            "news_summary": full_summary,
            "sources": merged_sources,
            "current_agent": "filings",
            "agent_logs": state.agent_logs + [log],
        }
