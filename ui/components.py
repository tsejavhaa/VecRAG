"""
ui/components.py
────────────────
Reusable HTML component helpers for VecRAG.
"""
import streamlit as st


def header():
    st.markdown("""
    <div class="v2-header">
      <div class="v2-logo">⬡ VecRAG</div>
      <div class="v2-tagline">PDF → Vector DB · LangChain Edition</div>
      <div class="v2-badge">LangChain</div>
    </div>
    """, unsafe_allow_html=True)


def section(title: str):
    st.markdown(f'<div class="sh">{title}</div>', unsafe_allow_html=True)


def cfg_section(title: str):
    st.markdown(f'<div class="cfg-title">{title}</div>', unsafe_allow_html=True)


def terminal_log(lines: list[str], title: str = "embed.log"):
    body = "\n".join(lines[-40:]) if lines else "Waiting…"
    st.markdown(f"""
    <div class="terminal-header">
      <div class="term-dot term-dot-r"></div>
      <div class="term-dot term-dot-y"></div>
      <div class="term-dot term-dot-g"></div>
      <div class="term-title">{title}</div>
    </div>
    <div class="terminal">{body}
</div>
    """, unsafe_allow_html=True)


def status_row(label: str, value: str, state: str = "off"):
    """state: 'ok' | 'warn' | 'off' | 'pulse'"""
    st.markdown(f"""
    <div class="status-row">
      <div class="dot dot-{state}"></div>
      <span style="color:#4a5a7a;min-width:90px">{label}</span>
      <span style="color:#e2e8f8;font-size:0.72rem;word-break:break-all">{value}</span>
    </div>
    """, unsafe_allow_html=True)


def stat_row(stats: list[tuple]):
    """stats = [(value, label), ...]"""
    boxes = "".join(
        f'<div class="stat-box"><div class="stat-val">{v}</div>'
        f'<div class="stat-lbl">{l}</div></div>'
        for v, l in stats
    )
    st.markdown(f'<div class="stat-row">{boxes}</div>', unsafe_allow_html=True)


def result_card(rank: int, text: str, meta: dict, score):
    import html as _html
    score_pct = int(score * 100) if score is not None else None
    if score_pct is None:
        score_html = '<span class="result-score score-mid">MMR</span>'
    elif score_pct >= 70:
        score_html = f'<span class="result-score score-hi">{score_pct}%</span>'
    elif score_pct >= 40:
        score_html = f'<span class="result-score score-mid">{score_pct}%</span>'
    else:
        score_html = f'<span class="result-score score-lo">{score_pct}%</span>'

    pg       = meta.get("page", meta.get("page_label", "?"))
    source   = meta.get("pdf_name", meta.get("source", "?"))
    n_chars  = len(text)

    # Show full text — html-escape but preserve newlines as <br>
    safe = _html.escape(text).replace("\n\n", "</p><p>").replace("\n", "<br>")
    safe = f"<p>{safe}</p>"

    st.markdown(f"""
    <div class="result-card">
      {score_html}
      <div class="result-meta">
        #{rank} &nbsp;·&nbsp; 📄 {source} &nbsp;·&nbsp; page {pg}
        &nbsp;·&nbsp; {n_chars:,} chars
      </div>
      <div class="result-text">{safe}</div>
    </div>
    """, unsafe_allow_html=True)


def card(body: str, variant: str = "teal"):
    st.markdown(
        f'<div class="card card-{variant}">{body}</div>',
        unsafe_allow_html=True,
    )