"""
QuantX - LangGraph StateGraph (fixed state passing)
"""

import logging
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


# ── Use plain dict as state (most reliable with LangGraph) ──────────────────
class QuantXState(TypedDict, total=False):
    query: str
    ticker: str
    company_name: str
    sub_tasks: list
    research_plan: str
    sources: list
    web_summary: str
    financial_data: Any
    options_data: Any
    news_items: list
    news_summary: str
    filing_excerpts: list
    filing_risks: str
    bull_case: str
    bear_case: str
    draft: str
    citations: list
    critique: list
    critique_passed: bool
    revision_count: int
    max_revisions: int
    human_approved: bool
    human_edits: str
    final_note: str
    agent_logs: list
    current_agent: str
    error: Any
    is_complete: bool


def make_state(d: dict):
    """Convert raw dict to ResearchState, safely."""
    from schemas.state import ResearchState
    try:
        return ResearchState(**{k: v for k, v in d.items() if v is not None})
    except Exception as e:
        logger.warning(f"State conversion warning: {e}")
        return ResearchState(query=d.get("query", ""))


def node_orchestrator(state: dict) -> dict:
    from agents.orchestrator import run_orchestrator
    result = run_orchestrator(make_state(state))
    logger.info(f"[Graph] orchestrator → ticker={result.get('ticker', '?')}")
    return result


def node_web_researcher(state: dict) -> dict:
    from agents.web_researcher import run_web_researcher
    s = make_state(state)
    logger.info(f"[Graph] web_researcher → ticker={s.ticker}")
    result = run_web_researcher(s)
    return result


def node_financial_data(state: dict) -> dict:
    from agents.financial_data import run_financial_data
    s = make_state(state)
    logger.info(f"[Graph] financial_data → ticker={s.ticker}")
    result = run_financial_data(s)
    return result


def node_news(state: dict) -> dict:
    from agents.news_agent import run_news_agent
    s = make_state(state)
    logger.info(f"[Graph] news → ticker={s.ticker}")
    return run_news_agent(s)


def node_filings(state: dict) -> dict:
    from agents.filings_agent import run_filings_agent
    s = make_state(state)
    logger.info(f"[Graph] filings → ticker={s.ticker}")
    return run_filings_agent(s)


def node_bull(state: dict) -> dict:
    from agents.debate import run_bull_agent
    s = make_state(state)
    logger.info(f"[Graph] bull → ticker={s.ticker}")
    return run_bull_agent(s)


def node_bear(state: dict) -> dict:
    from agents.debate import run_bear_agent
    s = make_state(state)
    logger.info(f"[Graph] bear → ticker={s.ticker}")
    return run_bear_agent(s)


def node_writer(state: dict) -> dict:
    from agents.writer import run_writer
    s = make_state(state)
    logger.info(f"[Graph] writer → ticker={s.ticker}, revision={s.revision_count}")
    return run_writer(s)


def node_critic(state: dict) -> dict:
    from agents.critic import run_critic
    s = make_state(state)
    logger.info(f"[Graph] critic → ticker={s.ticker}")
    return run_critic(s)


def node_hitl(state: dict) -> dict:
    from schemas.state import AgentLog, AgentStatus
    logger.info("[Graph] hitl → pipeline complete")
    log = AgentLog(
        agent_name="HITL Checkpoint",
        status=AgentStatus.DONE,
        message="Awaiting human analyst review",
        output_preview="Research note ready.",
    )
    existing_logs = state.get("agent_logs", [])
    return {
        "final_note": state.get("human_edits") or state.get("draft", ""),
        "is_complete": True,
        "current_agent": "complete",
        "agent_logs": existing_logs + [log],
    }


def route_after_critic(state: dict) -> str:
    critique_passed = state.get("critique_passed", False)
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 3)
    if critique_passed or revision_count >= max_revisions:
        return "hitl"
    return "writer"


def build_graph():
    graph = StateGraph(QuantXState)

    graph.add_node("orchestrator", node_orchestrator)
    graph.add_node("web_researcher", node_web_researcher)
    graph.add_node("financial_data", node_financial_data)
    graph.add_node("news", node_news)
    graph.add_node("filings", node_filings)
    graph.add_node("bull", node_bull)
    graph.add_node("bear", node_bear)
    graph.add_node("writer", node_writer)
    graph.add_node("critic", node_critic)
    graph.add_node("hitl", node_hitl)

    graph.set_entry_point("orchestrator")
    graph.add_edge("orchestrator", "web_researcher")
    graph.add_edge("web_researcher", "financial_data")
    graph.add_edge("financial_data", "news")
    graph.add_edge("news", "filings")
    graph.add_edge("filings", "bull")
    graph.add_edge("bull", "bear")
    graph.add_edge("bear", "writer")
    graph.add_edge("writer", "critic")
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {"writer": "writer", "hitl": "hitl"},
    )
    graph.add_edge("hitl", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_pipeline(query: str, thread_id: str = "default"):
    from schemas.state import ResearchState
    graph = get_graph()

    initial: QuantXState = {
        "query": query,
        "ticker": "",
        "company_name": "",
        "sub_tasks": [],
        "research_plan": "",
        "sources": [],
        "web_summary": "",
        "financial_data": None,
        "options_data": None,
        "news_items": [],
        "news_summary": "",
        "filing_excerpts": [],
        "filing_risks": "",
        "bull_case": "",
        "bear_case": "",
        "draft": "",
        "citations": [],
        "critique": [],
        "critique_passed": False,
        "revision_count": 0,
        "max_revisions": 3,
        "human_approved": False,
        "human_edits": "",
        "final_note": "",
        "agent_logs": [],
        "current_agent": "orchestrator",
        "error": None,
        "is_complete": False,
    }

    config = {"configurable": {"thread_id": thread_id}}

    final_state = dict(initial)
    for step in graph.stream(initial, config=config):
        for node_name, update in step.items():
            logger.info(f"[Graph] ✓ {node_name} complete")
            if isinstance(update, dict):
                final_state.update(update)

    logger.info(f"[Graph] Final ticker: {final_state.get('ticker')}")

    try:
        return ResearchState(**{k: v for k, v in final_state.items() if v is not None})
    except Exception as e:
        logger.error(f"Final state parse error: {e}")
        rs = ResearchState(query=query)
        rs.draft = final_state.get("draft", "")
        rs.ticker = final_state.get("ticker", "")
        return rs