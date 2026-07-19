# ADR-001: Framework and Model Selection for QuantX AlphaAgents

**Date:** 2025  
**Status:** Accepted  
**Project:** QuantX — Agentic Equity Research Analyst

---

## Context

We needed to choose an agent orchestration framework, a local LLM, and supporting tools for building a 9-agent multi-agent equity research system on a MacBook with 8GB RAM.

---

## Decision 1: LangGraph over CrewAI / AutoGen

**Chosen:** LangGraph

**Reasoning:**
- LangGraph exposes an explicit `StateGraph` with typed nodes and conditional edges, making the Reflexion loop (critic → writer → critic) easy to implement and debug
- State is fully transparent — every agent reads and writes to one typed `ResearchState` object, which makes debugging straightforward
- CrewAI abstracts away too much — when a 4B model returns malformed JSON, CrewAI's abstractions obscure where the failure happened
- AutoGen is designed for multi-turn dialogue between agents, not a structured pipeline with conditional routing — our use case fits LangGraph's model more naturally
- LangGraph's `MemorySaver` checkpointing gives us the HITL pause-and-resume pattern for free

**Trade-offs accepted:**
- More boilerplate than CrewAI (explicit edge definitions, manual state updates)
- Steeper learning curve than AutoGen's conversational API

---

## Decision 2: Phi-4-mini (3.8B) over Gemma3:4B / Qwen3:7B

**Chosen:** Phi-4-mini via Ollama

**Reasoning:**
- 8GB RAM Mac leaves ~5-6GB for the model after OS overhead; Phi-4-mini at Q4_K_M quantization uses ~3.5GB
- 128K context window is unusually large for a 3.8B model — critical for the writer agent synthesizing long filing excerpts, news, and research data
- Benchmarks show Phi-4-mini performs near models twice its size on reasoning tasks
- Qwen3:7B would outperform on raw reasoning but risks OOM crashes on 8GB hardware mid-pipeline
- Gemma3:4B has documented issues skipping required output fields — unacceptable for our JSON-schema-enforced agent outputs

**Trade-offs accepted:**
- Weaker reasoning than a 7B+ model — mitigated by: explicit few-shot prompting, strict JSON schemas, and the Reflexion loop catching errors
- Local inference means slower total pipeline time (~5-10 min) vs. cloud APIs — acceptable for a research tool, not a trading signal system

---

## Decision 3: JSON-mode Tool Calling over Native Function Calling

**Chosen:** Ollama `format: json` + manual dispatch

**Reasoning:**
- Phi-4-mini does not have Claude/GPT-style native function calling
- Ollama's `format: json` forces valid JSON output at the tokenizer level, more reliable than prompt-engineering alone
- We define each "tool" as a Python function; the LLM outputs `{"tool": "...", "args": {...}}` and Python executes it
- This approach is fully transparent — no hidden function-calling abstraction that breaks silently

---

## Decision 4: yfinance + SEC EDGAR over Paid APIs

**Chosen:** yfinance (free, no key) + SEC EDGAR public API (free, no key)

**Reasoning:**
- yfinance covers all fundamentals, ratios, historical prices, and options chain data needed for a demo
- SEC EDGAR's public API provides 10-K/10-Q filings with zero rate limit issues for reasonable usage
- Paid APIs (Alpha Vantage Pro, Bloomberg, Refinitiv) add cost and complexity without meaningfully improving the research note quality for a prototype
- Tavily (free tier: 1000 searches/month) covers web + news search adequately

---

## Decision 5: Derivatives / Options as Part of QuantX-Ledger

**Chosen:** Fold options data into the financial data agent, not a standalone agent

**Reasoning:**
- yfinance's `ticker.option_chain()` is a natural extension of `ticker.info` — same client, same session
- A dedicated "options agent" would add a 10th node to the graph without meaningfully changing the architecture
- Put/call ratio and IV skew are valuable inputs to the bull/bear debate agents — available earlier if computed in QuantX-Ledger

---

## Consequences

- Pipeline runs entirely offline (no cloud LLM costs) — good for cost-conscious demos
- Phi-4-mini's limitations mean the writer/critic loop is essential (not optional)
- Total pipeline time: ~5-10 minutes depending on hardware and network speed for web/filing fetches
- This architecture ports directly to a production setup by swapping Phi-4-mini for Claude via API and Ollama for a proper inference server (vLLM/TGI)
