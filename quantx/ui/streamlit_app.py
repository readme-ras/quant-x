"""
QuantX - Streamlit Web UI (fixed - no threading)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QuantX — AI Equity Research",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.big-title {
    font-size: 2.5rem; font-weight: 700;
    background: linear-gradient(135deg, #00d4ff, #7b2ff7);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.agent-card {
    background: #111827; border: 1px solid #1f2937;
    border-radius: 10px; padding: 12px 16px; margin-bottom: 8px;
}
.agent-done { border-color: #10b981; }
.agent-fail { border-color: #ef4444; }
.metric-box {
    background: #111827; border: 1px solid #1f2937;
    border-radius: 10px; padding: 14px; text-align: center;
}
.metric-val { font-size: 1.6rem; font-weight: 700; color: #00d4ff; }
.metric-lbl { font-size: 0.72rem; color: #6b7280; text-transform: uppercase; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ── Session init ──────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "approved" not in st.session_state:
    st.session_state.approved = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="big-title">QuantX</div>', unsafe_allow_html=True)
    st.markdown("**AI Equity Research Analyst**")
    st.markdown("---")

    from tools.llm import is_ollama_running, is_model_available
    groq_ok = is_ollama_running()
    st.markdown(f"{'🟢' if groq_ok else '🔴'} Groq API: {'Connected' if groq_ok else 'No API key'}")
    tavily_ok = bool(os.getenv("TAVILY_API_KEY"))
    st.markdown(f"{'🟢' if tavily_ok else '🟡'} Tavily: {'Connected' if tavily_ok else 'Not set'}")
    st.markdown("---")

    st.markdown("### Example Queries")
    examples = ["Analyze NVDA", "Is AAPL a buy?", "TSLA investment thesis",
                "Microsoft stock outlook", "AMD semiconductor analysis"]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}"):
            st.session_state.run_query = ex
            st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<h1 class="big-title">QuantX AlphaAgents 📊</h1>', unsafe_allow_html=True)
st.markdown("Multi-agent AI equity research — 9 agents, cited research note, human review.")
st.markdown("---")

# ── Query input ───────────────────────────────────────────────────────────────
col1, col2 = st.columns([5, 1])
with col1:
    default_query = st.session_state.get("run_query", "")
    query = st.text_input(
        "Enter your research query",
        value=default_query,
        placeholder="e.g. Analyze NVDA  |  Is AAPL a buy?  |  TSLA outlook",
        label_visibility="collapsed",
    )
with col2:
    run_btn = st.button("🔍 Research", type="primary", use_container_width=True)

# Clear the pre-filled query after use
if "run_query" in st.session_state:
    del st.session_state.run_query

st.markdown("---")

# ── Run pipeline ──────────────────────────────────────────────────────────────
if run_btn and query.strip():
    if not groq_ok:
        st.error("GROQ_API_KEY not set in .env file.")
        st.stop()

    st.session_state.result = None
    st.session_state.approved = False

    # Show live agent progress while running
    st.markdown(f"### 🔄 Researching: `{query}`")
    progress_bar = st.progress(0, text="Starting pipeline...")

    agent_names = [
        "QuantX-Orchestrator", "QuantX-Scout", "QuantX-Ledger",
        "QuantX-Pulse", "QuantX-Filing", "QuantX-Bull",
        "QuantX-Bear", "QuantX-Scribe", "QuantX-Auditor"
    ]
    status_placeholders = []
    for i, name in enumerate(agent_names):
        ph = st.empty()
        ph.markdown(f"⏳ **{name}** — waiting...")
        status_placeholders.append(ph)

    import time
    start_time = time.time()

    try:
        # Patch agents to update UI as they run
        import agents.orchestrator as orch_mod
        import agents.web_researcher as scout_mod
        import agents.financial_data as ledger_mod
        import agents.news_agent as pulse_mod
        import agents.filings_agent as filing_mod
        import agents.debate as debate_mod
        import agents.writer as writer_mod
        import agents.critic as critic_mod

        original_funcs = {
            "orchestrator": orch_mod.run_orchestrator,
            "web_researcher": scout_mod.run_web_researcher,
            "financial_data": ledger_mod.run_financial_data,
            "news": pulse_mod.run_news_agent,
            "filings": filing_mod.run_filings_agent,
            "bull": debate_mod.run_bull_agent,
            "bear": debate_mod.run_bear_agent,
            "writer": writer_mod.run_writer,
            "critic": critic_mod.run_critic,
        }

        def make_wrapper(idx, name, func):
            def wrapper(state):
                status_placeholders[idx].markdown(f"⚡ **{agent_names[idx]}** — running...")
                progress_bar.progress((idx) / 9, text=f"Running {agent_names[idx]}...")
                result = func(state)
                elapsed = time.time() - start_time
                status_placeholders[idx].markdown(
                    f"✅ **{agent_names[idx]}** — done ({elapsed:.0f}s)"
                )
                return result
            return wrapper

        orch_mod.run_orchestrator = make_wrapper(0, "orchestrator", original_funcs["orchestrator"])
        scout_mod.run_web_researcher = make_wrapper(1, "web_researcher", original_funcs["web_researcher"])
        ledger_mod.run_financial_data = make_wrapper(2, "financial_data", original_funcs["financial_data"])
        pulse_mod.run_news_agent = make_wrapper(3, "news", original_funcs["news"])
        filing_mod.run_filings_agent = make_wrapper(4, "filings", original_funcs["filings"])
        debate_mod.run_bull_agent = make_wrapper(5, "bull", original_funcs["bull"])
        debate_mod.run_bear_agent = make_wrapper(6, "bear", original_funcs["bear"])
        writer_mod.run_writer = make_wrapper(7, "writer", original_funcs["writer"])
        critic_mod.run_critic = make_wrapper(8, "critic", original_funcs["critic"])

        from graph.build_graph import run_pipeline
        result = run_pipeline(query.strip(), thread_id=f"ui_{int(time.time())}")

        # Restore original functions
        orch_mod.run_orchestrator = original_funcs["orchestrator"]
        scout_mod.run_web_researcher = original_funcs["web_researcher"]
        ledger_mod.run_financial_data = original_funcs["financial_data"]
        pulse_mod.run_news_agent = original_funcs["news"]
        filing_mod.run_filings_agent = original_funcs["filings"]
        debate_mod.run_bull_agent = original_funcs["bull"]
        debate_mod.run_bear_agent = original_funcs["bear"]
        writer_mod.run_writer = original_funcs["writer"]
        critic_mod.run_critic = original_funcs["critic"]

        elapsed_total = time.time() - start_time
        progress_bar.progress(1.0, text=f"Complete in {elapsed_total:.0f}s!")
        st.session_state.result = result
        st.success(f"✅ Research complete in {elapsed_total:.0f}s!")
        st.rerun()

    except Exception as e:
        st.error(f"Pipeline error: {e}")
        import traceback
        st.code(traceback.format_exc())

# ── Display results ───────────────────────────────────────────────────────────
result = st.session_state.result

if result and result.draft:
    # Metrics row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-box"><div class="metric-val">{result.ticker}</div><div class="metric-lbl">Ticker</div></div>', unsafe_allow_html=True)
    with c2:
        done = sum(1 for l in result.agent_logs if l.status.value == "done")
        st.markdown(f'<div class="metric-box"><div class="metric-val">{done}/9</div><div class="metric-lbl">Agents Done</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-box"><div class="metric-val">{len(result.sources)}</div><div class="metric-lbl">Sources</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-box"><div class="metric-val">{result.revision_count}</div><div class="metric-lbl">Revisions</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Research Note", "🤖 Agents", "📊 Financials",
        "⚖️ Bull vs Bear", "🔍 Sources", "✅ HITL Review"
    ])

    # ── Tab 1: Research Note ──────────────────────────────────────────────────
    with tab1:
        st.markdown(f"## {result.company_name} ({result.ticker})")
        draft_upper = result.draft.upper()[:300]
        rec = "BUY" if "BUY" in draft_upper else "SELL" if "SELL" in draft_upper else "HOLD"
        color = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}[rec]
        st.markdown(f"### {color} Recommendation: {rec}")
        st.markdown("---")
        st.markdown(result.draft)
        st.download_button(
            "📥 Download as Markdown",
            data=result.draft,
            file_name=f"QuantX_{result.ticker}_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
        )

    # ── Tab 2: Agents ─────────────────────────────────────────────────────────
    with tab2:
        st.markdown("### Agent Execution Log")
        if result.agent_logs:
            for log in result.agent_logs:
                status = log.status.value
                icon = {"done": "✅", "failed": "❌", "running": "⚡", "skipped": "⏭️"}.get(status, "⏳")
                with st.expander(f"{icon} {log.agent_name} — {log.message}"):
                    if log.output_preview:
                        st.markdown(log.output_preview)
        else:
            st.info("No agent logs available.")

        if result.sub_tasks:
            st.markdown("### Research Sub-Tasks")
            for i, t in enumerate(result.sub_tasks, 1):
                st.markdown(f"{i}. {t}")

    # ── Tab 3: Financials ─────────────────────────────────────────────────────
    with tab3:
        col_f, col_o = st.columns(2)
        with col_f:
            st.markdown("### Fundamentals")
            if result.financial_data and not result.financial_data.error:
                fd = result.financial_data
                rows = {
                    "Price": f"${fd.current_price:.2f}" if fd.current_price else "N/A",
                    "Market Cap": f"${fd.market_cap/1e9:.1f}B" if fd.market_cap else "N/A",
                    "P/E (TTM)": f"{fd.pe_ratio:.1f}x" if fd.pe_ratio else "N/A",
                    "P/E (Fwd)": f"{fd.forward_pe:.1f}x" if fd.forward_pe else "N/A",
                    "P/B": f"{fd.price_to_book:.2f}x" if fd.price_to_book else "N/A",
                    "Debt/Equity": f"{fd.debt_to_equity:.2f}" if fd.debt_to_equity else "N/A",
                    "Gross Margin": f"{fd.gross_margin*100:.1f}%" if fd.gross_margin else "N/A",
                    "Op. Margin": f"{fd.operating_margin*100:.1f}%" if fd.operating_margin else "N/A",
                    "ROE": f"{fd.roe*100:.1f}%" if fd.roe else "N/A",
                    "Beta": f"{fd.beta:.2f}" if fd.beta else "N/A",
                    "52W High": f"${fd.fifty_two_week_high:.2f}" if fd.fifty_two_week_high else "N/A",
                    "52W Low": f"${fd.fifty_two_week_low:.2f}" if fd.fifty_two_week_low else "N/A",
                    "Analyst Target": f"${fd.analyst_target:.2f}" if fd.analyst_target else "N/A",
                }
                for label, val in rows.items():
                    a, b = st.columns([2, 1])
                    a.markdown(f"**{label}**")
                    b.markdown(val)
            else:
                st.warning("Financial data not available.")

        with col_o:
            st.markdown("### Options & Derivatives")
            if result.options_data:
                od = result.options_data
                sig_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(od.sentiment_signal, "🟡")
                st.markdown(f"**Signal:** {sig_icon} {od.sentiment_signal.upper()}")
                if od.put_call_ratio:
                    st.markdown(f"**Put/Call Ratio:** {od.put_call_ratio:.2f}")
                if od.implied_volatility:
                    st.markdown(f"**Avg IV:** {od.implied_volatility*100:.1f}%")
                if od.iv_skew:
                    st.markdown(f"**IV Skew:** {od.iv_skew:.2f}")
                st.markdown("---")
                st.markdown(od.summary)
            else:
                st.info("Options data not available.")

        st.markdown("### Recent News")
        if result.news_items:
            for item in result.news_items:
                icon = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}.get(item.sentiment, "⚪")
                st.markdown(f"{icon} **[{item.headline}]({item.url})**  \n_{item.sentiment_reason}_")
        else:
            st.info("No news items. Add TAVILY_API_KEY to .env for live news.")

    # ── Tab 4: Bull vs Bear ───────────────────────────────────────────────────
    with tab4:
        bc, br = st.columns(2)
        with bc:
            st.markdown(result.bull_case or "*Bull case not generated.*")
        with br:
            st.markdown(result.bear_case or "*Bear case not generated.*")

        if result.critique:
            st.markdown("---")
            st.markdown(f"### Auditor Feedback ({len(result.critique)} issues found)")
            for c in result.critique:
                icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(c.severity, "🟡")
                st.markdown(f"{icon} **{c.issue}** — {c.suggestion}")

    # ── Tab 5: Sources ────────────────────────────────────────────────────────
    with tab5:
        st.markdown(f"### {len(result.sources)} Sources")
        if result.sources:
            for s in result.sources:
                icon = {"web": "🌐", "news": "📰", "filing": "📄"}.get(s.source_type, "🔗")
                with st.expander(f"{icon} [{s.id}] {s.title[:70]}"):
                    st.markdown(f"**URL:** {s.url}")
                    st.markdown(f"**Excerpt:** {s.snippet}")
        else:
            st.info("No sources. Add TAVILY_API_KEY to .env for web sources.")

    # ── Tab 6: HITL ───────────────────────────────────────────────────────────
    with tab6:
        st.markdown("### 👤 Human Analyst Review")
        if not st.session_state.approved:
            edited = st.text_area("Edit the research note before publishing:", value=result.draft, height=400)
            a_col, r_col = st.columns(2)
            with a_col:
                if st.button("✅ Approve & Publish", type="primary"):
                    st.session_state.approved = True
                    result.final_note = edited
                    result.human_approved = True
                    st.rerun()
            with r_col:
                if st.button("🔄 Run New Research"):
                    st.session_state.result = None
                    st.session_state.approved = False
                    st.rerun()
        else:
            st.success("✅ Published!")
            st.markdown(result.final_note or result.draft)
            st.download_button(
                "📥 Download Final Note",
                data=result.final_note or result.draft,
                file_name=f"QuantX_{result.ticker}_FINAL.md",
                mime="text/markdown",
            )

elif not result:
    st.markdown("### How it works")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**9 Specialized Agents**\n\nOrchestrator → Scout → Ledger → Pulse → Filing → Bull → Bear → Scribe → Auditor")
    with c2:
        st.info("**Reflexion Loop**\n\nAuditor reviews the draft and sends it back for revision up to 3 times.")
    with c3:
        st.info("**Human-in-the-Loop**\n\nEvery note goes through human review before publishing.")
    st.markdown("*Enter a query above and click Research to start.*")