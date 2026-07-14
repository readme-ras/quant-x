from langgraph.types import Command


def bull_agent(state):

    prompt = f"""
You are a professional equity analyst.

Research:
{state["research"]}

Financials:
{state["financial_data"]}

News:
{state["news"]}

Generate a bullish investment thesis.

Return:

- Strengths
- Growth Drivers
- Competitive Advantages
- Risks ignored by market
- Final Bull Rating (/10)
"""

    response = llm.invoke(prompt)

    return Command(
        update={
            "bull_report": response.content
        },
        goto="bear_agent"
    )