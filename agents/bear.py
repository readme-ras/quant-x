from langgraph.types import Command


def bear_agent(state):

    prompt = f"""
You are a hedge fund short seller.

Research:
{state["research"]}

Financials:
{state["financial_data"]}

News:
{state["news"]}

Generate a bearish investment thesis.

Return:

- Weaknesses
- Risks
- Valuation Problems
- Industry Threats
- Final Bear Rating (/10)
"""

    response = llm.invoke(prompt)

    return Command(
        update={
            "bear_report": response.content
        },
        goto="judge_agent"
    )