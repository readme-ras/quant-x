from langgraph.graph import StateGraph, END

from state import ResearchState

from agents.orchestrator import orchestrator
from agents.researcher import researcher
from agents.financial import financial_agent
from agents.news import news_agent
from agents.bull import bull_agent
from agents.bear import bear_agent


builder = StateGraph(ResearchState)

builder.add_node("orchestrator", orchestrator)
builder.add_node("researcher", researcher)
builder.add_node("financial_agent", financial_agent)
builder.add_node("news_agent", news_agent)
builder.add_node("bull_agent", bull_agent)
builder.add_node("bear_agent", bear_agent)

builder.set_entry_point("orchestrator")

builder.add_edge("orchestrator", "researcher")
builder.add_edge("researcher", "financial_agent")
builder.add_edge("financial_agent", "news_agent")
builder.add_edge("news_agent", "bull_agent")
builder.add_edge("bull_agent", "bear_agent")
builder.add_edge("bear_agent", END)

graph = builder.compile()