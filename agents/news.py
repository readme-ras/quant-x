from langgraph.types import Command

# Replace this with Tavily or NewsAPI later
def get_news(company):

    return [
        {
            "title": f"{company} launches new AI products",
            "summary": "Company announced multiple AI features."
        },
        {
            "title": f"{company} stock gains after earnings",
            "summary": "Revenue exceeded analyst expectations."
        }
    ]


def news_agent(state):

    company = state["company"]

    news = get_news(company)

    return Command(
        update={
            "news": news
        },
        goto="bull_agent"
    )