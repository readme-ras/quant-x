"""
QuantX - Search & Retrieval Tools
Tavily web search + SEC EDGAR filings retrieval.
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from schemas.state import Source, NewsItem

logger = logging.getLogger(__name__)

TAVILY_API_KEY = "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"
TAVILY_BASE_URL = "https://api.tavily.com"


# ─────────────────────────────────────────────
# Web Search (Tavily)
# ─────────────────────────────────────────────

def tavily_search(query: str, max_results: int = 5, search_depth: str = "basic") -> list[Source]:
    """Search the web using Tavily and return structured Source objects."""
    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set. Returning empty results.")
        return []

    try:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": False,
        }
        r = requests.post(f"{TAVILY_BASE_URL}/search", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()

        sources = []
        for i, result in enumerate(data.get("results", [])):
            sources.append(
                Source(
                    id=f"WEB-{i+1:02d}",
                    url=result.get("url", ""),
                    title=result.get("title", ""),
                    snippet=result.get("content", "")[:500],
                    source_type="web",
                )
            )
        return sources

    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []


def tavily_news_search(ticker: str, company_name: str, days: int = 7) -> list[dict]:
    """Search recent news for a company using Tavily."""
    if not TAVILY_API_KEY:
        return []

    query = f"{company_name} {ticker} stock news earnings analyst"
    try:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": 8,
            "search_depth": "basic",
            "topic": "news",
        }
        r = requests.post(f"{TAVILY_BASE_URL}/search", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("results", [])
    except Exception as e:
        logger.error(f"Tavily news search failed: {e}")
        return []


# ─────────────────────────────────────────────
# SEC EDGAR Filings
# ─────────────────────────────────────────────

EDGAR_BASE = "https://data.sec.gov"
EDGAR_HEADERS = {"User-Agent": "QuantX research@quantx.ai"}


def get_cik_for_ticker(ticker: str) -> str | None:
    """Resolve a ticker to a CIK number using SEC EDGAR company tickers JSON."""
    try:
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=EDGAR_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        for _, company in data.items():
            if company.get("ticker", "").upper() == ticker.upper():
                return str(company["cik_str"]).zfill(10)
        return None
    except Exception as e:
        logger.error(f"CIK lookup failed for {ticker}: {e}")
        return None


def get_latest_filing_text(ticker: str, form_type: str = "10-K") -> str:
    """
    Pull the latest 10-K or 10-Q text from SEC EDGAR for a given ticker.
    Returns a truncated string of the most relevant sections.
    """
    try:
        cik = get_cik_for_ticker(ticker)
        if not cik:
            return f"Could not find SEC filings for {ticker}."

        # Get submission history
        r = requests.get(
            f"{EDGAR_BASE}/submissions/CIK{cik}.json",
            headers=EDGAR_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        submissions = r.json()

        # Find the most recent filing of the requested type
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])

        target_accession = None
        for form, accession in zip(forms, accessions):
            if form == form_type:
                target_accession = accession.replace("-", "")
                break

        if not target_accession:
            return f"No recent {form_type} found for {ticker}."

        # Get filing index
        acc_formatted = f"{target_accession[:10]}-{target_accession[10:12]}-{target_accession[12:]}"
        index_url = f"https://www.sec.gov/Archives/edgar/full-index/{cik}/{acc_formatted}-index.htm"

        # Try to get the filing document listing
        r2 = requests.get(
            f"{EDGAR_BASE}/Archives/edgar/data/{int(cik)}/{target_accession}/{target_accession}-index.json",
            headers=EDGAR_HEADERS,
            timeout=15,
        )
        if r2.status_code != 200:
            return f"Retrieved CIK {cik} for {ticker} but could not fetch filing index."

        filing_data = r2.json()
        documents = filing_data.get("documents", [])

        # Find the main document
        main_doc = None
        for doc in documents:
            if doc.get("type") == form_type:
                main_doc = doc.get("filename")
                break

        if not main_doc:
            return f"Found {form_type} filing but could not locate main document for {ticker}."

        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{target_accession}/{main_doc}"
        r3 = requests.get(doc_url, headers=EDGAR_HEADERS, timeout=30)

        # Extract plain text (strip HTML tags crudely for brevity)
        import re
        text = re.sub(r'<[^>]+>', ' ', r3.text)
        text = re.sub(r'\s+', ' ', text)

        # Extract risk factors section
        risk_match = re.search(
            r'(RISK FACTORS|Item 1A\.?\s*Risk Factors)(.*?)(Item 1B|Item 2|UNRESOLVED)',
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if risk_match:
            risk_text = risk_match.group(2)[:4000]
            return f"**{ticker} {form_type} — Risk Factors (excerpt)**\n\n{risk_text}"

        # Fallback: return first 3000 chars of meaningful text
        return f"**{ticker} {form_type} excerpt**\n\n{text[:3000]}"

    except Exception as e:
        logger.error(f"Filing retrieval failed for {ticker}: {e}")
        return f"Could not retrieve SEC filing for {ticker}: {e}"
