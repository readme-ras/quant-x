# QuantX AlphaAgents 📊

> Multi-agent AI equity research system — from a one-line query to a cited, professional research note in minutes.

Built for **AlphaDesk**, a wealth-tech startup. Senior analysts take 4–8 hours per note. QuantX does it in under 5 minutes using 9 specialized AI agents running on **Llama 3.3 70B via Groq** (free, fast, no timeouts).

---

## What It Does

You type: `Analyze NVDA`

QuantX runs 9 agents in sequence, pulls real financial data, searches the web, reads SEC filings, argues both sides of the trade, writes a full research note, audits it, and hands it to you for review.

**Output includes:**
- Investment thesis with BUY / HOLD / SELL recommendation
- Full fundamentals and ratio analysis
- Options/derivatives sentiment (put/call ratio, IV skew)
- Last 7 days of news with sentiment classification
- SEC 10-K/10-Q risk factors
- Bull case vs bear case debate
- Every claim cited to a source

---

## The 9 Agents

| Agent | Name | What it does |
|---|---|---|
| 1 | **QuantX-Orchestrator** | Extracts ticker, plans research sub-tasks |
| 2 | **QuantX-Scout** | Searches web via Tavily, builds cited summary |
| 3 | **QuantX-Ledger** | Pulls fundamentals, ratios, options data via yfinance |
| 4 | **QuantX-Pulse** | Last 7 days of news, sentiment classification |
| 5 | **QuantX-Filing** | SEC EDGAR 10-K/10-Q risk factor extraction |
| 6 | **QuantX-Bull** | Builds strongest bullish investment case |
| 7 | **QuantX-Bear** | Builds strongest bearish investment case |
| 8 | **QuantX-Scribe** | Synthesizes everything into the research note |
| 9 | **QuantX-Auditor** | Scores the draft, triggers revisions if quality < 80% |

After the Auditor passes the note, it goes to a **Human-in-the-Loop** checkpoint where you approve or edit before publishing.

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Agent orchestration | LangGraph | Explicit state graph, conditional edges, Reflexion loop |
| LLM | Llama 3.3 70B via Groq | Free, fast (~2-3 min full pipeline), no timeouts |
| State management | Pydantic v2 | Typed contract between all agents |
| Financial data | yfinance | Free, no API key, covers fundamentals + options chain |
| Web search | Tavily API | Free tier (1000 searches/month), news + web in one |
| SEC filings | SEC EDGAR public API | Free, no key, full 10-K/10-Q access |
| UI | Streamlit | Live agent pipeline dashboard |
| Observability | Langfuse (optional) | Trace every agent call |

---

## Project Structure

```
quantx/
├── agents/
│   ├── orchestrator.py      # QuantX-Orchestrator
│   ├── web_researcher.py    # QuantX-Scout
│   ├── financial_data.py    # QuantX-Ledger (fundamentals + options)
│   ├── news_agent.py        # QuantX-Pulse
│   ├── filings_agent.py     # QuantX-Filing
│   ├── debate.py            # QuantX-Bull + QuantX-Bear
│   ├── writer.py            # QuantX-Scribe
│   └── critic.py            # QuantX-Auditor
├── graph/
│   └── build_graph.py       # LangGraph StateGraph — wires all 9 agents
├── schemas/
│   └── state.py             # ResearchState — shared Pydantic model
├── tools/
│   ├── llm.py               # Groq API client (Llama 3.3 70B)
│   ├── financial.py         # yfinance fundamentals + options tools
│   └── search.py            # Tavily search + SEC EDGAR fetcher
├── eval/
│   └── run_eval.py          # 20-query eval harness (LLM-as-judge)
├── ui/
│   └── streamlit_app.py     # Live web dashboard
├── tracing/
│   └── setup.py             # Langfuse observability
├── docs/
│   └── ADRs/
│       └── ADR-001-framework-choices.md
├── requirements.txt
└── .env.example
```

---

## Setup

### Step 1 — Clone and create virtual environment

```bash
git clone https://github.com/yourusername/quantx.git
cd quantx

python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 2 — Get API keys

**Groq (required)** — free at [console.groq.com](https://console.groq.com)
- Sign up → API Keys → Create key
- Gives you Llama 3.3 70B for free with generous rate limits

**Tavily (recommended)** — free at [tavily.com](https://tavily.com)
- 1000 searches/month free
- Powers web research and news for QuantX-Scout and QuantX-Pulse
- Without this, those agents skip gracefully — pipeline still works

### Step 3 — Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
GROQ_API_KEY=gsk_your_key_here
TAVILY_API_KEY=tvly_your_key_here   # optional but recommended
```

### Step 4 — Run

```bash
streamlit run ui/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Usage

### Web UI

1. Type a query: `Analyze NVDA` or `Is AAPL a buy?` or `TSLA investment thesis`
2. Watch all 9 agents run live with timing per agent
3. Read the research note across 6 tabs (note, pipeline, financials, bull/bear, sources, review)
4. Approve or edit in the HITL tab

### Python API

```python
from graph.build_graph import run_pipeline

result = run_pipeline("Analyze NVDA")

print(result.ticker)           # NVDA
print(result.company_name)     # NVIDIA Corporation
print(result.draft)            # Full research note (markdown)
print(result.bull_case)        # Bull argument
print(result.bear_case)        # Bear argument
print(len(result.sources))     # Number of cited sources
print(result.financial_data)   # Fundamentals + ratios
print(result.options_data)     # Put/call ratio, IV skew
```

### Eval harness

```bash
# Quick eval — 5 queries (~15 min)
python eval/run_eval.py --n 5

# Full eval — 20 queries (~1 hr)
python eval/run_eval.py --n 20

# Results saved to eval/eval_report.json
```

---

## Architecture

```
User query
    │
    ▼
QuantX-Orchestrator ── extracts ticker, plans sub-tasks
    │
    ├── QuantX-Scout    ── Tavily web search + cited summary
    ├── QuantX-Ledger   ── yfinance fundamentals + options chain
    ├── QuantX-Pulse    ── news sentiment (last 7 days)
    └── QuantX-Filing   ── SEC EDGAR 10-K/10-Q risks
                │
                ▼
    QuantX-Bull  ◄── builds strongest bull case
    QuantX-Bear  ◄── builds strongest bear case (independent)
                │
                ▼
    QuantX-Scribe ── synthesizes all research into note
                │
                ▼
    QuantX-Auditor ── scores 0-100, checks citations
       │                    │
       │ score ≥ 80         │ score < 80 (max 3 revisions)
       ▼                    └──────► QuantX-Scribe (revision)
    HITL Checkpoint ── human approves/edits
                │
                ▼
    Published Research Note
```

**Reflexion loop:** Auditor scores the draft. Below 80 → structured feedback sent back to Scribe for revision. Capped at 3 revisions. This is what makes the output genuinely better than a single-pass LLM call.

**Citation enforcement:** Every source gets an ID (`[WEB-01]`, `[NEWS-02]`, `[FILING-01]`). Agents must reference these IDs in every factual claim. Auditor flags unsupported claims.

**Typed state:** One `ResearchState` Pydantic model flows through every agent. No agent can pass garbage to the next.

---

## API Keys Reference

| Service | Required | Free Tier | Link |
|---|---|---|---|
| Groq | ✅ Yes | Generous free tier, Llama 3.3 70B | [console.groq.com](https://console.groq.com) |
| Tavily | 🟡 Recommended | 1000 searches/month | [tavily.com](https://tavily.com) |
| yfinance | ✅ Built-in | Unlimited | No key needed |
| SEC EDGAR | ✅ Built-in | Unlimited | No key needed |
| Langfuse | ❌ Optional | Free cloud tier | [cloud.langfuse.com](https://cloud.langfuse.com) |

---

## Troubleshooting

**"GROQ_API_KEY not set"**
→ Make sure `.env` has `GROQ_API_KEY=gsk_...` with no spaces. Run `cat .env` to verify.

**"No web results"**
→ Add `TAVILY_API_KEY` to `.env`. Without it, Scout and Pulse skip gracefully but the note will be thinner.

**Empty ticker / wrong company**
→ Be explicit: `Analyze NVDA` works better than `should I invest in the chip company`. The orchestrator regex catches most tickers directly.

**Pipeline errors mid-run**
→ Check `tools/llm.py` — make sure `GROQ_API_KEY` is loading. Run `python -c "from tools.llm import call_llm_json; print(call_llm_json('say hi', system='respond in json: {\"hi\": true}'))"` to test the LLM directly.

**Streamlit shows nothing after clicking Research**
→ Check the terminal running Streamlit for the actual error. The UI runs the pipeline synchronously so any error prints there.

---

## Extending QuantX

**Swap to Claude API**
Replace `tools/llm.py` with Anthropic's client. Claude's native tool use means cleaner function calling without the JSON-mode workaround.

**Add Chroma long-term memory**
Store past research notes in Chroma. Future queries on the same ticker retrieve cached context before running expensive agents.

**Add a Moderator debate agent**
A 10th agent that scores bull vs. bear arguments by evidence strength before passing to the writer — makes the synthesis more rigorous.

**Real-time streaming UI**
Replace Streamlit's synchronous model with FastAPI + SSE for true real-time token streaming per agent.

---

## Resume / Interview Talking Points

- Built a **9-agent LangGraph pipeline** with Reflexion loop — critic scores drafts 0-100, triggers writer revisions until quality threshold met
- **Citation enforcement via Pydantic schema** — every claim must reference a source ID, auditor flags violations
- Added **derivatives/options layer** (put/call ratio, IV skew via yfinance) as a signal not in typical student projects
- Switched from local Phi-4-mini to **Groq + Llama 3.3 70B** after diagnosing timeout issues — documented the trade-off in ADR-001
- **20-query eval harness** with LLM-as-judge scoring on factuality, completeness, citation density, actionability, risk coverage
- **Human-in-the-Loop** checkpoint with Streamlit approve/edit interface
- Pipeline runs on **free APIs only** — Groq, Tavily free tier, yfinance, SEC EDGAR public API

---

## Architecture Decision Records

See `docs/ADRs/ADR-001-framework-choices.md` for:
- Why LangGraph over CrewAI and AutoGen
- Why Groq + Llama 3.3 70B over local Phi-4-mini
- Why JSON-mode tool calling over native function calling
- Why yfinance + SEC EDGAR over paid financial APIs
- Why derivatives folded into QuantX-Ledger rather than a separate agent

---

*QuantX AlphaAgents — Built during Applied GenAI Engineering internship, 2025*
*AlphaDesk · E1: Agentic Research Analyst — Multi-Agent Equity Research*