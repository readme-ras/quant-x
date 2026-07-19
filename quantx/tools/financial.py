"""
QuantX - Financial Data Tools
Pulls fundamentals, ratios, and options data via yfinance (free, no API key).
"""

import yfinance as yf
import logging
from schemas.state import FinancialData, OptionsData

logger = logging.getLogger(__name__)


def get_fundamentals(ticker: str) -> FinancialData:
    """Pull fundamentals and key ratios for a ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.info

        data = FinancialData(
            ticker=ticker.upper(),
            company_name=info.get("longName", ticker),
            current_price=info.get("currentPrice") or info.get("regularMarketPrice"),
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            price_to_book=info.get("priceToBook"),
            debt_to_equity=info.get("debtToEquity"),
            revenue_growth=info.get("revenueGrowth"),
            gross_margin=info.get("grossMargins"),
            operating_margin=info.get("operatingMargins"),
            net_margin=info.get("profitMargins"),
            roe=info.get("returnOnEquity"),
            roa=info.get("returnOnAssets"),
            current_ratio=info.get("currentRatio"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            analyst_target=info.get("targetMeanPrice"),
            dividend_yield=info.get("dividendYield"),
            beta=info.get("beta"),
        )

        # Build a plain-English summary
        lines = [f"**{data.company_name} ({ticker.upper()}) — Fundamentals**"]
        if data.current_price:
            lines.append(f"- Price: ${data.current_price:.2f}")
        if data.market_cap:
            lines.append(f"- Market Cap: ${data.market_cap/1e9:.1f}B")
        if data.pe_ratio:
            lines.append(f"- P/E (trailing): {data.pe_ratio:.1f}x")
        if data.forward_pe:
            lines.append(f"- P/E (forward): {data.forward_pe:.1f}x")
        if data.price_to_book:
            lines.append(f"- P/B: {data.price_to_book:.2f}x")
        if data.debt_to_equity:
            lines.append(f"- Debt/Equity: {data.debt_to_equity:.2f}")
        if data.gross_margin:
            lines.append(f"- Gross Margin: {data.gross_margin*100:.1f}%")
        if data.operating_margin:
            lines.append(f"- Operating Margin: {data.operating_margin*100:.1f}%")
        if data.roe:
            lines.append(f"- ROE: {data.roe*100:.1f}%")
        if data.beta:
            lines.append(f"- Beta: {data.beta:.2f}")
        if data.analyst_target and data.current_price:
            upside = ((data.analyst_target - data.current_price) / data.current_price) * 100
            lines.append(f"- Analyst Target: ${data.analyst_target:.2f} ({upside:+.1f}% upside)")
        if data.fifty_two_week_high and data.fifty_two_week_low:
            lines.append(
                f"- 52-Week Range: ${data.fifty_two_week_low:.2f} – ${data.fifty_two_week_high:.2f}"
            )

        data.summary = "\n".join(lines)
        return data

    except Exception as e:
        logger.error(f"Error fetching fundamentals for {ticker}: {e}")
        return FinancialData(ticker=ticker, error=str(e))


def get_options_sentiment(ticker: str) -> OptionsData:
    """
    Pull options chain data and derive a sentiment signal.
    put/call ratio > 1 = bearish, < 0.7 = bullish, else neutral.
    IV skew: if puts have higher IV than calls = market pricing downside risk.
    """
    try:
        t = yf.Ticker(ticker)
        expirations = t.options

        if not expirations:
            return OptionsData(ticker=ticker, summary="No options data available.")

        # Use the nearest expiry
        nearest = expirations[0]
        chain = t.option_chain(nearest)
        calls = chain.calls
        puts = chain.puts

        total_call_oi = calls["openInterest"].sum() if not calls.empty else 0
        total_put_oi = puts["openInterest"].sum() if not puts.empty else 0
        pc_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else None

        # IV skew: compare ATM put vs call IV
        avg_call_iv = calls["impliedVolatility"].median() if not calls.empty else None
        avg_put_iv = puts["impliedVolatility"].median() if not puts.empty else None
        iv_skew = None
        if avg_put_iv and avg_call_iv and avg_call_iv > 0:
            iv_skew = avg_put_iv / avg_call_iv

        # Derive signal
        signal = "neutral"
        if pc_ratio is not None:
            if pc_ratio > 1.0:
                signal = "bearish"
            elif pc_ratio < 0.7:
                signal = "bullish"

        summary_parts = [f"**{ticker.upper()} — Options Sentiment (exp: {nearest})**"]
        if pc_ratio is not None:
            summary_parts.append(f"- Put/Call OI Ratio: {pc_ratio:.2f} → {signal.upper()} signal")
        if avg_call_iv:
            summary_parts.append(f"- Avg Call IV: {avg_call_iv*100:.1f}%")
        if avg_put_iv:
            summary_parts.append(f"- Avg Put IV: {avg_put_iv*100:.1f}%")
        if iv_skew:
            skew_desc = "puts pricing more downside risk" if iv_skew > 1.1 else "relatively balanced"
            summary_parts.append(f"- IV Skew (put/call): {iv_skew:.2f} ({skew_desc})")

        return OptionsData(
            ticker=ticker.upper(),
            put_call_ratio=pc_ratio,
            iv_skew=iv_skew,
            implied_volatility=avg_call_iv,
            open_interest=int(total_call_oi + total_put_oi),
            sentiment_signal=signal,
            summary="\n".join(summary_parts),
        )

    except Exception as e:
        logger.error(f"Error fetching options for {ticker}: {e}")
        return OptionsData(ticker=ticker, summary=f"Options data unavailable: {e}")


def extract_ticker_from_query(query: str) -> str:
    """
    Simple heuristic to extract a ticker from a query.
    Falls back to asking the LLM if not found.
    """
    import re
    # Match obvious ticker patterns like $NVDA or NVDA
    matches = re.findall(r'\$?([A-Z]{1,5})\b', query.upper())
    # Filter common English words
    stopwords = {"I", "A", "AN", "THE", "FOR", "IN", "ON", "AT", "IS", "IT", "AI", "AND", "OR"}
    tickers = [m for m in matches if m not in stopwords]
    if tickers:
        return tickers[0]
    return ""
