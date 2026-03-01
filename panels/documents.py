"""
panels/documents.py
────────────────────
Tab 1: Upload · Page Preview · Extracted Text · Chunk Preview
"""
import html
import streamlit as st
from core.loader   import get_page_count, render_page, load_documents
from core.splitter import SPLITTER_INFO, build_splitter, split_documents
from ui.components import section, stat_row


# ── Chunk quality thresholds ──────────────────────────────────────
_TOO_SMALL   = 80    # chars — chunk has almost no context
_TOO_LARGE   = 2200  # chars — may exceed model context window
_IDEAL_MIN   = 200
_IDEAL_MAX   = 1400

# Palette: 10 distinct teal/blue tones for chunk rainbow
_CHUNK_COLORS = [
    "#0e4f5c", "#0d4a54", "#0b424b", "#0e3d4e", "#102f45",
    "#0d3b52", "#0b4455", "#0f4858", "#0d3f4f", "#0b3a4a",
]
_CHUNK_BORDERS = [
    "#1a8fa0", "#17849a", "#1595a8", "#1a7a95", "#1b6e8f",
    "#1a82a2", "#158fa5", "#1a8aaa", "#177f9a", "#1478a0",
]
_CHUNK_LABEL_COLORS = [
    "#4ec9d9", "#45c2d4", "#4dcfd8", "#45bdd0", "#44b8cc",
    "#4ac6d6", "#44ccdb", "#4accd8", "#43c4d2", "#42b8cc",
]


def _quality_badge(n_chars: int) -> tuple[str, str]:
    """Return (html_badge, prose_reason) for a chunk of given char length."""
    if n_chars < _TOO_SMALL:
        return (
            '<span style="background:#3d1515;color:#f87171;font-size:0.6rem;'
            'font-weight:700;padding:1px 7px;border-radius:4px;'
            'text-transform:uppercase;letter-spacing:0.08em">TOO SHORT</span>',
            "Very little context — this chunk may not retrieve well."
        )
    if n_chars > _TOO_LARGE:
        return (
            '<span style="background:#3d2c0a;color:#fbbf24;font-size:0.6rem;'
            'font-weight:700;padding:1px 7px;border-radius:4px;'
            'text-transform:uppercase;letter-spacing:0.08em">TOO LONG</span>',
            "May exceed the embedding model's context window."
        )
    return (
        '<span style="background:#0d3324;color:#34d399;font-size:0.6rem;'
        'font-weight:700;padding:1px 7px;border-radius:4px;'
        'text-transform:uppercase;letter-spacing:0.08em">GOOD</span>',
        ""
    )


def _quality_bar(chunks: list) -> str:
    """Horizontal bar where each segment is coloured by quality."""
    if not chunks: return ""
    segs = []
    for c in chunks:
        n = len(c.page_content)
        if n < _TOO_SMALL:
            col = "#f87171"
        elif n > _TOO_LARGE:
            col = "#fbbf24"
        else:
            col = "#34d399"
        w = max(1, int(100 / len(chunks)))
        segs.append(f'<div style="flex:{w};background:{col};height:6px"></div>')
    return (
        '<div style="display:flex;gap:1px;border-radius:4px;overflow:hidden;'
        'margin-bottom:0.6rem">' + "".join(segs) + "</div>"
    )


def _ends_mid_sentence(text: str) -> bool:
    """Rough heuristic: chunk ends without closing punctuation."""
    t = text.rstrip()
    if not t: return False
    return t[-1] not in ".!?»\"'"


def panel():
    # ────────────────────────────────────────────────────────────────
    # UPLOAD
    # ────────────────────────────────────────────────────────────────
    section("Upload")
    uploaded = st.file_uploader(
        "Drop a PDF",
        type=["pdf"],
        label_visibility="collapsed",
        key="pdf_uploader",
    )

    if uploaded:
        raw = uploaded.read()
        if raw != st.session_state.get("pdf_bytes"):
            st.session_state.pdf_bytes    = raw
            st.session_state.pdf_name     = uploaded.name
            st.session_state.lc_docs      = []
            st.session_state.preview_page = 1
            st.session_state.pop("pdf_total_pages",    None)
            st.session_state.pop("preview_docs",       None)
            st.session_state.pop("chunk_preview_data", None)
            st.session_state.embed_status = "idle"
            st.session_state.vectorstore  = None
    else:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2rem;opacity:0.5">
          <div style="font-size:2rem;margin-bottom:0.5rem">⬆</div>
          <div style="font-family:'Space Grotesk',sans-serif;font-weight:600;color:#e2e8f8">
            No file selected
          </div>
          <div style="font-size:0.72rem;color:#4a5a7a;margin-top:0.3rem">
            Click above or drag a PDF onto the uploader
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    pdf_bytes = st.session_state.pdf_bytes
    pdf_name  = st.session_state.pdf_name

    if "pdf_total_pages" not in st.session_state:
        st.session_state.pdf_total_pages = get_page_count(pdf_bytes)
    total   = st.session_state.pdf_total_pages
    size_kb = len(pdf_bytes) // 1024

    stat_row([(total, "Pages"), (f"{size_kb} KB", "Size")])
    st.markdown(f"""
    <div class="card card-teal" style="padding:0.7rem 1rem;margin-bottom:0.8rem">
      <span style="color:#e2e8f8;font-weight:600">✓ Loaded</span>
      <span style="color:#94a3c0;margin-left:8px;font-size:0.8rem">📄 {pdf_name}</span>
    </div>
    """, unsafe_allow_html=True)

    # ────────────────────────────────────────────────────────────────
    # PAGE VIEWER
    # ────────────────────────────────────────────────────────────────
    section("Page Preview")
    cur = st.session_state.preview_page
    _l, nav, _r = st.columns([2, 3, 2])
    with nav:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("◀", key="pg_prev", disabled=(cur <= 1),
                         use_container_width=True):
                st.session_state.preview_page = cur - 1
                st.rerun()
        with c2:
            jumped = st.number_input(
                "p", min_value=1, max_value=total,
                value=cur, step=1, label_visibility="collapsed",
            )
            if int(jumped) != cur:
                st.session_state.preview_page = int(jumped)
                st.rerun()
        with c3:
            if st.button("▶", key="pg_next", disabled=(cur >= total),
                         use_container_width=True):
                st.session_state.preview_page = cur + 1
                st.rerun()

    st.markdown(
        f"<div style='text-align:center;font-size:0.68rem;color:#4a5a7a;"
        f"margin:4px 0 10px'>Page {cur} of {total}</div>",
        unsafe_allow_html=True,
    )
    with st.spinner(f"Rendering page {cur}…"):
        b64 = render_page(pdf_bytes, cur)
    if b64:
        st.markdown(f"""
        <div class="page-viewer">
          <img src="data:image/png;base64,{b64}">
          <div class="page-caption">Page {cur} / {total}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Page renderer unavailable — install pymupdf.")

    # ────────────────────────────────────────────────────────────────
    # EXTRACTED TEXT PREVIEW
    # ────────────────────────────────────────────────────────────────
    section("Extracted Text Preview")
    st.markdown(
        "<div style='font-size:0.7rem;color:#4a5a7a;margin-bottom:0.5rem'>"
        "Live preview of what LangChain loads page-by-page.</div>",
        unsafe_allow_html=True,
    )
    if st.button("↺  Preview extraction (first 3 pages)", key="preview_extract"):
        with st.spinner("Loading with LangChain…"):
            docs = load_documents(pdf_bytes, pdf_name)
            st.session_state.preview_docs = docs[:3]

    for doc in st.session_state.get("preview_docs", []):
        pg  = doc.metadata.get("page", "?")
        txt = doc.page_content[:600] + ("…" if len(doc.page_content) > 600 else "")
        with st.expander(f"Page {pg}  —  {len(doc.page_content):,} chars"):
            st.markdown(
                f'<div style="font-size:0.75rem;line-height:1.75;color:#94a3c0;'
                f'white-space:pre-wrap">{html.escape(txt)}</div>',
                unsafe_allow_html=True,
            )

    # ────────────────────────────────────────────────────────────────
    # CHUNK PREVIEW
    # ────────────────────────────────────────────────────────────────
    section("Chunk Preview")

    method      = st.session_state.splitter_method
    chunk_size  = st.session_state.chunk_size
    overlap     = st.session_state.chunk_overlap
    sp_info     = SPLITTER_INFO[method]

    st.markdown(
        f'<div style="font-size:0.72rem;color:#4a5a7a;margin-bottom:0.7rem">'
        f'Shows how <b style="color:#94a3c0">{sp_info["label"]}</b> splits '
        f'the first 3 pages with your current settings. '
        f'Change settings in the sidebar — click Refresh to update.</div>',
        unsafe_allow_html=True,
    )

    # Semantic chunker can't run in preview (needs full embedding load)
    if method == "semantic":
        st.markdown("""
        <div class="card card-warn" style="font-size:0.8rem">
          <b style="color:#fbbf24">⚠ Semantic chunker preview not available</b><br>
          <span style="color:#94a3c0">
            SemanticChunker needs to run the full embedding model to detect topic
            boundaries — too slow for a live preview. Use a different strategy to
            preview, then switch back to Semantic for your final embed.
          </span>
        </div>
        """, unsafe_allow_html=True)
        return

    # Build a cache key from current settings so we auto-invalidate
    preview_key = (method, chunk_size, overlap, pdf_name)
    cached      = st.session_state.get("chunk_preview_data")
    key_match   = st.session_state.get("chunk_preview_key") == preview_key

    if st.button("⬡  Run Chunk Preview", key="run_chunk_preview") or \
       (cached is None and not key_match):
        with st.spinner("Splitting first 3 pages…"):
            try:
                docs     = load_documents(pdf_bytes, pdf_name)
                sample   = docs[:3]
                splitter = build_splitter(method, chunk_size, overlap)
                chunks   = split_documents(sample, splitter)
                st.session_state.chunk_preview_data = chunks
                st.session_state.chunk_preview_key  = preview_key
            except Exception as e:
                st.error(f"Preview failed: {e}")
                return

    chunks = st.session_state.get("chunk_preview_data")
    if not chunks:
        return

    # ── Aggregate stats ──────────────────────────────────────────
    sizes     = [len(c.page_content) for c in chunks]
    avg_size  = int(sum(sizes) / len(sizes)) if sizes else 0
    min_size  = min(sizes)
    max_size  = max(sizes)
    n_short   = sum(1 for s in sizes if s < _TOO_SMALL)
    n_long    = sum(1 for s in sizes if s > _TOO_LARGE)
    n_good    = len(sizes) - n_short - n_long
    n_midcut  = sum(1 for c in chunks if _ends_mid_sentence(c.page_content))
    pct_good  = int(n_good / len(chunks) * 100) if chunks else 0

    # Overall verdict
    if pct_good >= 85 and n_midcut <= len(chunks) * 0.25:
        verdict_col = "#34d399"
        verdict_ico = "✅"
        verdict_txt = "Good split — most chunks are well-sized and end cleanly."
    elif pct_good >= 55:
        verdict_col = "#fbbf24"
        verdict_ico = "⚠"
        verdict_txt = (
            f"{n_short} too-short and {n_long} too-long chunks detected. "
            "Try adjusting chunk size or switching strategy."
        )
    else:
        verdict_col = "#f87171"
        verdict_ico = "✗"
        verdict_txt = (
            "Poor split quality — many chunks are outside the ideal range. "
            "Consider a different strategy for this document."
        )

    st.markdown(f"""
    <div class="card" style="border-left:3px solid {verdict_col};margin-bottom:1rem">
      <div style="font-family:'Space Grotesk',sans-serif;font-weight:600;
                  color:{verdict_col};font-size:0.9rem;margin-bottom:6px">
        {verdict_ico} {verdict_txt}
      </div>
      <div style="font-size:0.72rem;color:#4a5a7a">
        {len(chunks)} chunks from 3 pages &nbsp;·&nbsp;
        avg <b style="color:#94a3c0">{avg_size}</b> chars &nbsp;·&nbsp;
        min <b style="color:#94a3c0">{min_size}</b> &nbsp;·&nbsp;
        max <b style="color:#94a3c0">{max_size}</b> &nbsp;·&nbsp;
        <span style="color:#34d399">{n_good} good</span> &nbsp;
        <span style="color:#fbbf24">{n_long} long</span> &nbsp;
        <span style="color:#f87171">{n_short} short</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Quality bar — visual overview of all chunks at a glance
    st.markdown(_quality_bar(chunks), unsafe_allow_html=True)
    st.markdown(
        '<div style="display:flex;gap:1.2rem;font-size:0.62rem;color:#4a5a7a;'
        'margin-bottom:1rem">'
        '<span><span style="color:#34d399">■</span> Good (200–1400 chars)</span>'
        '<span><span style="color:#fbbf24">■</span> Too long (&gt;1400)</span>'
        '<span><span style="color:#f87171">■</span> Too short (&lt;80)</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Individual chunk cards ────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.65rem;color:#4a5a7a;margin-bottom:0.5rem">'
        'Each card = one chunk. Hover to see full text.</div>',
        unsafe_allow_html=True,
    )

    # Show max 25 chunks to keep the page fast
    display = chunks[:25]
    more    = len(chunks) - len(display)

    for i, chunk in enumerate(display):
        text    = chunk.page_content
        n_chars = len(text)
        badge, reason = _quality_badge(n_chars)
        cut_warn = (
            '<span style="font-size:0.62rem;color:#fbbf24;margin-left:8px">'
            '✂ ends mid-sentence</span>'
            if _ends_mid_sentence(text) else ""
        )
        pg = chunk.metadata.get("page", chunk.metadata.get("page_label", "?"))

        # Colour cycles through the palette
        ci     = i % len(_CHUNK_COLORS)
        bg     = _CHUNK_COLORS[ci]
        border = _CHUNK_BORDERS[ci]
        lbl    = _CHUNK_LABEL_COLORS[ci]

        # Preview: first 280 chars, html-escaped
        preview = html.escape(text[:280]) + ("…" if n_chars > 280 else "")

        # Replace newlines with ↵ so they're visible inline
        preview_inline = preview.replace("\n", " ↵ ")

        # IMPORTANT: No line must start with 4+ spaces — Streamlit's markdown
        # parser treats indented lines as <code> blocks, leaking raw HTML.
        # Also: build font-family span separately to avoid quote clash in f-string.
        reason_html  = f'<div style="font-size:0.65rem;color:#4a5a7a;margin-top:4px">{reason}</div>' if reason else ""
        rank_span    = f'<span style="font-family:Space Grotesk,sans-serif;font-weight:700;color:{lbl};font-size:0.75rem">#{i+1}</span>'
        meta_span    = f'<span style="margin-left:auto;font-size:0.62rem;color:#4a5a7a">page {pg} &nbsp;&middot;&nbsp; {n_chars:,} chars</span>'
        header_row   = f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:0.5rem;flex-wrap:wrap">{rank_span}{badge}{cut_warn}{meta_span}</div>'
        text_div     = f'<div style="font-size:0.75rem;line-height:1.7;color:#8fbcbb;white-space:pre-wrap;word-break:break-word">{preview_inline}</div>'
        outer        = f'<div style="background:{bg};border:1px solid {border};border-left:3px solid {border};border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem">{header_row}{text_div}{reason_html}</div>'
        st.markdown(outer, unsafe_allow_html=True)

    if more > 0:
        st.markdown(
            f'<div style="text-align:center;font-size:0.72rem;color:#4a5a7a;'
            f'padding:0.5rem">+ {more} more chunks not shown</div>',
            unsafe_allow_html=True,
        )

    # ── Strategy comparison tip ───────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section("Strategy Comparison Guide")

    rows = []
    for key, info in SPLITTER_INFO.items():
        if key == "semantic":
            quality = "⭐⭐⭐⭐⭐"
            speed   = "🐢 Slow"
            note    = "Topic-aware splits. Best for retrieval quality."
        elif key == "recursive":
            quality = "⭐⭐⭐⭐"
            speed   = "⚡ Fast"
            note    = "Best all-round. Start here."
        elif key == "sentence":
            quality = "⭐⭐⭐⭐"
            speed   = "⚡ Fast"
            note    = "Never exceeds model token limit."
        elif key == "paragraph":
            quality = "⭐⭐⭐"
            speed   = "⚡ Fast"
            note    = "Great if PDF has clear paragraphs."
        elif key == "token":
            quality = "⭐⭐⭐"
            speed   = "⚡ Fast"
            note    = "Use when feeding chunks to an LLM."
        else:  # markdown
            quality = "⭐⭐⭐"
            speed   = "⚡ Fast"
            note    = "Only works well on headed documents."

        active_style = (
            "border:1px solid #1a8fa0;background:#0a2530"
            if key == method else
            "border:1px solid #1e2d45;background:#111827"
        )
        active_dot = (
            '<span style="color:#00d4aa;font-size:0.65rem"> ← current</span>'
            if key == method else ""
        )
        rows.append(f"""
        <div style="{active_style};border-radius:7px;padding:0.6rem 0.9rem;
                    margin-bottom:0.4rem;display:flex;align-items:center;gap:10px;
                    flex-wrap:wrap">
          <span style="font-family:'Space Grotesk',sans-serif;font-weight:600;
                       color:#e2e8f8;min-width:200px;font-size:0.8rem">
            {info['label']}{active_dot}
          </span>
          <span style="font-size:0.75rem;min-width:100px">{quality}</span>
          <span style="font-size:0.72rem;color:#4a5a7a;min-width:70px">{speed}</span>
          <span style="font-size:0.72rem;color:#94a3c0">{note}</span>
        </div>
        """)

    st.markdown("".join(rows), unsafe_allow_html=True)