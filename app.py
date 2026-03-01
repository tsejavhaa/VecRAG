"""
app.py  —  VecRAG  (LangChain edition)
══════════════════════════════════════════
Two-panel layout:
  LEFT sidebar  = all configuration controls
  RIGHT main    = three tabs: Documents | Embed | Search

Run:
  pip install -r requirements.txt
  streamlit run app.py

Structure:
  core/
    loader.py       ← LangChain PDF loading, page render
    splitter.py     ← LangChain text splitters
    embedder.py     ← LangChain HuggingFace / Ollama embeddings
    vectorstore.py  ← LangChain Chroma + search + background worker
  ui/
    styles.py       ← Navy + Teal theme CSS
    components.py   ← Reusable HTML helpers
  panels/
    documents.py    ← Tab 1: Upload, preview, extract
    embed.py        ← Tab 2: Configure, embed, live log
    search.py       ← Tab 3: Search, results, export
"""

import logging
import streamlit as st

# ── Silence noisy loggers ─────────────────────────────────────────
logging.basicConfig(level=logging.WARNING)
for _l in ("tornado.websocket", "tornado.iostream", "asyncio",
           "chromadb", "sentence_transformers", "transformers"):
    logging.getLogger(_l).setLevel(logging.ERROR)

# ── Page config  (must be FIRST Streamlit call) ───────────────────
st.set_page_config(
    page_title = "VecRAG · LangChain",
    page_icon  = "⬡",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

from ui.styles    import inject_css
from ui.components import header, cfg_section, status_row
inject_css()

# ── Session-state defaults ────────────────────────────────────────
DEFAULTS = {
    # Document
    "pdf_bytes":        None,
    "pdf_name":         None,
    "lc_docs":          [],
    "preview_page":     1,
    # Splitter
    "splitter_method":  "recursive",
    "chunk_size":       1000,
    "chunk_overlap":    150,
    # Embeddings
    "embed_provider":   "huggingface",
    "embed_model":      (
        "all-MiniLM-L6-v2"   # lightweight default — change in sidebar
        if __import__("os").environ.get("STREAMLIT_SHARING_MODE")
        else "paraphrase-multilingual-MiniLM-L12-v2"
    ),
    "ollama_url":       "http://localhost:11434",
    "ollama_model":     "nomic-embed-text",
    "device":           "cpu",
    # Storage
    "collection_name":  "vecrag_lc",
    "persist_dir":      "./chroma_lc",
    # Search
    "top_k":            5,
    "search_results":   [],
    "last_query":       "",
    "search_did_run":   False,
    "search_status":    "idle",
    "search_elapsed":   0.0,
    "search_logs":      [],
    "search_last_mode": None,
    "search_last_k":    5,
    "search_job_id":    None,
    "search_start_time":0.0,
    "search_q_display": "",
    # Embed job
    "embed_job_id":     None,
    "embed_status":     "idle",
    "embed_error":      None,
    "embed_count":      0,
    "embed_start_time": 0.0,
    "embed_logs":       [],
    "vectorstore":      None,
    # LLM / Ask
    "llm_model":        "lfm2.5-thinking",
    "llm_temperature":   0.1,
    "ask_result":        None,
    "ask_last_question": "",
    "ask_elapsed":       0.0,
    "ask_job_id":        None,
    "ask_start_time":    0.0,
    "ask_q_display":     "",
    # Chunk preview cache
    "chunk_preview_data": None,
    "chunk_preview_key":  None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Imports (after session_state so cached resources are safe) ─────
from core.splitter   import SPLITTER_INFO
from core.embedder   import HUGGINGFACE_MODELS
from core.chain      import LLM_MODELS, DEFAULT_LLM
from core.vectorstore import _job_store, cancel_job, _search_store
from panels.documents import panel as panel_documents
from panels.embed     import panel as panel_embed
from panels.search    import panel as panel_search
from panels.ask       import panel as panel_ask


# ══════════════════════════════════════════════════════════════════
#  CONFIG SIDEBAR
# ══════════════════════════════════════════════════════════════════

def _sidebar():
    with st.sidebar:
        # Logo
        st.markdown("""
        <div style="padding:0.8rem 0 1.2rem">
          <div style="font-family:'Space Grotesk',sans-serif;font-size:1.1rem;
                      font-weight:700;color:#00d4aa;letter-spacing:-0.02em">⬡ VecRAG</div>
          <div style="font-size:0.6rem;color:#4a5a7a;text-transform:uppercase;
                      letter-spacing:0.12em;margin-top:2px">LangChain Edition</div>
        </div>
        """, unsafe_allow_html=True)

        # Status indicators
        has_pdf = st.session_state.pdf_bytes is not None
        has_vs  = st.session_state.vectorstore is not None
        e_st    = st.session_state.embed_status

        # ── PDF ──
        status_row("PDF",
                   st.session_state.pdf_name or "None",
                   "ok" if has_pdf else "off")

        # ── Vector DB ──
        status_row("Vector DB",
                   f"{st.session_state.embed_count} chunks" if has_vs else "Empty",
                   "ok" if has_vs else "off")

        # ── Embed ──
        status_row("Embed", e_st,
                   "pulse" if e_st == "running" else
                   "ok"    if e_st == "done"    else
                   "warn"  if e_st == "error"   else "off")

        # ── Search ──
        s_st      = st.session_state.search_status
        s_q       = st.session_state.get("search_q_display","")
        s_results = st.session_state.get("search_results",[])
        if s_st == "searching":
            s_label = "searching…"
            s_dot   = "pulse"
        elif s_st == "done" and s_results:
            s_label = f"{len(s_results)} results"
            s_dot   = "ok"
        elif s_st == "done" and not s_results:
            s_label = "no results"
            s_dot   = "warn"
        elif s_st == "error":
            s_label = "error"
            s_dot   = "warn"
        elif st.session_state.get("search_did_run") and st.session_state.get("search_last_mode") != st.session_state.get("search_mode"):
            s_label = "settings changed"
            s_dot   = "warn"
        elif has_vs:
            s_label = "ready"
            s_dot   = "off"
        else:
            s_label = "waiting"
            s_dot   = "off"
        status_row("Search", s_label, s_dot)

        # ── Ask ──
        ask_job    = st.session_state.get("ask_job_id")
        ask_result = st.session_state.get("ask_result")
        ask_elapsed = st.session_state.get("ask_elapsed", 0)
        if ask_job:
            a_label = "thinking…"
            a_dot   = "pulse"
        elif ask_result:
            a_label = f"done  {ask_elapsed:.0f}s"
            a_dot   = "ok"
        elif has_vs:
            a_label = "ready"
            a_dot   = "off"
        else:
            a_label = "waiting"
            a_dot   = "off"
        status_row("Ask", a_label, a_dot)

        st.markdown("<hr style='border-color:#1e2d45;margin:1rem 0'>",
                    unsafe_allow_html=True)

        # ── Text Splitter ─────────────────────────────────────────
        cfg_section("✂  Text Splitter")

        method = st.selectbox(
            "Strategy",
            options=list(SPLITTER_INFO.keys()),
            format_func=lambda k: f'{SPLITTER_INFO[k]["label"]}  [{SPLITTER_INFO[k]["tag"]}]',
            index=list(SPLITTER_INFO.keys()).index(st.session_state.splitter_method),
            key="sb_splitter",
        )
        st.session_state.splitter_method = method
        info = SPLITTER_INFO[method]

        # Semantic warning — needs embeddings loaded at split time
        if info["needs_embeddings"]:
            st.markdown(
                '<div class="cfg-hint" style="color:#fbbf24;margin-bottom:0.4rem">'
                '⚠ Uses the embedding model to detect topic shifts. '
                'Slower but produces the most meaningful chunks.</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div class="cfg-hint">{info["desc"]}</div>',
            unsafe_allow_html=True,
        )

        # Size controls — hidden for strategies that manage their own sizing
        if info["has_size_control"]:
            chunk_size = st.slider("Chunk size (chars)",
                                   min_value=100, max_value=3000,
                                   value=st.session_state.chunk_size, step=50,
                                   key="sb_chunk_size")
            st.session_state.chunk_size = chunk_size

            overlap = st.slider("Overlap (chars)",
                                min_value=0, max_value=500,
                                value=st.session_state.chunk_overlap, step=10,
                                key="sb_overlap")
            st.session_state.chunk_overlap = overlap
        else:
            st.markdown(
                '<div class="cfg-hint" style="color:#4a5a7a;margin-top:0.3rem">'
                'Chunk size is determined automatically by this strategy.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='border-color:#1e2d45;margin:1rem 0'>",
                    unsafe_allow_html=True)

        # ── Embedding Model ───────────────────────────────────────
        cfg_section("🧠  Embedding Model")
        st.markdown(
            '<div class="cfg-hint" style="margin-bottom:0.5rem">'
            'Models below support <b style="color:#e2e8f8">Mongolian + English</b>.</div>',
            unsafe_allow_html=True,
        )

        provider = st.selectbox(
            "Provider",
            options=["huggingface", "ollama"],
            format_func=lambda x: "HuggingFace (local)" if x == "huggingface" else "Ollama (local server)",
            index=["huggingface", "ollama"].index(st.session_state.embed_provider),
            key="sb_provider",
        )
        st.session_state.embed_provider = provider

        if provider == "huggingface":
            safe_default = (
                st.session_state.embed_model
                if st.session_state.embed_model in HUGGINGFACE_MODELS
                else "paraphrase-multilingual-MiniLM-L12-v2"
            )
            model = st.selectbox(
                "Model",
                options=list(HUGGINGFACE_MODELS.keys()),
                format_func=lambda k: HUGGINGFACE_MODELS[k]["note"].split("·")[0].strip()
                                       + f"  ({HUGGINGFACE_MODELS[k]['size']})",
                index=list(HUGGINGFACE_MODELS.keys()).index(safe_default),
                key="sb_hf_model",
            )
            st.session_state.embed_model = model
            info = HUGGINGFACE_MODELS[model]
            st.markdown(
                f'<div class="cfg-hint">'
                f'<b style="color:#94a3c0">{info["dims"]}d</b> · {info["size"]}<br>'
                f'🌐 {info["langs"]}<br>'
                f'{info["note"]}</div>',
                unsafe_allow_html=True,
            )
            device = st.selectbox(
                "Device",
                options=["cpu", "cuda", "mps"],
                index=["cpu", "cuda", "mps"].index(st.session_state.device),
                key="sb_device",
            )
            st.session_state.device = device

        else:  # Ollama embedding
            ollama_url = st.text_input(
                "Ollama URL",
                value=st.session_state.ollama_url,
                key="sb_ollama_url",
            )
            st.session_state.ollama_url = ollama_url
            ollama_model = st.text_input(
                "Embedding model",
                value=st.session_state.ollama_model,
                key="sb_ollama_model",
            )
            st.session_state.ollama_model = ollama_model
            st.session_state.embed_model  = ollama_model
            st.markdown(
                '<div class="cfg-hint">Run: <code>ollama pull nomic-embed-text</code></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='border-color:#1e2d45;margin:1rem 0'>",
                    unsafe_allow_html=True)

        # ── LLM — any Ollama model ────────────────────────────────
        cfg_section("🦙  LLM  (Ask tab)")

        # Preset picker for convenience
        preset = st.selectbox(
            "Quick select",
            options=["(type custom below)"] + list(LLM_MODELS.keys()),
            format_func=lambda k: k if k == "(type custom below)"
                                   else LLM_MODELS[k]["label"],
            key="sb_llm_preset",
        )
        if preset != "(type custom below)":
            st.session_state.llm_model = preset

        # Free-text override — accepts any model in your `ollama list`
        llm_model = st.text_input(
            "Model name  (any from ollama list)",
            value=st.session_state.llm_model,
            key="sb_llm_model",
        ).strip()
        st.session_state.llm_model = llm_model or DEFAULT_LLM

        linfo = LLM_MODELS.get(llm_model, {})
        hint  = f'{linfo["note"]} · {linfo["size"]}' if linfo else "Custom Ollama model"
        st.markdown(
            f'<div class="cfg-hint">{hint}</div>',
            unsafe_allow_html=True,
        )

        # Shared Ollama URL (used by both Ollama embedding + LLM)
        if provider != "ollama":   # only show if not already shown above
            ollama_url_llm = st.text_input(
                "Ollama URL",
                value=st.session_state.ollama_url,
                key="sb_ollama_url_llm",
            )
            st.session_state.ollama_url = ollama_url_llm

        st.markdown(
            '<div class="cfg-hint" style="color:#4a5a7a;margin-top:0.4rem">'
            'Pull model once: <code>ollama pull lfm2.5-thinking</code></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<hr style='border-color:#1e2d45;margin:1rem 0'>",
                    unsafe_allow_html=True)

        # ── Storage ───────────────────────────────────────────────
        cfg_section("💾  Storage")

        col_name = st.text_input(
            "Collection name",
            value=st.session_state.collection_name,
            key="sb_col_name",
        )
        st.session_state.collection_name = col_name

        persist = st.text_input(
            "Persist directory",
            value=st.session_state.persist_dir,
            key="sb_persist",
        )
        st.session_state.persist_dir = persist

        st.markdown("<hr style='border-color:#1e2d45;margin:1rem 0'>",
                    unsafe_allow_html=True)

        # ── Reset ─────────────────────────────────────────────────
        if st.button("↺  Start Over", key="reset_all"):
            job_id = st.session_state.get("embed_job_id")
            if job_id:
                cancel_job(job_id)
            for k, v in DEFAULTS.items():
                st.session_state[k] = v
            st.session_state.pop("pdf_total_pages",   None)
            st.session_state.pop("preview_docs",     None)
            st.session_state.pop("chunk_preview_data", None)
            st.session_state.pop("chunk_preview_key",  None)
            st.rerun()


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    _sidebar()
    header()

    tab_docs, tab_embed, tab_search, tab_ask = st.tabs([
        "📄  Documents",
        "⬡  Embed",
        "🔍  Search",
        "🦙  Ask",
    ])

    with tab_docs:
        panel_documents()

    with tab_embed:
        panel_embed()

    with tab_search:
        panel_search()

    with tab_ask:
        panel_ask()


if __name__ == "__main__":
    main()