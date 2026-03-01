"""
panels/ask.py
──────────────
Tab 4: Ask — background-threaded LLM with live elapsed timer + cancel.
The LLM runs in a ThreadPoolExecutor so the UI never freezes.
"""
import time
import streamlit as st
from core.chain    import (submit_ask, poll_ask, cancel_ask,
                           LLM_MODELS, DEFAULT_LLM)
from ui.components import section, stat_row, card


def _ollama_reachable(url: str, model: str) -> tuple[bool, str]:
    """GET /api/tags — instant, no inference."""
    try:
        import requests
        r = requests.get(f"{url.rstrip('/')}/api/tags", timeout=5)
        if r.status_code != 200:
            return False, f"Ollama returned HTTP {r.status_code}"
        installed  = [m.get("name","") for m in r.json().get("models",[])]
        model_base = model.split(":")[0]
        found = any(m == model or m.startswith(model_base+":") for m in installed)
        if not found:
            names = ", ".join(installed) or "none"
            return False, (f"Model '{model}' not pulled.\n"
                           f"Installed: {names}\n"
                           f"Fix: ollama pull {model}")
        return True, ""
    except Exception as e:
        return False, str(e)


def _fmt_elapsed(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}m {s % 60}s" if s >= 60 else f"{s}s"


def panel():
    vs = st.session_state.get("vectorstore")

    # ── Guard ─────────────────────────────────────────────────────
    if vs is None:
        card(
            '<b style="color:#e2e8f8">No vector store loaded.</b><br>'
            '<span style="font-size:0.78rem">Go to <b>Embed</b> and run embedding first.</span>',
            variant="warn",
        )
        return

    ollama_url = st.session_state.ollama_url
    llm_model  = st.session_state.llm_model

    # ── LLM status ────────────────────────────────────────────────
    section("LLM")
    info = LLM_MODELS.get(llm_model, {"note": "custom model", "size": "?"})
    _display = info.get("label", llm_model)
    st.markdown(
        f'<div class="status-row"><div class="dot dot-ok"></div>'
        f'<span style="color:#4a5a7a;min-width:90px">Model</span>'
        f'<span style="color:#e2e8f8;font-size:0.72rem">{_display}</span>'
        f'<span style="color:#4a5a7a;font-size:0.68rem;margin-left:8px">'
        f'{info["note"]} · {info["size"]}</span></div>'
        f'<div class="status-row"><div class="dot dot-off"></div>'
        f'<span style="color:#4a5a7a;min-width:90px">Ollama</span>'
        f'<span style="color:#94a3c0;font-size:0.72rem">{ollama_url}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════════════════════
    # RUNNING — poll background thread, show live timer
    # ══════════════════════════════════════════════════════════════
    job_id = st.session_state.get("ask_job_id")
    if job_id:
        state, payload = poll_ask(job_id)
        elapsed = time.time() - st.session_state.get("ask_start_time", time.time())

        if state == "done":
            st.session_state.ask_result        = payload
            st.session_state.ask_last_question = st.session_state.get("ask_q_display","")
            st.session_state.ask_elapsed        = elapsed
            st.session_state.pop("ask_job_id",   None)
            st.session_state.pop("ask_start_time", None)
            st.rerun(); return

        if state == "error":
            err_lines = payload
            st.session_state.pop("ask_job_id",    None)
            st.session_state.pop("ask_start_time", None)
            st.error(f"LLM error: {err_lines[-1] if err_lines else 'unknown'}")
            st.markdown(
                '<div style="font-size:0.72rem;color:#4a5a7a;margin-top:0.3rem">'
                f'Run: <code>ollama pull {llm_model}</code> if model is missing.<br>'
                'Run: <code>pip install langchain-ollama langchain-core</code> if import fails.'
                '</div>', unsafe_allow_html=True,
            )
            return

        # Still running — show live progress
        logs = payload   # list of log lines from the worker
        st.markdown(
            f'<div class="card card-teal" style="text-align:center;padding:1.6rem 1.2rem">'
            f'<div style="font-size:2rem;margin-bottom:6px">🦙</div>'
            f'<div style="font-family:\'Space Grotesk\',sans-serif;font-weight:700;'
            f'color:#00d4aa;font-size:1.1rem;margin-bottom:4px">Thinking…</div>'
            f'<div style="font-size:1.6rem;font-weight:700;color:#e2e8f8;'
            f'font-family:\'Space Grotesk\',sans-serif;margin-bottom:8px">'
            f'{_fmt_elapsed(elapsed)}</div>'
            f'<div style="font-size:0.7rem;color:#4a5a7a">'
            f'{"<br>".join(logs[-3:]) if logs else "Loading model into memory…"}'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # Cancel button
        if st.button("✕  Cancel", key="cancel_ask"):
            cancel_ask(job_id)
            st.session_state.pop("ask_job_id",    None)
            st.session_state.pop("ask_start_time", None)
            st.rerun(); return

        time.sleep(1); st.rerun(); return   # poll every second

    # ══════════════════════════════════════════════════════════════
    # IDLE — question form
    # ══════════════════════════════════════════════════════════════
    section("Question")
    st.markdown(
        '<div style="font-size:0.72rem;color:#4a5a7a;margin-bottom:0.5rem">'
        'Runs in background — UI stays responsive. First call loads the model '
        '(~10–30s). Subsequent calls are faster.</div>',
        unsafe_allow_html=True,
    )

    user_question = st.text_area(
        "Question",
        placeholder="Антиматери гэж юу вэ?\nWhat is OpenCV?\nWhat are the main topics?",
        height=100,
        label_visibility="collapsed",
        key="ask_input",
    )

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        top_k = st.number_input("Chunks (k)", min_value=1, max_value=15,
                                value=5, step=1, key="ask_top_k")
    with c2:
        lang = st.selectbox(
            "Language",
            options=["auto","mongolian","english"],
            format_func=lambda x: {"auto":"🌐 Auto","mongolian":"🇲🇳 Mongolian",
                                    "english":"🇬🇧 English"}[x],
            key="ask_lang",
        )
    with c3:
        temp = st.slider("Temperature  (0 = focused · 1 = creative)",
                         min_value=0.0, max_value=1.0, value=0.1, step=0.05,
                         key="ask_temp")

    # Show friendly label on button — use LLM_MODELS display name if available,
    # otherwise fall back to the raw model tag
    _btn_label = LLM_MODELS.get(llm_model, {}).get("label", llm_model)
    run = st.button(f"⬡  Ask {_btn_label}", key="run_ask",
                    disabled=(not user_question.strip()))

    if run and user_question.strip():
        ok, err = _ollama_reachable(ollama_url, llm_model)
        if not ok:
            st.markdown(
                f'<div class="card card-danger">'
                f'<b style="color:#f87171">⚠ Cannot reach Ollama</b><br>'
                f'<span style="font-size:0.78rem;color:#94a3c0">'
                f'{err.replace(chr(10),"<br>")}</span></div>',
                unsafe_allow_html=True,
            )
            return

        # Submit to background thread — UI immediately goes to the poll loop
        job_id = submit_ask(
            vectorstore  = vs,
            model_name   = llm_model,
            ollama_url   = ollama_url,
            temperature  = float(temp),
            question     = user_question.strip(),
            top_k        = int(top_k),
            language     = lang,
        )
        st.session_state.ask_job_id    = job_id
        st.session_state.ask_start_time = time.time()
        st.session_state.ask_q_display  = user_question.strip()
        st.rerun(); return

    # ══════════════════════════════════════════════════════════════
    # RESULTS
    # ══════════════════════════════════════════════════════════════
    result  = st.session_state.get("ask_result")
    prev_q  = st.session_state.get("ask_last_question","")
    elapsed = st.session_state.get("ask_elapsed", 0)

    if not result:
        st.markdown(
            '<div class="card" style="text-align:center;padding:2.5rem;opacity:0.45">'
            '<div style="font-size:2rem;margin-bottom:0.5rem">🦙</div>'
            '<div style="font-family:\'Space Grotesk\',sans-serif;font-weight:600;'
            'color:#e2e8f8;font-size:0.9rem">Ready to answer</div>'
            '<div style="font-size:0.7rem;color:#4a5a7a;margin-top:0.4rem">'
            'Type a question and press Ask</div></div>',
            unsafe_allow_html=True,
        )
        return

    section(f'Answer — "{prev_q[:60]}{"…" if len(prev_q)>60 else ""}"')
    stat_row([
        (llm_model,              "Model"),
        (f"{elapsed:.1f}s",      "Response time"),
        (len(result["sources"]), "Chunks used"),
    ])

    answer_safe = (
        result["answer"]
        .replace("<","&lt;").replace(">","&gt;")
        .replace("\n\n","</p><p>").replace("\n","<br>")
    )
    st.markdown(
        f'<div class="card card-teal" style="font-size:0.88rem;line-height:1.9;'
        f'color:#dde6f8;padding:1.2rem 1.4rem"><p>{answer_safe}</p></div>',
        unsafe_allow_html=True,
    )

    if result["sources"]:
        section(f'Source Chunks  ({len(result["sources"])} retrieved)')
        for i, src in enumerate(result["sources"], 1):
            text_safe = src["text"].replace("<","&lt;").replace(">","&gt;")
            st.markdown(
                f'<div class="result-card">'
                f'<div class="result-meta">#{i} &nbsp;·&nbsp; 📄 {src["pdf"]}'
                f' &nbsp;·&nbsp; page {src["page"]}'
                f' &nbsp;·&nbsp; {len(src["text"]):,} chars</div>'
                f'<div class="result-text">{text_safe}</div></div>',
                unsafe_allow_html=True,
            )