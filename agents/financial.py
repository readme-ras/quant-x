from langgraph.types import Command
import yfinance as yf


def financial_agent(state):

    ticker = state["ticker"]

    stock = yf.Ticker(ticker)

    info = stock.info

    financial_data = {
        "company": info.get("longName"),
        "current_price": info.get("currentPrice"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "eps": info.get("trailingEps"),
        "revenue": info.get("totalRevenue"),
        "profit_margin": info.get("profitMargins"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "beta": info.get("beta"),
        "dividend_yield": info.get("dividendYield")
    }

    return Command(
        update={
            "financial_data": financial_data
        },
        goto="news_agent"
    )