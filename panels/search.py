"""
panels/search.py
─────────────────
Tab 3: Vector search — background-threaded with live log terminal.
Same poll pattern as embed and ask tabs.
"""
import json
import time
import streamlit as st
from core.vectorstore import submit_search, poll_search, cancel_search, get_search_logs
from ui.components    import section, stat_row, result_card, card, terminal_log


_SEARCH_MODES = {
    "similarity": {
        "label": "Semantic",
        "desc":  "Cosine similarity — best for paraphrased or conceptual queries.",
    },
    "mmr": {
        "label": "MMR  (Diverse)",
        "desc":  "Maximal Marginal Relevance — reduces redundancy, broadens coverage.",
    },
    "similarity_score_threshold": {
        "label": "Threshold",
        "desc":  "Only returns chunks scoring ≥ 0.30. Fewer but more confident results.",
    },
}


def _fmt_elapsed(s: float) -> str:
    s = int(s)
    return f"{s//60}m {s%60}s" if s >= 60 else f"{s}s"


def panel():
    vs = st.session_state.get("vectorstore")
    if vs is None:
        card(
            '<b style="color:#e2e8f8">No vector store loaded.</b><br>'
            '<span style="font-size:0.78rem">Go to <b>Embed</b> tab and run embedding first.</span>',
            variant="warn",
        )
        return

    # ══════════════════════════════════════════════════════════════
    # RUNNING — poll background thread, show live terminal
    # ══════════════════════════════════════════════════════════════
    job_id = st.session_state.get("search_job_id")
    if job_id:
        state, payload = poll_search(job_id)
        elapsed = time.time() - st.session_state.get("search_start_time", time.time())

        if state == "done":
            st.session_state.search_results   = payload
            st.session_state.last_query       = st.session_state.get("search_q_display","")
            st.session_state.search_did_run   = True
            st.session_state.search_elapsed   = elapsed
            st.session_state.search_logs      = get_search_logs(job_id)
            st.session_state.search_status    = "done"
            st.session_state.pop("search_job_id",    None)
            st.session_state.pop("search_start_time", None)
            st.rerun(); return

        if state == "error":
            st.session_state.search_did_run = True
            st.session_state.search_status  = "error"
            st.session_state.search_logs    = payload
            st.session_state.pop("search_job_id",    None)
            st.session_state.pop("search_start_time", None)
            st.rerun(); return

        # Still running — show live log
        logs = payload
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.6rem">'
            f'<div class="dot dot-pulse"></div>'
            f'<span style="font-family:Space Grotesk,sans-serif;font-weight:600;'
            f'color:#00d4aa;font-size:0.9rem">Searching…</span>'
            f'<span style="margin-left:auto;font-size:0.72rem;color:#4a5a7a">'
            f'{_fmt_elapsed(elapsed)}</span></div>',
            unsafe_allow_html=True,
        )
        terminal_log(logs, title="search.log")

        if st.button("✕  Cancel", key="cancel_search"):
            cancel_search(job_id)
            st.session_state.search_status = "idle"
            st.session_state.pop("search_job_id",    None)
            st.session_state.pop("search_start_time", None)
            st.rerun(); return

        time.sleep(0.8); st.rerun(); return

    # ══════════════════════════════════════════════════════════════
    # IDLE — show form
    # ══════════════════════════════════════════════════════════════
    section("Query")
    query = st.text_input(
        "Enter your query",
        placeholder="What is the main argument of the document?",
        label_visibility="collapsed",
        key="search_query",
    )

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        mode = st.selectbox(
            "Mode",
            options=list(_SEARCH_MODES.keys()),
            format_func=lambda k: _SEARCH_MODES[k]["label"],
            key="search_mode",
        )
    with c2:
        top_k = st.number_input("Results (k)", min_value=1, max_value=20,
                                value=st.session_state.top_k, step=1,
                                key="top_k_input")
    with c3:
        filter_page = st.number_input("Filter page (0 = all)", min_value=0,
                                      max_value=9999, value=0, step=1,
                                      key="filter_page")

    st.markdown(
        f'<div class="cfg-hint" style="margin-bottom:0.8rem">'
        f'{_SEARCH_MODES[mode]["desc"]}</div>',
        unsafe_allow_html=True,
    )

    # Track if mode/k changed since last search — show "settings changed" hint
    last_mode = st.session_state.get("search_last_mode")
    last_k    = st.session_state.get("search_last_k")
    settings_changed = (
        st.session_state.get("search_did_run") and
        (mode != last_mode or int(top_k) != last_k)
    )
    if settings_changed:
        st.markdown(
            '<div style="font-size:0.68rem;color:#fbbf24;margin-bottom:0.5rem">'
            '⚙ Settings changed — press Search to apply.</div>',
            unsafe_allow_html=True,
        )

    run = st.button("⬡  Search", key="run_search", disabled=(not query.strip()))

    if run and query.strip():
        filter_meta = {"page": filter_page - 1} if filter_page > 0 else None
        job_id = submit_search(vs, query.strip(), mode, int(top_k), filter_meta)
        st.session_state.search_job_id     = job_id
        st.session_state.search_start_time = time.time()
        st.session_state.search_q_display  = query.strip()
        st.session_state.search_status     = "searching"
        st.session_state.search_last_mode  = mode
        st.session_state.search_last_k     = int(top_k)
        # Clear old results so the log is visible immediately
        st.session_state.search_results    = []
        st.rerun(); return

    # ══════════════════════════════════════════════════════════════
    # LOG — show last search log collapsed (always available)
    # ══════════════════════════════════════════════════════════════
    search_logs = st.session_state.get("search_logs", [])
    if search_logs:
        with st.expander("📋  Last search log", expanded=False):
            terminal_log(search_logs, title="search.log")

    # ══════════════════════════════════════════════════════════════
    # ERROR state
    # ══════════════════════════════════════════════════════════════
    if st.session_state.get("search_status") == "error":
        logs = st.session_state.get("search_logs", [])
        st.error(f"Search failed: {logs[-1] if logs else 'unknown'}")
        return

    # ══════════════════════════════════════════════════════════════
    # RESULTS
    # ══════════════════════════════════════════════════════════════
    results   = st.session_state.get("search_results", [])
    did_search = st.session_state.get("search_did_run", False)
    elapsed    = st.session_state.get("search_elapsed", 0)

    if not results:
        if not did_search:
            st.markdown(
                '<div class="card" style="text-align:center;padding:2rem;opacity:0.5">'
                '<div style="font-size:1.8rem;margin-bottom:0.5rem">🔍</div>'
                '<div style="font-family:Space Grotesk,sans-serif;font-weight:600;'
                'color:#e2e8f8;font-size:0.9rem">Ready to search</div>'
                '<div style="font-size:0.7rem;color:#4a5a7a;margin-top:0.3rem">'
                'Type a query above and press Search</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="card card-warn" style="text-align:center;padding:1.5rem">'
                '<div style="font-size:1.4rem;margin-bottom:0.5rem">🔍</div>'
                '<div style="font-family:Space Grotesk,sans-serif;font-weight:600;'
                'color:#fbbf24;font-size:0.9rem">No results found</div>'
                '<div style="font-size:0.72rem;color:#4a5a7a;margin-top:0.4rem">'
                'Try a different query, lower the threshold, or switch mode.</div></div>',
                unsafe_allow_html=True,
            )
        return

    last_q    = st.session_state.get("last_query","")
    section(f'Results — "{last_q[:60]}{"…" if len(last_q)>60 else ""}"')

    scores    = [r["score"] for r in results if r["score"] is not None]
    avg_score = sum(scores)/len(scores) if scores else None
    stat_row([
        (len(results),                                     "Results"),
        (f"{int(avg_score*100)}%" if avg_score else "—",  "Avg score"),
        (f"{elapsed:.1f}s",                                "Time"),
        (_SEARCH_MODES[mode]["label"],                     "Mode"),
    ])

    for i, r in enumerate(results, 1):
        result_card(i, r["text"], r["metadata"], r["score"])

    # ── Export ────────────────────────────────────────────────────
    section("Export")
    export = [
        {"rank": i, "score": r["score"],
         "page": r["metadata"].get("page"),
         "source": r["metadata"].get("pdf_name", r["metadata"].get("source")),
         "text": r["text"], "metadata": r["metadata"]}
        for i, r in enumerate(results, 1)
    ]
    st.download_button(
        label     = "⬇  Download results as JSON",
        data      = json.dumps({"query": last_q, "mode": mode, "results": export},
                               indent=2, ensure_ascii=False),
        file_name = "vecrag_results.json",
        mime      = "application/json",
        key       = "dl_json",
    )